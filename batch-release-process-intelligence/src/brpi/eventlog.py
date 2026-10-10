"""Event-log builder: SAP-style extract (+ MES/QMS) -> one event log + a data-quality report.

Event schema (one row per activity instance):
    case_id      plant|material|batch (SAP WERKS|MATNR|CHARG)
    activity     see config.ACTIVITIES
    ts_start     start time, or NaT when it cannot be established (see start rule)
    ts_end       completion time (milestones: ts_start == ts_end)
    role         organisational role (hand-offs = consecutive role changes)
    source_table AFRU, MSEG, QALS, QAMR, QMEL, QAVE, STATUS_LOG(JCDS|CDHDR/CDPOS), MES_BATCH_RECORD, QMS_DISPOSITION
    source_key   key of the source row (order, document, lot, notification, record id ...)
    start_source explicit | status_log | milestone | none
    match_conf   crosswalk confidence of the batch ID (1.0 for SAP tables)
    inherited_from  parent case for events inherited through a batch split/merge, else ''
    ud_code      usage-decision code (Usage Decision rows only)

Rules (each one is counted in the data-quality report):
  R1 start times: explicit start column -> status-change log (JCDS / CDHDR-CDPOS) -> none ("elapsed, unsplit")
  R2 duplicates: collapse on (case_id, activity, ts_end, source_key)
  R3 same activity + same timestamp + new key -> suspected re-send (kept out of rework, listed)
     same activity + new key + new timestamp -> repeat (rework candidate)
  R4 splits/merges: children inherit the parent's upstream (manufacturing) events via LINEAGE
  R5 batch IDs from MES/QMS are matched to SAP batches through a crosswalk with a confidence;
     matches below MATCH_MIN_CONF are excluded from the log and reported as unmatched/ambiguous
  R6 start after end -> start dropped (flagged)
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C

TS = '%Y-%m-%d %H:%M:%S'


def _ts(s):
    return pd.to_datetime(s.replace('', np.nan), format=TS, errors='coerce')


def load_raw(raw_dir):
    raw_dir = Path(raw_dir)
    out = {}
    for p in raw_dir.glob('*.csv'):
        out[p.stem] = pd.read_csv(p, dtype=str, keep_default_na=False)
    return out


def levenshtein(a, b, maxd=2):
    if abs(len(a) - len(b)) > maxd:
        return maxd + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def normalise_id(s, plant=None):
    s = re.sub(r'[^A-Za-z0-9]', '', str(s)).upper()
    if plant and s.startswith(plant):
        s = s[len(plant):]
    return s


def build_crosswalk(ids, sap_batches, gr_ts, window=(-2, 120)):
    """ids: DataFrame [source_system, plant, source_id, first_ts]. sap_batches: {plant: set(charg)}.
    gr_ts: {(plant, charg): goods-receipt timestamp} used for timing plausibility.
    Returns DataFrame [source_system, plant, source_id, charg, method, confidence]."""
    rows = []
    for r in ids.itertuples(index=False):
        norm = normalise_id(r.source_id, r.plant)
        pool = sap_batches.get(r.plant, set())

        def plausible(ch):
            g = gr_ts.get((r.plant, ch))
            if g is None or pd.isna(r.first_ts):
                return False
            d = (r.first_ts - g).total_seconds() / 86400
            return window[0] <= d <= window[1]
        if norm in pool:
            if plausible(norm):
                rows.append((r.source_system, r.plant, r.source_id, norm, 'exact after normalisation', 1.0))
            else:
                rows.append((r.source_system, r.plant, r.source_id, norm, 'exact, implausible timing', 0.5))
            continue
        cands = [ch for ch in pool if abs(len(ch) - len(norm)) <= 1 and levenshtein(norm, ch, 1) <= 1]
        if not cands:
            rows.append((r.source_system, r.plant, r.source_id, '', 'unmatched', 0.0))
            continue
        ok = [ch for ch in cands if plausible(ch)]
        if len(cands) == 1 and ok:
            rows.append((r.source_system, r.plant, r.source_id, cands[0], 'fuzzy (edit distance 1), unique', 0.85))
        elif len(ok) == 1:
            rows.append((r.source_system, r.plant, r.source_id, ok[0],
                         'fuzzy (edit distance 1), resolved by timing among %d' % len(cands), 0.8))
        else:
            rows.append((r.source_system, r.plant, r.source_id, '', 'ambiguous (%d candidates)' % len(cands), 0.5))
    return pd.DataFrame(rows, columns=['source_system', 'plant', 'source_id', 'charg', 'method', 'confidence'])


def build_event_log(raw):
    """raw: dict table -> DataFrame (strings). Returns (events, crosswalk, lineage, dq)."""
    dq = {'rules': {}, 'tables': {t: int(len(df)) for t, df in raw.items()}}
    ev = []
    cid = lambda w, m, c: '%s|%s|%s' % (w, m, c)  # noqa: E731
    stl = raw.get('STATUS_LOG', pd.DataFrame(columns=['STAT_ID', 'OBJ_TYPE', 'OBJ_KEY', 'STAT', 'UDATE_TS', 'SOURCE']))
    stl = stl.assign(ts=_ts(stl['UDATE_TS']))
    stat_start = {(r.OBJ_TYPE, r.OBJ_KEY): r.ts for r in stl.itertuples() if r.STAT in ('STARTED', 'INSP_START', 'IN_REVIEW')}

    def add(case, act, s, e, src, key, start_source, conf=1.0, ud=''):
        ev.append((case, act, s, e, C.ROLE[act], src, key, start_source, conf, '', ud))

    # AFRU -> Manufacturing Executed (one per order: first operation start, last confirmation finish)
    afru = raw['AFRU'].assign(s=lambda d: _ts(d['ISDD']), e=lambda d: _ts(d['IEDD']))
    afru = afru.drop_duplicates(subset=['RUECK'])          # duplicate confirmation rows (same key)
    for (w, m, c, a), g in afru.groupby(['WERKS', 'MATNR', 'CHARG', 'AUFNR']):
        g = g.sort_values('VORNR')
        s0 = g['s'].iloc[0]
        if pd.notna(s0):
            s, how = s0, 'explicit'
        elif ('AUFNR', a) in stat_start:
            s, how = stat_start[('AUFNR', a)], 'status_log'
        else:
            s, how = pd.NaT, 'none'
        add(cid(w, m, c), 'Manufacturing Executed', s, g['e'].max(), 'AFRU', a, how)

    mseg = raw['MSEG']
    mseg = mseg[mseg['BWART'] == '101'].assign(t=lambda d: _ts(d['BUDAT_TS']))
    for r in mseg.itertuples():
        add(cid(r.WERKS, r.MATNR, r.CHARG), 'Goods Receipt', r.t, r.t, 'MSEG', '%s/%s' % (r.MBLNR, r.ZEILE), 'milestone')

    qals = raw['QALS'].assign(t=lambda d: _ts(d['ENSTEHDAT_TS']))
    lot_case = {}
    for r in qals.itertuples():
        lot_case[r.PRUEFLOS] = cid(r.WERK, r.MATNR, r.CHARG)
        add(lot_case[r.PRUEFLOS], 'Inspection Lot Created', r.t, r.t, 'QALS', r.PRUEFLOS, 'milestone')

    qamr = raw['QAMR'].assign(s=lambda d: _ts(d['PRUEFDATUV_TS']), e=lambda d: _ts(d['PRUEFDATUB_TS']))
    for r in qamr.itertuples():
        if r.PRUEFLOS not in lot_case:
            continue
        if pd.notna(r.s):
            s, how = r.s, 'explicit'
        elif ('QALS', r.PRUEFLOS) in stat_start:
            s, how = stat_start[('QALS', r.PRUEFLOS)], 'status_log'
        else:
            s, how = pd.NaT, 'none'
        add(lot_case[r.PRUEFLOS], 'QC Results Recorded', s, r.e, 'QAMR', '%s/%s' % (r.PRUEFLOS, r.MERKNR), how)

    qmel = raw['QMEL'].assign(s=lambda d: _ts(d['QMDAT_TS']), e=lambda d: _ts(d['QMDAB_TS']))
    qm_case = {}
    for r in qmel.itertuples():
        c = cid(r.WERKS, r.MATNR, r.CHARG)
        qm_case[r.QMNUM] = c
        add(c, 'Deviation Raised', r.s, r.s, 'QMEL', r.QMNUM, 'milestone')
        if pd.notna(r.e):
            add(c, 'Deviation Closed', r.e, r.e, 'QMEL', r.QMNUM + ':completed', 'milestone')
    for r in stl[stl['OBJ_TYPE'] == 'QMEL'].itertuples():
        if r.OBJ_KEY in qm_case:
            act = {'CLOSED': 'Deviation Closed', 'REOPENED': 'Deviation Reopened'}[r.STAT]
            add(qm_case[r.OBJ_KEY], act, r.ts, r.ts, 'STATUS_LOG:CDHDR/CDPOS', r.STAT_ID, 'milestone')

    qave = raw['QAVE'].assign(t=lambda d: _ts(d['VDATUM_TS']))
    for r in qave.itertuples():
        if r.PRUEFLOS in lot_case:
            add(lot_case[r.PRUEFLOS], 'Usage Decision', r.t, r.t, 'QAVE', '%s/%s' % (r.PRUEFLOS, r.KZART), 'milestone',
                ud=r.VCODE)

    # ---- crosswalk for MES / QMS batch IDs (R5)
    sap = {}
    for (w, m, c) in {tuple(k.split('|')) for k in lot_case.values()}:
        sap.setdefault(w, set()).add(c)
    mat_of = {(k.split('|')[0], k.split('|')[2]): k.split('|')[1] for k in lot_case.values()}
    gr_ts = {(r.WERKS, r.CHARG): r.t for r in mseg.itertuples()}
    mes = raw['MES_BATCH_RECORD'].assign(s=lambda d: _ts(d['TS_START']), e=lambda d: _ts(d['TS_END']))
    qms = raw['QMS_DISPOSITION'].assign(s=lambda d: _ts(d['TS_START']), e=lambda d: _ts(d['TS_END']))
    ids = pd.concat([
        mes.groupby(['PLANT', 'MES_BATCH_ID'])['e'].min().reset_index()
           .rename(columns={'PLANT': 'plant', 'MES_BATCH_ID': 'source_id', 'e': 'first_ts'}).assign(source_system='MES'),
        qms.groupby(['SITE', 'QMS_BATCH_REF'])['e'].min().reset_index()
           .rename(columns={'SITE': 'plant', 'QMS_BATCH_REF': 'source_id', 'e': 'first_ts'}).assign(source_system='QMS'),
    ], ignore_index=True)
    xw = build_crosswalk(ids, sap, gr_ts)
    xmap = {(r.source_system, r.plant, r.source_id): (r.charg, r.confidence) for r in xw.itertuples()}
    excluded_rows = {'MES': 0, 'QMS': 0}
    for sysname, df, idcol, plcol, amap, objt in [
            ('MES', mes, 'MES_BATCH_ID', 'PLANT', {'BR_COMPLETE': 'Batch Record Completed', 'BR_REVIEW': 'Batch Record Review',
                                                    'BR_RETURNED': 'Batch Record Returned', 'BR_CORRECTED': 'Batch Record Corrected'}, 'MES_BR'),
            ('QMS', qms, 'QMS_BATCH_REF', 'SITE', {'DISP_REVIEW': 'QA Disposition Review', 'QA_QUERY': 'QA Query Raised'}, 'QMS_DR')]:
        src = 'MES_BATCH_RECORD' if sysname == 'MES' else 'QMS_DISPOSITION'
        for r in df.itertuples():
            ch, conf = xmap.get((sysname, getattr(r, plcol), getattr(r, idcol)), ('', 0.0))
            if not ch or conf < C.MATCH_MIN_CONF:
                excluded_rows[sysname] += 1
                continue
            plant = getattr(r, plcol)
            act = amap[r.EVENT]
            if act in C.DURATION_ACTIVITIES:
                if pd.notna(r.s):
                    s, how = r.s, 'explicit'
                elif (objt, r.REC_ID) in stat_start:
                    s, how = stat_start[(objt, r.REC_ID)], 'status_log'
                else:
                    s, how = pd.NaT, 'none'
            else:
                s, how = r.e, 'milestone'
            ev.append((cid(plant, mat_of[(plant, ch)], ch), act, s, r.e, C.ROLE[act], src, r.REC_ID, how, conf, '', ''))

    cols = ['case_id', 'activity', 'ts_start', 'ts_end', 'role', 'source_table', 'source_key', 'start_source',
            'match_conf', 'inherited_from', 'ud_code']
    E = pd.DataFrame(ev, columns=cols)
    E['ts_start'] = pd.to_datetime(E['ts_start'])
    E['ts_end'] = pd.to_datetime(E['ts_end'])

    # ---- R2 duplicates
    before = len(E)
    dupmask = E.duplicated(subset=['case_id', 'activity', 'ts_end', 'source_key'])
    dup_by_src = E[dupmask].groupby('source_table').size().to_dict()
    E = E[~dupmask].copy()
    # AFRU duplicates were collapsed on confirmation number before aggregation
    afru_dups = int(raw['AFRU'].duplicated(subset=['RUECK']).sum())
    if afru_dups:
        dup_by_src['AFRU'] = dup_by_src.get('AFRU', 0) + afru_dups
    dq['rules']['R2_duplicates_collapsed'] = {'total': int(before - len(E)) + afru_dups,
                                              'by_source': {k: int(v) for k, v in dup_by_src.items()}}

    # ---- R3 suspected re-sends: same case/activity/timestamp, different key
    rs = E.duplicated(subset=['case_id', 'activity', 'ts_end'], keep='first')
    resend = E[rs][['case_id', 'activity', 'ts_end', 'source_table', 'source_key']]
    E = E[~rs].copy()
    dq['rules']['R3_suspected_resends'] = {'count': int(len(resend)),
                                           'examples': [dict(r._asdict()) | {'ts_end': str(r.ts_end)}
                                                        for r in resend.head(5).itertuples(index=False)]}

    # ---- R4 lineage inheritance
    lin = raw.get('LINEAGE', pd.DataFrame(columns=['PARENT_WERKS', 'PARENT_MATNR', 'PARENT_CHARG', 'CHILD_WERKS',
                                                   'CHILD_MATNR', 'CHILD_CHARG', 'RELATION', 'TS']))
    lin = lin.assign(parent=lambda d: d['PARENT_WERKS'] + '|' + d['PARENT_MATNR'] + '|' + d['PARENT_CHARG'],
                     child=lambda d: d['CHILD_WERKS'] + '|' + d['CHILD_MATNR'] + '|' + d['CHILD_CHARG'])
    inh = []
    for r in lin.itertuples():
        up = E[(E['case_id'] == r.parent) & (E['activity'] == 'Manufacturing Executed')].copy()
        up['case_id'] = r.child
        up['inherited_from'] = r.parent
        inh.append(up)
    if inh:
        E = pd.concat([E] + inh, ignore_index=True)
    dq['rules']['R4_lineage'] = {'links': int(len(lin)), 'splits': int((lin['RELATION'] == 'split').sum()),
                                 'merges': int((lin['RELATION'] == 'merge').sum()),
                                 'inherited_events': int(sum(len(x) for x in inh)),
                                 'lineage_parents_excluded_from_release_kpis': int(lin['parent'].nunique())}

    # ---- R6 start after end
    bad = E['ts_start'].notna() & (E['ts_start'] > E['ts_end'])
    E.loc[bad, 'ts_start'] = pd.NaT
    E.loc[bad, 'start_source'] = 'none'
    dq['rules']['R6_start_after_end_dropped'] = int(bad.sum())

    # ---- R1 start coverage per duration activity
    cov = {}
    for act in C.DURATION_ACTIVITIES + ['Manufacturing Executed']:
        d = E[E['activity'] == act]
        vc = d['start_source'].value_counts().to_dict()
        cov[act] = {'events': int(len(d)), 'explicit': int(vc.get('explicit', 0)),
                    'status_log': int(vc.get('status_log', 0)), 'none': int(vc.get('none', 0)),
                    'coverage_pct': round(100 * (1 - vc.get('none', 0) / max(len(d), 1)), 1)}
    dq['rules']['R1_start_times'] = cov

    # ---- R5 crosswalk summary
    xs = xw.groupby(['source_system', 'method']).size().reset_index(name='ids')
    dq['rules']['R5_crosswalk'] = {
        'distinct_source_ids': int(len(xw)),
        'by_method': [dict(r._asdict()) for r in xs.itertuples(index=False)],
        'included_min_conf': C.MATCH_MIN_CONF,
        'rows_excluded': excluded_rows,
        'unmatched_examples': xw[xw['confidence'] < C.MATCH_MIN_CONF].head(8)[['source_system', 'plant', 'source_id', 'method']]
                              .to_dict('records')}

    order = {a: i for i, a in enumerate(C.ACT_ORDER)}
    E['_o'] = E['activity'].map(order)
    E = E.sort_values(['case_id', 'ts_end', '_o']).drop(columns='_o').reset_index(drop=True)
    dq['events'] = int(len(E))
    dq['cases_in_log'] = int(E['case_id'].nunique())
    return E, xw, lin, dq
