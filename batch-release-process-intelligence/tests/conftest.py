"""Hand-built SAP-style fixtures. Each test builds a tiny extract whose KPIs can be computed by hand."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

COLS = {
    'AFRU': ['RUECK', 'AUFNR', 'VORNR', 'WERKS', 'MATNR', 'CHARG', 'ISDD', 'IEDD', 'LMNGA'],
    'MSEG': ['MBLNR', 'ZEILE', 'BWART', 'WERKS', 'MATNR', 'CHARG', 'BUDAT_TS', 'MENGE'],
    'QALS': ['PRUEFLOS', 'WERK', 'MATNR', 'CHARG', 'HERKUNFT', 'ENSTEHDAT_TS'],
    'QAMR': ['PRUEFLOS', 'MERKNR', 'PRUEFDATUV_TS', 'PRUEFDATUB_TS', 'RESULT'],
    'QMEL': ['QMNUM', 'QMART', 'WERKS', 'MATNR', 'CHARG', 'QMDAT_TS', 'QMDAB_TS', 'CATEGORY', 'CAPA_REQUIRED', 'EVENT_REF'],
    'QAVE': ['PRUEFLOS', 'VCODE', 'VDATUM_TS', 'KZART'],
    'STATUS_LOG': ['STAT_ID', 'OBJ_TYPE', 'OBJ_KEY', 'STAT', 'UDATE_TS', 'SOURCE'],
    'MES_BATCH_RECORD': ['REC_ID', 'PLANT', 'MES_BATCH_ID', 'EVENT', 'TS_START', 'TS_END'],
    'QMS_DISPOSITION': ['REC_ID', 'SITE', 'QMS_BATCH_REF', 'EVENT', 'TS_START', 'TS_END'],
    'LINEAGE': ['PARENT_WERKS', 'PARENT_MATNR', 'PARENT_CHARG', 'CHILD_WERKS', 'CHILD_MATNR', 'CHILD_CHARG', 'RELATION', 'TS'],
}
MAT = 'MAT-100010'          # oral solid, target 9 d


class Extract:
    """Builder for a minimal raw extract (dict of string DataFrames, like eventlog.load_raw)."""

    def __init__(self):
        self.rows = {k: [] for k in COLS}
        self.n = 0

    def _id(self):
        self.n += 1
        return str(self.n)

    def add(self, table, **kw):
        self.rows[table].append({c: str(kw.get(c, '')) for c in COLS[table]})
        return self

    def batch(self, charg, plant='1100', mfg_start='2026-03-02 06:00:00', mfg_end='2026-03-03 00:00:00',
              qc=('2026-03-03 08:00:00', '2026-03-05 08:00:00'), br_complete='2026-03-03 12:00:00',
              br_review=('2026-03-04 08:00:00', '2026-03-04 12:00:00'), qa=('2026-03-06 08:00:00', '2026-03-06 12:00:00'),
              ud='2026-03-08 00:00:00', lot=None, aufnr=None, ud_code='A'):
        lot = lot or 'L' + charg
        aufnr = aufnr or 'O' + charg
        self.add('AFRU', RUECK=self._id(), AUFNR=aufnr, VORNR='0010', WERKS=plant, MATNR=MAT, CHARG=charg,
                 ISDD=mfg_start, IEDD='2026-03-02 12:00:00', LMNGA=1)
        self.add('AFRU', RUECK=self._id(), AUFNR=aufnr, VORNR='0020', WERKS=plant, MATNR=MAT, CHARG=charg,
                 ISDD='2026-03-02 13:00:00', IEDD=mfg_end, LMNGA=1)
        self.add('MSEG', MBLNR='M' + charg, ZEILE=1, BWART='101', WERKS=plant, MATNR=MAT, CHARG=charg,
                 BUDAT_TS=mfg_end.replace('00:00:00', '02:00:00'), MENGE=1)
        self.add('QALS', PRUEFLOS=lot, WERK=plant, MATNR=MAT, CHARG=charg, HERKUNFT='04',
                 ENSTEHDAT_TS=mfg_end.replace('00:00:00', '03:00:00'))
        if qc:
            self.add('QAMR', PRUEFLOS=lot, MERKNR='0010', PRUEFDATUV_TS=qc[0], PRUEFDATUB_TS=qc[1], RESULT='PASS')
        mid = '%s-%s' % (plant, charg.lower())
        self.add('MES_BATCH_RECORD', REC_ID='R' + self._id(), PLANT=plant, MES_BATCH_ID=mid, EVENT='BR_COMPLETE',
                 TS_START='', TS_END=br_complete)
        self.add('MES_BATCH_RECORD', REC_ID='R' + self._id(), PLANT=plant, MES_BATCH_ID=mid, EVENT='BR_REVIEW',
                 TS_START=br_review[0], TS_END=br_review[1])
        self.add('QMS_DISPOSITION', REC_ID='Q' + self._id(), SITE=plant, QMS_BATCH_REF='%s-%s' % (charg[:4], charg[4:]),
                 EVENT='DISP_REVIEW', TS_START=qa[0], TS_END=qa[1])
        if ud:
            self.add('QAVE', PRUEFLOS=lot, VCODE=ud_code, VDATUM_TS=ud, KZART='initial')
        return self

    def raw(self):
        return {k: pd.DataFrame(v, columns=COLS[k]).astype(str) for k, v in self.rows.items()}


@pytest.fixture
def ex():
    return Extract()


def build(ex):
    from brpi.eventlog import build_event_log
    from brpi.kpis import attach_registers, case_table
    raw = ex.raw()
    E, xw, lin, dq = build_event_log(raw)
    T, trans = case_table(E, lin)
    T = attach_registers(T, E, raw)
    return E, xw, lin, dq, T, trans


@pytest.fixture(scope='session')
def full(tmp_path_factory):
    """The full synthetic pipeline, built once into a temp dir."""
    from brpi import export
    root = tmp_path_factory.mktemp('demo')
    info = export.export(root, regenerate=True)
    raw, E, xw, lin, dq, T, trans = export.build(root, regenerate=False)
    return {'root': root, 'info': info, 'E': E, 'T': T, 'dq': dq, 'trans': trans, 'raw': raw}
