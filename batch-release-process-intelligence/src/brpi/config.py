"""Static configuration of the synthetic scenario and of the analysis.

Everything here is synthetic and illustrative: site names, materials, targets and the
intervention / exceptional-event register are made up for the demo.
"""
from datetime import datetime

SEED = 20260601

PERIOD_START = datetime(2026, 1, 5)
PERIOD_END_PRODUCTION = datetime(2026, 9, 22)
CUTOFF = datetime(2026, 9, 30, 23, 59)   # extract cut-off: nothing after this exists in the data

SITES = {
    '1100': {'name': 'Site A', 'label': 'Site A (plant 1100)'},
    '2200': {'name': 'Site B', 'label': 'Site B (plant 2200)'},
}

# target_days = illustrative internal release-cycle target per product (sterile products carry a
# 14-day sterility test, so their target is longer).
PRODUCTS = {
    'MAT-100010': {'name': 'Tablet 10 mg', 'family': 'Oral solid', 'target_days': 9.0},
    'MAT-100020': {'name': 'Capsule 25 mg', 'family': 'Oral solid', 'target_days': 9.0},
    'MAT-200030': {'name': 'Injection 5 mL', 'family': 'Sterile', 'target_days': 19.0},
    'MAT-200040': {'name': 'Lyophilised vial', 'family': 'Sterile', 'target_days': 21.0},
}
SITE_PRODUCTS = {
    '1100': ['MAT-100010', 'MAT-100020', 'MAT-200030'],
    '2200': ['MAT-100020', 'MAT-200030', 'MAT-200040'],
}

# Activities of the event log, in expected-path order. role = the organisational role that
# performs the activity (used for hand-off counting).
ACTIVITIES = [
    ('Manufacturing Executed', 'Production'),
    ('Goods Receipt', 'Warehouse'),
    ('Inspection Lot Created', 'QC Lab'),
    ('QC Results Recorded', 'QC Lab'),
    ('Batch Record Completed', 'Production'),
    ('Batch Record Review', 'QA Operations'),
    ('Batch Record Returned', 'QA Operations'),
    ('Batch Record Corrected', 'Production'),
    ('Deviation Raised', 'QA Compliance'),
    ('Deviation Closed', 'QA Compliance'),
    ('Deviation Reopened', 'QA Compliance'),
    ('QA Disposition Review', 'QA Release'),
    ('QA Query Raised', 'QA Release'),
    ('Usage Decision', 'QA Release'),
]
ROLE = dict(ACTIVITIES)
ACT_ORDER = [a for a, _ in ACTIVITIES]

# Expected ("happy") path. QC and documentation run in parallel, so conformance is checked with
# declarative rules (presence once + precedence), not a single sequence.
EXPECTED_ONCE = ['Manufacturing Executed', 'Goods Receipt', 'Inspection Lot Created', 'QC Results Recorded',
                 'Batch Record Completed', 'Batch Record Review', 'QA Disposition Review', 'Usage Decision']
EXCEPTION_ACTIVITIES = ['Batch Record Returned', 'Batch Record Corrected', 'Deviation Raised', 'Deviation Closed',
                        'Deviation Reopened', 'QA Query Raised']
# Activities with a duration inside the release window (the rest are instantaneous milestones).
DURATION_ACTIVITIES = ['QC Results Recorded', 'Batch Record Review', 'QA Disposition Review']

INTERVENTIONS = [
    {'id': 'INT-01', 'site': '1100', 'date': '2026-06-01',
     'title': 'Quality-documentation pre-check before QA batch record review',
     'owner': 'QA Operations lead, Site A (synthetic)',
     'target_kpis': ['doc_rework', 'qa_wait_d', 'cycle_d'],
     'pre_window': ['2026-03-01', '2026-05-31'], 'post_window': ['2026-06-01', '2026-08-31']},
]

EXCEPTIONAL_EVENTS = [
    {'id': 'EXC-2026-01', 'site': '1100', 'start': '2026-03-09', 'end': '2026-03-13', 'category': 'Material/supplier', 'type': 'Production disruption',
     'title': 'Excipient lot quarantined by supplier notification',
     'rule': 'deviation notification (QMEL) referencing EXC-2026-01'},
    {'id': 'EXC-2026-02', 'site': '2200', 'start': '2026-08-10', 'end': '2026-08-21', 'category': 'Environmental monitoring', 'type': 'Production disruption',
     'title': 'HVAC excursion in Grade B filling area',
     'rule': 'deviation notification (QMEL) referencing EXC-2026-02'},
]

# Crosswalk: matches below this confidence are excluded from the event log and reported.
MATCH_MIN_CONF = 0.8

FRAMEWORK_DRAFT_NOTE = ('DRAFT mapping prepared from public framework texts for discussion. It must be reviewed and '
                        'signed off by a qualified GMP / QA subject-matter expert before any use.')
