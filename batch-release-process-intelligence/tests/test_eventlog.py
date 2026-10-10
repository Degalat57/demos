"""Data-quality rules R1-R6 of the event-log builder, on hand-built fixtures."""
import pandas as pd

from brpi.eventlog import build_crosswalk, levenshtein, normalise_id
from conftest import MAT, build

CASE = '1100|%s|B26A00001' % MAT


def acts(E, case=CASE):
    return E[E['case_id'] == case]['activity'].tolist()


def test_happy_path_event_log(ex):
    ex.batch('B26A00001')
    E, xw, lin, dq, T, _ = build(ex)
    assert acts(E) == ['Manufacturing Executed', 'Goods Receipt', 'Inspection Lot Created', 'Batch Record Completed',
                       'Batch Record Review', 'QC Results Recorded', 'QA Disposition Review', 'Usage Decision']
    me = E[E['activity'] == 'Manufacturing Executed'].iloc[0]
    assert str(me['ts_start']) == '2026-03-02 06:00:00' and str(me['ts_end']) == '2026-03-03 00:00:00'
    assert set(E['source_table']) == {'AFRU', 'MSEG', 'QALS', 'QAMR', 'MES_BATCH_RECORD', 'QMS_DISPOSITION', 'QAVE'}
    assert (E['match_conf'] == 1.0).all()


def test_r1_start_from_status_log_then_none(ex):
    ex.batch('B26A00001', qc=None).batch('B26A00002', qc=None)
    ex.add('QAMR', PRUEFLOS='LB26A00001', MERKNR='0010', PRUEFDATUV_TS='', PRUEFDATUB_TS='2026-03-05 08:00:00', RESULT='PASS')
    ex.add('QAMR', PRUEFLOS='LB26A00002', MERKNR='0010', PRUEFDATUV_TS='', PRUEFDATUB_TS='2026-03-05 08:00:00', RESULT='PASS')
    ex.add('STATUS_LOG', STAT_ID=1, OBJ_TYPE='QALS', OBJ_KEY='LB26A00001', STAT='INSP_START', UDATE_TS='2026-03-03 09:00:00', SOURCE='JCDS')
    E, *_, dq, T, _ = build(ex)
    qc = E[E['activity'] == 'QC Results Recorded'].set_index('case_id')
    assert qc.loc[CASE, 'start_source'] == 'status_log' and str(qc.loc[CASE, 'ts_start']) == '2026-03-03 09:00:00'
    c2 = '1100|%s|B26A00002' % MAT
    assert qc.loc[c2, 'start_source'] == 'none' and pd.isna(qc.loc[c2, 'ts_start'])
    cov = dq['rules']['R1_start_times']['QC Results Recorded']
    assert (cov['explicit'], cov['status_log'], cov['none'], cov['coverage_pct']) == (0, 1, 1, 50.0)
    t = T.set_index('case_id')
    assert bool(t.loc[CASE, 'split_ok']) and not bool(t.loc[c2, 'split_ok'])   # elapsed, unsplit


def test_r2_exact_duplicates_collapsed(ex):
    ex.batch('B26A00001')
    ex.rows['MSEG'].append(dict(ex.rows['MSEG'][0]))
    ex.rows['QALS'].append(dict(ex.rows['QALS'][0]))
    ex.rows['AFRU'].append(dict(ex.rows['AFRU'][0]))
    E, *_, dq, T, _ = build(ex)
    assert acts(E).count('Goods Receipt') == 1 and acts(E).count('Inspection Lot Created') == 1
    assert dq['rules']['R2_duplicates_collapsed']['total'] == 3
    assert dq['rules']['R2_duplicates_collapsed']['by_source'] == {'MSEG': 1, 'QALS': 1, 'AFRU': 1}
    assert not T.iloc[0]['retest']                    # a duplicate lot row is not a retest


def test_r3_resend_vs_repeat(ex):
    ex.batch('B26A00001')
    # same activity + same timestamp + new key -> suspected re-send (dropped, listed)
    ex.add('MES_BATCH_RECORD', REC_ID='R900', PLANT='1100', MES_BATCH_ID='1100-b26a00001', EVENT='BR_COMPLETE',
           TS_START='', TS_END='2026-03-03 12:00:00')
    E, *_, dq, T, _ = build(ex)
    assert dq['rules']['R3_suspected_resends']['count'] == 1
    assert acts(E).count('Batch Record Completed') == 1 and not T.iloc[0]['rework']
    # same activity + new key + new timestamp -> repeat (rework)
    ex.add('MES_BATCH_RECORD', REC_ID='R901', PLANT='1100', MES_BATCH_ID='1100-b26a00001', EVENT='BR_REVIEW',
           TS_START='2026-03-04 14:00:00', TS_END='2026-03-04 15:00:00')
    E, *_, dq, T, _ = build(ex)
    assert acts(E).count('Batch Record Review') == 2
    assert T.iloc[0]['doc_rework'] and T.iloc[0]['rework'] and not T.iloc[0]['rft']


def test_r4_split_children_inherit_upstream(ex):
    # parent batch is produced; two children are released
    ex.add('AFRU', RUECK=1, AUFNR='O1', VORNR='0010', WERKS='1100', MATNR=MAT, CHARG='B26A00010',
           ISDD='2026-03-02 06:00:00', IEDD='2026-03-03 00:00:00', LMNGA=1)
    for ch in ['B26A00011', 'B26A00012']:
        ex.batch(ch)
        ex.rows['AFRU'] = [r for r in ex.rows['AFRU'] if r['CHARG'] != ch]   # children have no own production
        ex.add('LINEAGE', PARENT_WERKS='1100', PARENT_MATNR=MAT, PARENT_CHARG='B26A00010', CHILD_WERKS='1100',
               CHILD_MATNR=MAT, CHILD_CHARG=ch, RELATION='split', TS='2026-03-03 02:00:00')
    E, *_, dq, T, _ = build(ex)
    for ch in ['B26A00011', 'B26A00012']:
        me = E[(E['case_id'] == '1100|%s|%s' % (MAT, ch)) & (E['activity'] == 'Manufacturing Executed')]
        assert len(me) == 1 and me.iloc[0]['inherited_from'] == '1100|%s|B26A00010' % MAT
    assert len(T) == 2 and set(T['lineage']) == {'split'}         # parent is not a release case
    assert T['cycle_d'].round(6).tolist() == [5.0, 5.0]
    assert dq['rules']['R4_lineage']['splits'] == 2 and dq['rules']['R4_lineage']['inherited_events'] == 2


def test_r4_merge_uses_latest_parent(ex):
    for p, end in [('B26A00020', '2026-03-02 20:00:00'), ('B26A00021', '2026-03-03 00:00:00')]:
        ex.add('AFRU', RUECK=p, AUFNR='O' + p, VORNR='0010', WERKS='1100', MATNR=MAT, CHARG=p, ISDD='2026-03-02 06:00:00',
               IEDD=end, LMNGA=1)
        ex.add('LINEAGE', PARENT_WERKS='1100', PARENT_MATNR=MAT, PARENT_CHARG=p, CHILD_WERKS='1100', CHILD_MATNR=MAT,
               CHILD_CHARG='B26A00022', RELATION='merge', TS=end)
    ex.batch('B26A00022')
    ex.rows['AFRU'] = [r for r in ex.rows['AFRU'] if r['CHARG'] != 'B26A00022']
    *_, T, _ = build(ex)
    assert len(T) == 1 and T.iloc[0]['cycle_d'] == 5.0 and T.iloc[0]['conformant']


def test_r5_crosswalk_rules():
    assert normalise_id('1100-b26a00123', '1100') == 'B26A00123'
    assert normalise_id('  b26a-00123 ') == 'B26A00123'
    assert levenshtein('B26A0O123', 'B26A00123') == 1
    gr = {('1100', 'B26A00123'): pd.Timestamp('2026-03-01'), ('1100', 'B26A00124'): pd.Timestamp('2026-03-01'),
          ('1100', 'B26A00777'): pd.Timestamp('2026-08-01')}
    sap = {'1100': set(c for _, c in gr)}
    ids = pd.DataFrame([
        ('MES', '1100', '1100-b26a00123', pd.Timestamp('2026-03-03')),   # exact after normalisation
        ('MES', '1100', '1100-b26a0o777', pd.Timestamp('2026-08-03')),   # O-for-0 typo, unique
        ('MES', '1100', '1100-b26a0012', pd.Timestamp('2026-03-03')),    # dropped char: 2 candidates, both plausible
        ('MES', '1100', 'UNK-1234', pd.Timestamp('2026-03-03')),         # unmatched
        ('QMS', '1100', 'B26A-00777', pd.Timestamp('2026-03-03')),       # exact but timing implausible (before GR)
    ], columns=['source_system', 'plant', 'source_id', 'first_ts'])
    xw = build_crosswalk(ids, sap, gr).set_index('source_id')
    assert xw.loc['1100-b26a00123', 'confidence'] == 1.0
    assert xw.loc['1100-b26a0o777', 'charg'] == 'B26A00777' and xw.loc['1100-b26a0o777', 'confidence'] == 0.85
    assert xw.loc['1100-b26a0012', 'charg'] == '' and xw.loc['1100-b26a0012', 'confidence'] == 0.5
    assert xw.loc['UNK-1234', 'method'] == 'unmatched'
    assert xw.loc['B26A-00777', 'confidence'] == 0.5


def test_r5_unmatched_rows_excluded_and_reported(ex):
    ex.batch('B26A00001')
    ex.add('MES_BATCH_RECORD', REC_ID='R77', PLANT='1100', MES_BATCH_ID='UNK-0001', EVENT='BR_REVIEW',
           TS_START='2026-03-04 08:00:00', TS_END='2026-03-04 09:00:00')
    E, *_, dq, T, _ = build(ex)
    assert dq['rules']['R5_crosswalk']['rows_excluded'] == {'MES': 1, 'QMS': 0}
    assert acts(E).count('Batch Record Review') == 1


def test_r6_start_after_end_dropped(ex):
    ex.batch('B26A00001', br_review=('2026-03-04 13:00:00', '2026-03-04 12:00:00'))
    E, *_, dq, T, _ = build(ex)
    assert dq['rules']['R6_start_after_end_dropped'] == 1
    assert E[E['activity'] == 'Batch Record Review'].iloc[0]['start_source'] == 'none'
    assert not T.iloc[0]['split_ok']
