"""Deterministic KPI engine: event log -> one row per case (batch) -> aggregate KPIs.

No LLM is involved anywhere in this module. Definitions (also in README):

  cycle_d        release cycle time = final usage decision - last order confirmation (manufacturing complete)
  processing_d   union of activity intervals (ts_start..ts_end) inside the release window; overlapping
                 parallel work (QC testing and QA documentation review) is counted once, so waiting >= 0.
                 Only for cases where every duration activity has a start ("split" cases).
  waiting_d      cycle_d - processing_d (split cases only); other cases are "elapsed, unsplit"
  segments       telescoping critical-path decomposition (always sums exactly to cycle_d):
                   pre_qa  = ready-for-QA - manufacturing complete, attributed to the binding path
                             (documentation / QC results / deviation closure, whichever finished last)
                   qa_stage = last QA disposition review end - ready-for-QA  (= qa_wait + qa_review)
                   approval = usage decision - QA review end
  rework         any repeated activity: second batch record review, repeated QA review, second inspection
                 lot (retest), reopened deviation, changed usage decision
  rft            right first time: no deviation AND no rework AND first usage decision = accept ('A')
  handoffs       number of consecutive role changes along the ordered trace
"""
import numpy as np
import pandas as pd

from . import config as C

DAY = 86400.0


def _d(a, b):
    if pd.isna(a) or pd.isna(b):
        return np.nan
    return (b - a).total_seconds() / DAY


def interval_union_days(intervals, lo, hi):
    """Total length in days of the union of [s, e] intervals clipped to [lo, hi]."""
    iv = sorted((max(s, lo), min(e, hi)) for s, e in intervals if pd.notna(s) and pd.notna(e))
    iv = [(s, e) for s, e in iv if e > s]
    total, cur_s, cur_e = 0.0, None, None
    for s, e in iv:
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += (cur_e - cur_s).total_seconds()
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += (cur_e - cur_s).total_seconds()
    return total / DAY


def count_handoffs(roles):
    return int(sum(1 for a, b in zip(roles, roles[1:]) if a != b))


def conformance(acts, ev):
    """Declarative expected-path check. Returns list of issue strings (empty = conformant)."""
    issues = []
    cnt = pd.Series(acts).value_counts().to_dict()
    for a in C.EXPECTED_ONCE:
        n = cnt.get(a, 0)
        if a == 'Manufacturing Executed' and n >= 1:
            continue                            # merges legitimately inherit several
        if n == 0:
            issues.append('missing: ' + a)
        elif n > 1:
            issues.append('repeated: ' + a)
    for a in C.EXCEPTION_ACTIVITIES:
        if cnt.get(a, 0):
            issues.append('extra: ' + a)
    return issues


def case_table(E, lin=None):
    """One row per release case (cases with an inspection lot). Lineage parents are excluded."""
    parents = set(lin['parent']) if lin is not None and len(lin) else set()
    children = dict(zip(lin['child'], lin['RELATION'])) if lin is not None and len(lin) else {}
    exc_by_case = {}
    rows, trans = [], {}
    for case, g in E.groupby('case_id', sort=False):
        acts = g['activity'].tolist()
        if 'Inspection Lot Created' not in acts:
            continue
        plant, mat, charg = case.split('|')
        A = lambda a: g[g['activity'] == a]  # noqa: E731
        mfg = A('Manufacturing Executed')['ts_end'].max()
        ud = A('Usage Decision')
        closed = len(ud) > 0
        r = {'case_id': case, 'site': plant, 'material': mat, 'family': C.PRODUCTS[mat]['family'], 'batch': charg,
             'target_d': C.PRODUCTS[mat]['target_days'], 'lineage': children.get(case, 'none'),
             'mfg_complete': mfg, 'closed': closed, 'n_events': len(g)}
        r['ud_first_code'] = ud['ud_code'].iloc[0] if closed else ''
        r['ud_final_code'] = ud['ud_code'].iloc[-1] if closed else ''
        udt = ud['ts_end'].max() if closed else pd.NaT
        r['ud_ts'] = udt
        r['cycle_d'] = _d(mfg, udt)
        # flags
        n = g['activity'].value_counts().to_dict()
        r['n_dev'] = n.get('Deviation Raised', 0)
        r['has_dev'] = r['n_dev'] > 0
        r['doc_rework'] = n.get('Batch Record Review', 0) > 1 or n.get('Batch Record Returned', 0) > 0
        r['doc_loops'] = n.get('Batch Record Returned', 0)
        r['qa_repeat'] = n.get('QA Disposition Review', 0) > 1 or n.get('QA Query Raised', 0) > 0
        r['retest'] = n.get('Inspection Lot Created', 0) > 1
        r['dev_reopened'] = n.get('Deviation Reopened', 0) > 0
        r['ud_changed'] = n.get('Usage Decision', 0) > 1
        r['rework'] = bool(r['doc_rework'] or r['qa_repeat'] or r['retest'] or r['dev_reopened'] or r['ud_changed'])
        r['rft'] = bool(closed and not r['has_dev'] and not r['rework'] and r['ud_first_code'] == 'A')
        r['handoffs'] = count_handoffs(g['role'].tolist())
        r['variant'] = ' > '.join(acts)
        issues = conformance(acts, g)
        r['conformant'] = len(issues) == 0
        r['issues'] = '; '.join(issues)
        r['min_match_conf'] = float(g['match_conf'].min())
        # milestones for the decomposition
        doc_done = A('Batch Record Review')['ts_end'].max()
        qc_done = A('QC Results Recorded')['ts_end'].max()
        dev_done = A('Deviation Closed')['ts_end'].max() if r['has_dev'] else pd.NaT
        br_c = A('Batch Record Completed')['ts_end'].min()
        qa = A('QA Disposition Review')
        qa_end = qa['ts_end'].max()
        cand = {'Documentation': doc_done, 'QC results': qc_done, 'Deviation closure': dev_done}
        cand = {k: v for k, v in cand.items() if pd.notna(v)}
        ready = max(cand.values()) if cand else pd.NaT
        r['binding'] = max(cand, key=lambda k: cand[k]) if cand else ''
        r['qc_delay_d'] = _d(mfg, qc_done)
        r['doc_complete_d'] = _d(mfg, br_c)
        r['doc_review_done_d'] = _d(mfg, doc_done)
        devs = g[g['activity'].isin(['Deviation Raised', 'Deviation Closed'])]
        r['dev_res_d'] = _d(devs[devs['activity'] == 'Deviation Raised']['ts_end'].min(), dev_done) if r['has_dev'] else np.nan
        # exceptional-event link and sequence control
        r['seq_exception'] = bool(r['has_dev'] and len(qa) and pd.notna(dev_done) and
                                  pd.notna(qa['ts_start'].min()) and qa['ts_start'].min() < dev_done)
        ud_first = ud['ts_end'].min() if closed else pd.NaT
        r['ud_after_qc'] = bool(closed and pd.notna(qc_done) and ud_first >= qc_done)
        r['ud_after_dev'] = bool(closed and (not r['has_dev'] or (pd.notna(dev_done) and ud_first >= dev_done)))
        r['compliance_ok'] = bool(closed and not r['seq_exception'] and r['ud_after_qc'] and r['ud_after_dev'] and
                                  all(k in n for k in ['QC Results Recorded', 'Batch Record Review', 'QA Disposition Review'])
                                  and (pd.isna(dev_done) or dev_done <= udt) and qa_end <= udt)
        if closed and pd.notna(ready) and pd.notna(qa_end):
            r['seg_pre_qa'] = _d(mfg, ready)
            r['seg_qa_stage'] = _d(ready, qa_end)
            r['seg_approval'] = _d(qa_end, udt)
            for k in ['Documentation', 'QC results', 'Deviation closure']:
                r['seg_' + k.split()[0].lower()] = r['seg_pre_qa'] if r['binding'] == k else 0.0
            if qa['ts_start'].notna().all():
                rev = float(sum(_d(s, e) for s, e in zip(qa['ts_start'], qa['ts_end'])))
                r['qa_review_d'] = rev
                r['qa_wait_d'] = r['seg_qa_stage'] - rev
            else:
                r['qa_review_d'] = r['qa_wait_d'] = np.nan
        # processing / waiting split (R1: only where all starts exist)
        if closed:
            win = g[g['activity'].isin(C.DURATION_ACTIVITIES) & (g['ts_end'] > mfg) & (g['ts_end'] <= udt)]
            r['split_ok'] = bool(win['ts_start'].notna().all())
            if r['split_ok']:
                r['processing_d'] = interval_union_days(zip(win['ts_start'], win['ts_end']), mfg, udt)
                r['waiting_d'] = r['cycle_d'] - r['processing_d']
            else:
                r['processing_d'] = r['waiting_d'] = np.nan
        # transitions (directly-follows) with waiting hours
        ts_s = g['ts_start'].where(g['ts_start'].notna(), g['ts_end']).tolist()
        ts_e = g['ts_end'].tolist()
        trans[case] = [(acts[i], acts[i + 1], max(0.0, (ts_s[i + 1] - ts_e[i]).total_seconds() / 3600.0))
                       for i in range(len(acts) - 1)]
        rows.append(r)
    T = pd.DataFrame(rows)
    T = T[~T['case_id'].isin(parents)].reset_index(drop=True)
    T['month'] = T['mfg_complete'].dt.strftime('%Y-%m')
    T['site_name'] = T['site'].map(lambda s: C.SITES[s]['name'])
    T['product'] = T['material'].map(lambda m: C.PRODUCTS[m]['name'])
    T['ontime'] = T['cycle_d'] <= T['target_d']
    return T, trans


def attach_registers(T, E, raw):
    """Link cases to the exceptional-event register (via QMEL EVENT_REF) and intervention exposure."""
    q = raw['QMEL']
    ref = {}
    for r in q.itertuples():
        if r.EVENT_REF:
            ref['%s|%s|%s' % (r.WERKS, r.MATNR, r.CHARG)] = r.EVENT_REF
    T['exc_event'] = T['case_id'].map(ref).fillna('')
    for iv in C.INTERVENTIONS:
        d = pd.Timestamp(iv['date'])
        T[iv['id'] + '_exposed'] = (T['site'] == iv['site']) & (T['mfg_complete'] >= d)
    return T


def aggregate(T, mask=None):
    """Aggregate KPIs over closed cases (optionally filtered). Returns dict with value, n and coverage."""
    d = T if mask is None else T[mask]
    c = d[d['closed']]
    n = len(c)
    out = {'n_cases': int(len(d)), 'n_closed': int(n), 'n_open': int(len(d) - n)}
    if n == 0:
        return out
    split = c[c['split_ok']]
    qa_cov = c['qa_wait_d'].notna()
    out.update({
        'cycle_mean_d': float(c['cycle_d'].mean()), 'cycle_median_d': float(c['cycle_d'].median()),
        'cycle_p90_d': float(c['cycle_d'].quantile(0.9)),
        'target_mean_d': float(c['target_d'].mean()),
        'ontime_pct': 100 * float(c['ontime'].mean()),
        'processing_mean_d': float(split['processing_d'].mean()) if len(split) else None,
        'waiting_mean_d': float(split['waiting_d'].mean()) if len(split) else None,
        'waiting_share_pct': 100 * float(split['waiting_d'].sum() / split['cycle_d'].sum()) if len(split) else None,
        'split_coverage_pct': 100 * len(split) / n,
        'qa_wait_mean_d': float(c.loc[qa_cov, 'qa_wait_d'].mean()) if qa_cov.any() else None,
        'qa_wait_coverage_pct': 100 * float(qa_cov.mean()),
        'qc_delay_mean_d': float(c['qc_delay_d'].mean()),
        'dev_res_mean_d': float(c['dev_res_d'].mean()) if c['has_dev'].any() else None,
        'deviation_rate_pct': 100 * float(c['has_dev'].mean()),
        'rework_pct': 100 * float(c['rework'].mean()),
        'doc_rework_pct': 100 * float(c['doc_rework'].mean()),
        'qa_repeat_pct': 100 * float(c['qa_repeat'].mean()),
        'rft_pct': 100 * float(c['rft'].mean()),
        'handoffs_mean': float(c['handoffs'].mean()),
        'conformance_pct': 100 * float(c['conformant'].mean()),
        'compliance_pct': 100 * float(c['compliance_ok'].mean()),
    })
    return out


def decompose(T, mask=None):
    """Outcome KPI -> process KPI drivers: mean segment days that sum exactly to mean cycle time."""
    d = T if mask is None else T[mask]
    c = d[d['closed'] & d['seg_qa_stage'].notna()]
    segs = {'Documentation (incl. rework) binding': 'seg_documentation', 'QC results binding': 'seg_qc',
            'Deviation closure binding': 'seg_deviation', 'QA queue + disposition review': 'seg_qa_stage',
            'Usage-decision approval wait': 'seg_approval'}
    out = {k: float(c[v].mean()) for k, v in segs.items()}
    out['_cycle_mean_d'] = float(c['cycle_d'].mean())
    out['_n'] = int(len(c))
    return out
