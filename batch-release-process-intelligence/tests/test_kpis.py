"""Exact KPI definitions on hand-built fixtures (values computed by hand in the comments)."""
import math

import pandas as pd
import pytest

from brpi.kpis import aggregate, count_handoffs, decompose, interval_union_days
from conftest import build

T0 = pd.Timestamp


def approx(x):
    return pytest.approx(x, abs=1e-9)


def test_cycle_processing_waiting_segments(ex):
    # mfg complete 03-03 00:00, UD 03-08 00:00 -> cycle 5.0 d
    # QC 03-03 08:00..03-05 08:00 (2 d), BR review 03-04 08..12 (inside QC, counted once), QA 03-06 08..12 (4 h)
    ex.batch('B26A00001')
    *_, T, _ = build(ex)
    r = T.iloc[0]
    assert r['cycle_d'] == approx(5.0)
    assert r['processing_d'] == approx(2 + 4 / 24)
    assert r['waiting_d'] == approx(5.0 - 2 - 4 / 24)
    # ready-for-QA = last QC result 03-05 08:00 (binding: QC results)
    assert r['binding'] == 'QC results'
    assert r['seg_pre_qa'] == approx(2 + 8 / 24) and r['seg_qc'] == approx(2 + 8 / 24) and r['seg_documentation'] == 0
    assert r['seg_qa_stage'] == approx(1 + 4 / 24) and r['qa_review_d'] == approx(4 / 24) and r['qa_wait_d'] == approx(1.0)
    assert r['seg_approval'] == approx(1.5)
    assert r['seg_pre_qa'] + r['seg_qa_stage'] + r['seg_approval'] == approx(r['cycle_d'])
    assert r['qc_delay_d'] == approx(2 + 8 / 24) and r['doc_complete_d'] == approx(0.5)


def test_handoffs_and_conformance(ex):
    # roles: Production, Warehouse, QC Lab, Production, QA Operations, QC Lab, QA Release, QA Release -> 6 changes
    ex.batch('B26A00001')
    *_, T, _ = build(ex)
    assert T.iloc[0]['handoffs'] == 6
    assert T.iloc[0]['conformant'] and T.iloc[0]['issues'] == ''
    assert T.iloc[0]['rft'] and not T.iloc[0]['rework']


def test_rework_types_and_rft_is_not_100_minus_rework(ex):
    ex.batch('B26A00001')                                     # clean -> RFT
    ex.batch('B26A00002')                                     # deviation, no loop -> not RFT, not rework
    ex.add('QMEL', QMNUM='Q1', QMART='Q3', WERKS='1100', MATNR='MAT-100010', CHARG='B26A00002',
           QMDAT_TS='2026-03-02 20:00:00', QMDAB_TS='2026-03-05 20:00:00', CATEGORY='Equipment', CAPA_REQUIRED='N', EVENT_REF='')
    ex.batch('B26A00003', lot='LOT3')                         # second inspection lot -> retest rework
    ex.add('QALS', PRUEFLOS='LOT3B', WERK='1100', MATNR='MAT-100010', CHARG='B26A00003', HERKUNFT='89',
           ENSTEHDAT_TS='2026-03-05 10:00:00')
    ex.batch('B26A00004', lot='LOT4')                         # changed usage decision -> rework
    ex.add('QAVE', PRUEFLOS='LOT4', VCODE='A', VDATUM_TS='2026-03-09 00:00:00', KZART='change')
    ex.rows['QAVE'][-2]['VCODE'] = 'A2'
    *_, T, _ = build(ex)
    t = T.set_index('batch')
    assert t.loc['B26A00001', 'rft'] and not t.loc['B26A00001', 'rework']
    assert not t.loc['B26A00002', 'rft'] and not t.loc['B26A00002', 'rework'] and t.loc['B26A00002', 'has_dev']
    assert t.loc['B26A00003', 'retest'] and t.loc['B26A00003', 'rework']
    assert t.loc['B26A00004', 'ud_changed'] and t.loc['B26A00004', 'rework']
    assert t.loc['B26A00004', 'cycle_d'] == approx(6.0)        # final usage decision counts
    a = aggregate(T)
    assert a['rework_pct'] == approx(50.0) and a['rft_pct'] == approx(25.0)   # 100 - rework would be 50
    assert a['deviation_rate_pct'] == approx(25.0)
    # deviation closed 03-05 20:00 > QC done 03-05 08:00 -> deviation closure is binding
    assert t.loc['B26A00002', 'binding'] == 'Deviation closure'
    assert t.loc['B26A00002', 'dev_res_d'] == approx(3.0)


def test_qa_repeat_and_reopened_deviation(ex):
    ex.batch('B26A00001')
    ex.add('QMS_DISPOSITION', REC_ID='Q90', SITE='1100', QMS_BATCH_REF='B26A-00001', EVENT='QA_QUERY', TS_START='',
           TS_END='2026-03-06 12:30:00')
    ex.add('QMS_DISPOSITION', REC_ID='Q91', SITE='1100', QMS_BATCH_REF='B26A-00001', EVENT='DISP_REVIEW',
           TS_START='2026-03-07 08:00:00', TS_END='2026-03-07 10:00:00')
    ex.add('QMEL', QMNUM='Q5', QMART='Q3', WERKS='1100', MATNR='MAT-100010', CHARG='B26A00001',
           QMDAT_TS='2026-03-02 20:00:00', QMDAB_TS='2026-03-05 00:00:00', CATEGORY='Equipment', CAPA_REQUIRED='N', EVENT_REF='')
    ex.add('STATUS_LOG', STAT_ID=7, OBJ_TYPE='QMEL', OBJ_KEY='Q5', STAT='CLOSED', UDATE_TS='2026-03-03 20:00:00', SOURCE='CDHDR/CDPOS')
    ex.add('STATUS_LOG', STAT_ID=8, OBJ_TYPE='QMEL', OBJ_KEY='Q5', STAT='REOPENED', UDATE_TS='2026-03-04 08:00:00', SOURCE='CDHDR/CDPOS')
    *_, T, _ = build(ex)
    r = T.iloc[0]
    assert r['qa_repeat'] and r['dev_reopened'] and r['rework']
    # QA stage = QA end 03-07 10:00 - ready 03-05 08:00 = 2 d 2 h; review effort 4 h + 2 h
    assert r['seg_qa_stage'] == approx(2 + 2 / 24) and r['qa_review_d'] == approx(6 / 24)
    assert r['qa_wait_d'] == approx(2 + 2 / 24 - 6 / 24)


def test_sequence_exception_flags_compliance(ex):
    ex.batch('B26A00001')
    ex.add('QMEL', QMNUM='Q6', QMART='Q3', WERKS='1100', MATNR='MAT-100010', CHARG='B26A00001',
           QMDAT_TS='2026-03-02 20:00:00', QMDAB_TS='2026-03-06 10:00:00', CATEGORY='Equipment', CAPA_REQUIRED='N', EVENT_REF='')
    *_, T, _ = build(ex)
    r = T.iloc[0]   # QA review started 03-06 08:00, deviation closed 03-06 10:00
    assert r['seq_exception'] and not r['compliance_ok'] and r['ud_after_dev']


def test_open_case_excluded_from_cycle(ex):
    ex.batch('B26A00001').batch('B26A00002', ud=None)
    *_, T, _ = build(ex)
    a = aggregate(T)
    assert (a['n_cases'], a['n_closed'], a['n_open']) == (2, 1, 1)
    assert a['cycle_mean_d'] == approx(5.0)


def test_coverage_reported_per_kpi(ex):
    ex.batch('B26A00001').batch('B26A00002', qa=('', '2026-03-06 12:00:00'))
    *_, T, _ = build(ex)
    a = aggregate(T)
    assert a['qa_wait_coverage_pct'] == approx(50.0) and a['split_coverage_pct'] == approx(50.0)
    assert a['qa_wait_mean_d'] == approx(1.0)
    d = decompose(T)
    assert sum(v for k, v in d.items() if not k.startswith('_')) == approx(d['_cycle_mean_d'])


def test_interval_union_and_handoff_units():
    lo, hi = T0('2026-01-01'), T0('2026-01-10')
    iv = [(T0('2026-01-02'), T0('2026-01-04')), (T0('2026-01-03'), T0('2026-01-05')), (T0('2026-01-07'), T0('2026-01-08')),
          (T0('2025-12-30'), T0('2026-01-01 12:00')), (pd.NaT, T0('2026-01-09'))]
    assert interval_union_days(iv, lo, hi) == approx(3 + 1 + 0.5)
    assert count_handoffs(['A', 'A', 'B', 'A', 'C', 'C']) == 3
    assert count_handoffs([]) == 0
    assert not math.isnan(interval_union_days([], lo, hi))
