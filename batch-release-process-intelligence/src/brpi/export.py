"""Run the whole pipeline and export processed tables + the static site's data bundle (assets/data.js)."""
import json
import math
from pathlib import Path

import pandas as pd

from . import analysis as AN
from . import config as C
from . import copilot as CP
from . import frameworks as FW
from . import mining as MN
from .eventlog import build_event_log, load_raw
from .generate import generate
from .kpis import aggregate, attach_registers, case_table, decompose


def _clean(o):
    if isinstance(o, float):
        return None if math.isnan(o) else round(o, 4)
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (pd.Timestamp,)):
        return o.strftime('%Y-%m-%d %H:%M')
    if hasattr(o, 'item'):
        return _clean(o.item())
    return o


def build(root, regenerate=True):
    root = Path(root)
    data = root / 'data'
    if regenerate or not (data / 'raw' / 'AFRU.csv').exists():
        generate(data)
    raw = load_raw(data / 'raw')
    E, xw, lin, dq = build_event_log(raw)
    T, trans = case_table(E, lin)
    T = attach_registers(T, E, raw)
    return raw, E, xw, lin, dq, T, trans


def export(root, regenerate=True):
    root = Path(root)
    raw, E, xw, lin, dq, T, trans = build(root, regenerate)
    proc = root / 'data' / 'processed'
    proc.mkdir(parents=True, exist_ok=True)
    E.to_csv(proc / 'events.csv', index=False)
    xw.to_csv(proc / 'crosswalk.csv', index=False)
    T.drop(columns=['variant']).to_csv(proc / 'cases.csv', index=False, float_format='%.6f')

    # registers and analyses
    iv = AN.intervention_effect(T, C.INTERVENTIONS[0], True)
    iv_all = AN.intervention_effect(T, C.INTERVENTIONS[0], False)
    sus = {'INT-01': bool(iv['sustained'])}
    turns = CP.run_transcript(T)
    fw = FW.assess(T, T['month'] <= '2026-08')
    vt, nvar = MN.variants(T)
    summary = {
        'overall': aggregate(T), 'overall_complete_months': aggregate(T, T['month'] <= '2026-08'),
        'decomposition': decompose(T, T['month'] <= '2026-08'),
        'maturity_q1': AN.maturity(T, T['month'].between('2026-01', '2026-03'), sus),
        'maturity_jun_aug': AN.maturity(T, T['month'].between('2026-06', '2026-08'), sus),
        'intervention': iv, 'intervention_incl_exceptional': iv_all,
        'opportunities': AN.opportunities(T, T['month'].between('2026-06', '2026-08')),
        'fast_slow': AN.fast_slow(T, T['month'] <= '2026-08'), 'facts': AN.facts(T, T['month'] <= '2026-08'),
        'scenario_exc02_jun_aug': AN.scenario_exclude(T, ['EXC-2026-02'], T['month'].between('2026-06', '2026-08')),
        'variants_total': nvar, 'loops': MN.loops(T), 'conformance': MN.conformance_summary(T),
    }
    summary['maturity_change'] = AN.maturity_change(summary['maturity_q1'], summary['maturity_jun_aug'])
    (proc / 'dq_report.json').write_text(json.dumps(_clean(dq), indent=1, default=str))
    (proc / 'kpi_summary.json').write_text(json.dumps(_clean(summary), indent=1, default=str))
    (proc / 'copilot_transcript.json').write_text(json.dumps(_clean(turns), indent=1, default=str))
    (proc / 'copilot_tools.json').write_text(json.dumps(CP.tool_specs(), indent=1))
    pd.DataFrame(fw).to_csv(proc / 'framework_mapping.csv', index=False, float_format='%.4f')

    # ---------------- site bundle
    acts = C.ACT_ORDER
    ai = {a: i for i, a in enumerate(acts)}
    vlist = sorted(T['variant'].unique(), key=lambda v: -int((T['variant'] == v).sum()))
    vi = {v: i for i, v in enumerate(vlist)}
    cols = ['id', 'site', 'mat', 'month', 'mfg', 'closed', 'cycle', 'target', 'proc', 'wait', 'split', 'segDoc', 'segQc',
            'segDev', 'segQa', 'segAppr', 'qaWait', 'qaRev', 'qcDelay', 'devRes', 'hasDev', 'nDev', 'docRw', 'docLoops',
            'qaRep', 'retest', 'devReo', 'udChg', 'rework', 'rft', 'handoffs', 'conf', 'compl', 'seqExc', 'exc', 'variant',
            'binding', 'ontime', 'lineage', 'issues', 'batch', 'family', 'udAfterQc', 'udAfterDev', 'int1']
    src = ['case_id', 'site', 'material', 'month', 'mfg_complete', 'closed', 'cycle_d', 'target_d', 'processing_d', 'waiting_d',
           'split_ok', 'seg_documentation', 'seg_qc', 'seg_deviation', 'seg_qa_stage', 'seg_approval', 'qa_wait_d', 'qa_review_d',
           'qc_delay_d', 'dev_res_d', 'has_dev', 'n_dev', 'doc_rework', 'doc_loops', 'qa_repeat', 'retest', 'dev_reopened',
           'ud_changed', 'rework', 'rft', 'handoffs', 'conformant', 'compliance_ok', 'seq_exception', 'exc_event', 'variant',
           'binding', 'ontime', 'lineage', 'issues', 'batch', 'family', 'ud_after_qc', 'ud_after_dev', 'INT-01_exposed']
    rows = []
    for r in T[src].itertuples(index=False):
        row = []
        for c, v in zip(src, r):
            if c == 'variant':
                v = vi[v]
            elif c == 'mfg_complete':
                v = v.strftime('%Y-%m-%d')
            elif isinstance(v, bool) or (hasattr(v, 'dtype') and str(getattr(v, 'dtype', '')) == 'bool'):
                v = 1 if v else 0
            elif isinstance(v, float):
                v = None if math.isnan(v) else round(v, 3)
            row.append(_clean(v))
        rows.append(row)
    tr = {cid: [[ai[a], ai[b], round(w, 1)] for a, b, w in trans[cid]] for cid in T['case_id']}
    last_act = E.groupby('case_id')['activity'].last().to_dict()
    ob = AN.open_batches(T)
    openb = [{'id': r.case_id, 'site': r.site, 'product': r.product, 'batch': r.batch, 'age_d': round(r.age_d, 1),
              'target_d': r.target_d, 'at_risk': bool(r.at_risk), 'last_step': last_act.get(r.case_id, ''),
              'has_dev': bool(r.has_dev), 'doc_rework': bool(r.doc_rework)} for r in ob.itertuples()]
    q = raw['QMEL']
    reo = set(raw['STATUS_LOG'].query("OBJ_TYPE == 'QMEL' and STAT == 'REOPENED'")['OBJ_KEY'])
    ids = set(T['case_id'])
    devs = []
    for r in q.itertuples():
        cid = '%s|%s|%s' % (r.WERKS, r.MATNR, r.CHARG)
        if cid not in ids:
            continue
        a, b = pd.to_datetime(r.QMDAT_TS), pd.to_datetime(r.QMDAB_TS) if r.QMDAB_TS else None
        devs.append([cid, r.CATEGORY, None if b is None else round((b - a).total_seconds() / 86400, 2),
                     r.CAPA_REQUIRED == 'Y', r.EVENT_REF, r.QMNUM in reo])
    bundle = {
        'deviations': devs,
        'meta': {'generated_from': 'synthetic SAP-style extract (seed %d)' % C.SEED, 'cutoff': C.CUTOFF.strftime('%Y-%m-%d'),
                 'period': [C.PERIOD_START.strftime('%Y-%m-%d'), C.CUTOFF.strftime('%Y-%m-%d')],
                 'n_events': int(len(E)), 'n_cases': int(len(T)), 'complete_through': '2026-08'},
        'sites': C.SITES, 'products': C.PRODUCTS, 'activities': acts, 'roles': [C.ROLE[a] for a in acts],
        'expected_once': C.EXPECTED_ONCE, 'cols': cols, 'cases': rows, 'trans': tr,
        'variants': [[ai[a] for a in v.split(' > ')] for v in vlist],
        'interventions': C.INTERVENTIONS, 'exceptional_events': C.EXCEPTIONAL_EVENTS,
        'intervention_result': iv, 'intervention_result_incl_exc': iv_all,
        'ci_sustained': {'INT-01': bool(iv['sustained'])},
        'maturity_dims': [{'key': k, 'label': l, 'weight': w, 'rule': r} for k, l, w, r in AN.MATURITY_DIMS],
        'bench_kpis': [{'key': k, 'label': l, 'unit': u, 'lower': lo} for k, l, u, lo in AN.BENCH_KPIS],
        'targets': AN.TARGETS, 'effort': AN.EFFORT,
        'framework': {'note': C.FRAMEWORK_DRAFT_NOTE, 'mapping': FW.MAPPING, 'hierarchy': FW.HIERARCHY},
        'dq': dq, 'crosswalk_examples': xw[xw['method'] != 'exact after normalisation'].head(30).to_dict('records'),
        'transcript': turns, 'tools': CP.tool_specs(), 'open_batches': openb, 'summary': summary,
        'sample_events': E[E['case_id'].isin(T[T['doc_rework'] & T['has_dev']]['case_id'].head(1))].assign(
            ts_start=lambda d: d['ts_start'].dt.strftime('%Y-%m-%d %H:%M'), ts_end=lambda d: d['ts_end'].dt.strftime('%Y-%m-%d %H:%M')
        ).fillna('').to_dict('records'),
    }
    js = 'window.BRPI = ' + json.dumps(_clean(bundle), separators=(',', ':'), default=str) + ';\n'
    (root / 'assets').mkdir(exist_ok=True)
    (root / 'assets' / 'data.js').write_text(js)
    return {'events': len(E), 'cases': len(T), 'closed': int(T['closed'].sum()), 'data_js_kb': len(js) // 1024,
            'transcript_grounded': all(t['grounded'] for t in turns)}
