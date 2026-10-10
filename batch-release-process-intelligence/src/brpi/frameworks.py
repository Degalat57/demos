"""Framework mapping (DRAFT for SME sign-off) and an APQC-style L1-L4 hierarchy for Batch Review & Release.

Three kinds of statement are kept apart everywhere:
  reference  what the framework expects (paraphrased from the public text; not legal advice)
  evidence   what the data shows (a deterministic check over the event log)
  inference  what the system concludes from the evidence (status), to be confirmed by a human
"""
from . import config as C

HIERARCHY = {
    'note': ('APQC-style L1-L4 hierarchy derived from the event log. Element names and IDs must be aligned to the '
             'licensed APQC Life Sciences PCF during the PoC (DRAFT).'),
    'L1': 'Manufacturing quality (deliver physical product)',
    'L2': 'Batch review & release',
    'L3': [
        {'name': 'Manufacturing completion', 'L4': ['Manufacturing Executed', 'Goods Receipt']},
        {'name': 'QC testing & results', 'L4': ['Inspection Lot Created', 'QC Results Recorded']},
        {'name': 'Batch record review', 'L4': ['Batch Record Completed', 'Batch Record Review', 'Batch Record Returned',
                                               'Batch Record Corrected']},
        {'name': 'Deviation management', 'L4': ['Deviation Raised', 'Deviation Closed', 'Deviation Reopened']},
        {'name': 'QA disposition & release', 'L4': ['QA Disposition Review', 'QA Query Raised', 'Usage Decision']},
    ],
}

# Each row: framework, reference (paraphrase), L3 area, evidence check key, evidence description, rule for status
MAPPING = [
    {'framework': 'EU GMP Annex 16', 'ref': 'QP certification and batch release',
     'expectation': 'Before certification, all required testing is complete and results are available.',
     'area': 'QA disposition & release', 'check': 'ud_after_qc',
     'evidence': '% of usage decisions recorded after the last QC result', 'aligned_if': '== 100%'},
    {'framework': 'EU GMP Annex 16', 'ref': 'QP certification and batch release',
     'expectation': 'Deviations affecting the batch are assessed and closed (or justified) before certification.',
     'area': 'Deviation management', 'check': 'ud_after_dev',
     'evidence': '% of batches with deviations whose usage decision follows deviation closure', 'aligned_if': '== 100%'},
    {'framework': 'EU GMP Annex 16', 'ref': 'QP certification and batch release',
     'expectation': 'QA disposition review is based on a complete batch record and closed exceptions.',
     'area': 'QA disposition & release', 'check': 'seq_exception',
     'evidence': '% of batches where QA disposition review started before deviation closure', 'aligned_if': '== 0%'},
    {'framework': 'ICH Q10', 'ref': '3.2.1 Process performance and product quality monitoring system',
     'expectation': 'Process performance is monitored with appropriate measures; sources of variation are identified.',
     'area': 'Batch review & release (L2)', 'check': 'monitoring',
     'evidence': 'Release KPIs computed per batch with data coverage; variation (P90) and drivers reported', 'aligned_if': 'coverage >= 80%'},
    {'framework': 'ICH Q10', 'ref': '3.2.2 Corrective action and preventive action (CAPA) system',
     'expectation': 'Deviations are investigated and CAPAs taken; effectiveness of actions is evaluated.',
     'area': 'Deviation management', 'check': 'reopen',
     'evidence': '% of deviations reopened after closure; recorded interventions with a measured effect', 'aligned_if': 'reopened <= 5%'},
    {'framework': 'ICH Q10', 'ref': '3.2.4 Management review of process performance and product quality',
     'expectation': 'Management reviews process performance and the outcome of improvement actions.',
     'area': 'Batch review & release (L2)', 'check': 'review',
     'evidence': 'Maturity score with dimension contributions; intervention pre/post results available', 'aligned_if': 'available'},
    {'framework': 'ICH Q9(R1)', 'ref': 'Quality risk management (identification, evaluation, control, review)',
     'expectation': 'Risks to quality and timely release are identified, evaluated and controlled; level of formality is proportionate.',
     'area': 'Deviation management', 'check': 'risk',
     'evidence': 'Deviation categories and exceptional events registered and linked to batches; risk-ranked opportunities', 'aligned_if': 'events linked'},
    {'framework': 'APQC Life Sciences PCF', 'ref': 'Process hierarchy and measures (L1-L4, DRAFT)',
     'expectation': 'Process is classified in a standard hierarchy with comparable performance measures.',
     'area': 'Batch review & release (L2)', 'check': 'hierarchy',
     'evidence': 'All event-log activities mapped to L3/L4; KPIs defined per level', 'aligned_if': 'all mapped'},
    {'framework': 'Internal framework', 'ref': 'SOPs, internal targets, best-site practice',
     'expectation': 'Release within the internal target per product; best-site practice adopted.',
     'area': 'Batch review & release (L2)', 'check': 'internal',
     'evidence': '% of batches within internal target; gap to internal best site-quarter', 'aligned_if': 'on-time >= 80%'},
]


def assess(T, mask=None):
    """Evaluate every mapping row against the data. Returns rows with value + inferred status."""
    d = T if mask is None else T[mask]
    c = d[d['closed']]
    n = max(len(c), 1)
    dev = c[c['has_dev']]
    vals = {
        'ud_after_qc': 100 * float(c['ud_after_qc'].mean()),
        'ud_after_dev': 100 * float(dev['ud_after_dev'].mean()) if len(dev) else 100.0,
        'seq_exception': 100 * float(dev['seq_exception'].mean()) if len(dev) else 0.0,
        'monitoring': 100 * float(c['split_ok'].mean()),
        'reopen': 100 * float(dev['dev_reopened'].mean()) if len(dev) else 0.0,
        'internal': 100 * float(c['ontime'].mean()),
    }
    out = []
    for m in MAPPING:
        k = m['check']
        v = vals.get(k)
        if k == 'seq_exception':
            status = 'aligned' if v == 0 else 'investigate'
            ev = '%.1f%% of %d batches with deviations' % (v, len(dev))
        elif k in ('ud_after_qc', 'ud_after_dev'):
            status = 'aligned' if v >= 99.95 else 'investigate'
            ev = '%.1f%% of %d batches' % (v, n if k == 'ud_after_qc' else len(dev))
        elif k == 'monitoring':
            status = 'aligned' if v >= 80 else 'missing evidence'
            ev = 'start-time coverage for waiting/processing split: %.1f%%' % v
        elif k == 'reopen':
            status = 'aligned' if v <= 5 else 'investigate'
            ev = '%.1f%% of batches with deviations had a reopened deviation' % v
        elif k == 'internal':
            status = 'aligned' if v >= 80 else 'investigate'
            ev = '%.1f%% released within target' % v
        elif k == 'review':
            status, ev = 'aligned', 'maturity + intervention tracking produced by this tool'
        elif k == 'risk':
            status, ev = 'missing evidence', ('exceptional events linked via deviation references; formal risk '
                                              'assessments (FMEA etc.) are not in the extract')
        else:
            status, ev = 'aligned', '%d activities mapped to %d L3 areas' % (sum(len(x['L4']) for x in HIERARCHY['L3']),
                                                                           len(HIERARCHY['L3']))
        out.append({**m, 'value': v, 'evidence_value': ev, 'status': status})
    return out

