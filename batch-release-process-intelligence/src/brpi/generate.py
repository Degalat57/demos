"""Synthetic SAP-style extract generator (all data is synthetic).

Writes one CSV per source table into <out>/raw/:

  AFRU.csv        order confirmations (actual start ISDD / finish IEDD per operation)
  MSEG.csv        goods movements, movement type 101 = goods receipt of the batch
  QALS.csv        inspection lots (a second lot for the same batch = retest)
  QAMR.csv        inspection results (start PRUEFDATUV sometimes missing, end PRUEFDATUB)
  QMEL.csv        quality notifications used as deviations (created QMDAT, completed QMDAB)
  QAVE.csv        usage decisions (a second record = changed usage decision)
  STATUS_LOG.csv  status-change log in the style of JCDS (SAP objects) and CDHDR/CDPOS (MES/QMS records)
  MES_BATCH_RECORD.csv  batch record lifecycle from a synthetic MES/QMS (different batch-ID format)
  QMS_DISPOSITION.csv   QA disposition review from a synthetic QMS (yet another batch-ID format)
  LINEAGE.csv     batch splits and merges (parent -> child)
  EXCEPTIONAL_EVENTS.csv, INTERVENTIONS.csv  registers recorded by the process owner

Built-in messiness (each is detected and reported by the event-log builder): missing start times,
exact duplicate rows from overlapping extracts, re-sent records with new keys, batch splits/merges,
inconsistent / mistyped batch IDs across systems, open batches at the cut-off, one exceptional
production event affecting a cluster of batches, and a documented intervention with a real effect.
"""
import csv
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from . import config as C

H = timedelta(hours=1)


class Gen:
    def __init__(self, seed=C.SEED):
        self.r = np.random.default_rng(seed)
        self.rows = {k: [] for k in ['AFRU', 'MSEG', 'QALS', 'QAMR', 'QMEL', 'QAVE', 'STATUS_LOG',
                                      'MES_BATCH_RECORD', 'QMS_DISPOSITION', 'LINEAGE']}
        self.seq = {'aufnr': 1000000, 'rueck': 50000000, 'mblnr': 4900000000, 'lot': 40000000000,
                    'qmnum': 200000000, 'mes': 700000, 'qms': 300000, 'stat': 1}
        self.charg_seq = {'1100': 0, '2200': 0}
        self.truth = []   # ground truth per release unit (used only by tests / README numbers sanity)

    # ------------------------------------------------------------------ helpers
    def nxt(self, k):
        self.seq[k] += 1
        return self.seq[k]

    def u(self, a, b):
        return float(self.r.uniform(a, b))

    def p(self, prob):
        return bool(self.r.random() < prob)

    def logn(self, median_h, sigma=0.5):
        return float(median_h * math.exp(self.r.normal(0, sigma)))

    def working(self, t):
        """QA/QC office hours: Mon-Fri 07:00-18:00. Shift t to the next working slot."""
        for _ in range(10):
            if t.weekday() >= 5:
                t = (t + timedelta(days=7 - t.weekday())).replace(hour=7, minute=0) + timedelta(minutes=self.u(0, 90))
            elif t.hour < 7:
                t = t.replace(hour=7, minute=0) + timedelta(minutes=self.u(0, 90))
            elif t.hour >= 18:
                t = (t + timedelta(days=1)).replace(hour=7, minute=0) + timedelta(minutes=self.u(0, 90))
            else:
                return t
        return t

    def new_charg(self, plant):
        self.charg_seq[plant] += 1
        letter = 'A' if plant == '1100' else 'B'
        return 'B26%s%05d' % (letter, self.charg_seq[plant])

    def status(self, obj_type, key, stat, ts, source):
        self.rows['STATUS_LOG'].append({'STAT_ID': self.nxt('stat'), 'OBJ_TYPE': obj_type, 'OBJ_KEY': key,
                                        'STAT': stat, 'UDATE_TS': ts, 'SOURCE': source})

    def mes_id(self, plant, charg):
        s = '%s-%s' % (plant, charg.lower())
        x = self.r.random()
        if x < 0.010:            # O-for-0 typo (unique edit-distance-1 match)
            i = s.rfind('0')
            s = s[:i] + 'o' + s[i + 1:]
        elif x < 0.016:          # dropped character (may be ambiguous; needs timing to resolve)
            i = len(s) - 1 - int(self.r.integers(0, 3))
            s = s[:i] + s[i + 1:]
        elif x < 0.020:          # garbled / manual entry: unmatched
            s = 'UNK-%04d' % int(self.r.integers(0, 9999))
        return s

    def qms_id(self, charg):
        s = '%s-%s' % (charg[:4], charg[4:])
        x = self.r.random()
        if x < 0.010:
            s = '  ' + s.lower() + ' '
        elif x < 0.015:
            i = len(s) - 1 - int(self.r.integers(0, 2))
            s = s[:i] + s[i + 1:]
        return s

    # ------------------------------------------------------------------ production
    def produce(self, plant, mat, day):
        fam = C.PRODUCTS[mat]['family']
        aufnr = str(self.nxt('aufnr'))
        charg = self.new_charg(plant)
        t = day + timedelta(hours=self.u(5, 16))
        n_ops = 3 if fam == 'Oral solid' else 4
        ops = []
        first_start = t
        for i in range(n_ops):
            dur = self.logn(7 if fam == 'Oral solid' else 9, 0.3)
            s, e = t, t + dur * H
            ops.append((s, e))
            t = e + self.u(0.2, 4) * H
        missing_p = 0.08 if plant == '1100' else 0.12
        for i, (s, e) in enumerate(ops):
            miss = self.p(missing_p)
            self.rows['AFRU'].append({'RUECK': self.nxt('rueck'), 'AUFNR': aufnr, 'VORNR': '%04d' % (10 * (i + 1)),
                                      'WERKS': plant, 'MATNR': mat, 'CHARG': charg,
                                      'ISDD': '' if miss else s, 'IEDD': e, 'LMNGA': 1})
            if miss and i == 0 and self.p(0.5):
                self.status('AUFNR', aufnr, 'STARTED', s, 'JCDS')
        return {'plant': plant, 'mat': mat, 'charg': charg, 'aufnr': aufnr, 'start': first_start,
                'complete': ops[-1][1]}

    # ------------------------------------------------------------------ release unit (one case)
    def release(self, plant, mat, charg, parents, relation):
        fam = C.PRODUCTS[mat]['family']
        sterile = fam == 'Sterile'
        mfg_complete = max(pp['complete'] for pp in parents)
        exc = None
        for ev in C.EXCEPTIONAL_EVENTS:
            s, e = datetime.fromisoformat(ev['start']), datetime.fromisoformat(ev['end']) + timedelta(days=2)
            if ev['site'] == plant and s <= mfg_complete <= e:
                exc = ev
        post_int = plant == '1100' and mfg_complete >= datetime(2026, 6, 1)
        august = mfg_complete.month == 8
        truth = {'plant': plant, 'mat': mat, 'charg': charg, 'relation': relation, 'exc': exc['id'] if exc else '',
                 'post_int': post_int}

        # goods receipt + inspection lot
        gr = mfg_complete + self.u(0.5, 6) * H
        mblnr = str(self.nxt('mblnr'))
        self.rows['MSEG'].append({'MBLNR': mblnr, 'ZEILE': 1, 'BWART': '101', 'WERKS': plant, 'MATNR': mat,
                                  'CHARG': charg, 'BUDAT_TS': gr, 'MENGE': 1})
        lot = str(self.nxt('lot'))
        lot_t = gr + self.u(0.05, 0.5) * H
        self.rows['QALS'].append({'PRUEFLOS': lot, 'WERK': plant, 'MATNR': mat, 'CHARG': charg, 'HERKUNFT': '04',
                                  'ENSTEHDAT_TS': lot_t})
        # QC testing (sterility test incubates 14 days)
        qc_s = self.working(lot_t + self.logn(14 if plant == '1100' else 11, 0.6) * H)
        qc_dur = (14 * 24 + self.logn(18, 0.4)) if sterile else self.logn(44, 0.45)
        if exc and exc['id'] == 'EXC-2026-02':
            qc_dur += self.u(48, 96)          # additional environmental-monitoring testing
        qc_e = self.working(qc_s + qc_dur * H)
        oos = self.p(0.05)
        self.qamr(lot, qc_s, qc_e, 'OOS' if oos else 'PASS', plant)
        qc_done = qc_e
        lots = [lot]
        if oos:                               # retest on a second inspection lot
            lot2 = str(self.nxt('lot'))
            t2 = qc_e + self.u(2, 8) * H
            self.rows['QALS'].append({'PRUEFLOS': lot2, 'WERK': plant, 'MATNR': mat, 'CHARG': charg,
                                      'HERKUNFT': '89', 'ENSTEHDAT_TS': t2})
            s2 = self.working(t2 + self.logn(6, 0.5) * H)
            e2 = self.working(s2 + self.logn(40, 0.4) * H)
            self.qamr(lot2, s2, e2, 'PASS', plant)
            qc_done = e2
            lots.append(lot2)
        truth['oos'] = oos

        # deviations
        devs = []
        p_dev = (0.10 if not sterile else 0.15) + (0.03 if plant == '2200' else 0)
        if exc:
            cat = exc['category']
            raised = mfg_complete - self.u(0, 12) * H
            med = 14 * 24 if exc['id'] == 'EXC-2026-02' else 9 * 24
            devs.append((cat, raised, raised + self.logn(med, 0.35) * H, exc['id']))
        if oos:
            raised = qc_e + self.u(1, 6) * H
            devs.append(('OOS/OOT', raised, raised + self.logn(10 * 24, 0.45) * H, ''))
        if self.p(p_dev):
            cats = ['Documentation error', 'Process parameter', 'Equipment', 'Material/supplier', 'Environmental monitoring']
            cat = cats[int(self.r.choice(5, p=[0.32, 0.22, 0.2, 0.14, 0.12]))]
            med = {'Documentation error': 3, 'Process parameter': 6, 'Equipment': 8, 'Material/supplier': 7,
                   'Environmental monitoring': 9}[cat] * 24
            if plant == '2200':
                med *= 1.15
            raised = mfg_complete - self.u(0, 20) * H if self.p(0.6) else mfg_complete + self.u(1, 72) * H
            devs.append((cat, raised, raised + self.logn(med, 0.5) * H, ''))
        dev_done = None
        for cat, raised, closed, ref in devs:
            q = str(self.nxt('qmnum'))
            final_close = closed
            if self.p(0.07):                  # reopened deviation (status log carries the first closure)
                self.status('QMEL', q, 'CLOSED', closed, 'CDHDR/CDPOS')
                reo = closed + self.logn(30, 0.4) * H
                self.status('QMEL', q, 'REOPENED', reo, 'CDHDR/CDPOS')
                final_close = reo + self.logn(72, 0.4) * H
            capa = 'Y' if cat in ('Equipment', 'Process parameter', 'Environmental monitoring') and self.p(0.4) else 'N'
            self.rows['QMEL'].append({'QMNUM': q, 'QMART': 'Q3', 'WERKS': plant, 'MATNR': mat, 'CHARG': charg,
                                      'QMDAT_TS': raised, 'QMDAB_TS': final_close, 'CATEGORY': cat,
                                      'CAPA_REQUIRED': capa, 'EVENT_REF': ref})
            dev_done = max(dev_done, final_close) if dev_done else final_close
        truth['n_dev'] = len(devs)

        # batch record (MES) and QA batch record review, with rework loops
        mid = self.mes_id(plant, charg)
        br_c = mfg_complete + self.logn(30 if plant == '1100' else 20, 0.5) * H
        self.mes(plant, mid, 'BR_COMPLETE', '', br_c)
        if self.p(0.005):                     # re-sent record with a new key and identical timestamp
            self.mes(plant, mid, 'BR_COMPLETE', '', br_c)
        p_rw = 0.25 if plant == '1100' else 0.13
        if post_int:
            p_rw = 0.09
        if sterile:
            p_rw += 0.03
        t = br_c
        loops = 0
        while True:
            rs = self.working(t + self.logn(16 if plant == '1100' else 12, 0.6) * H)
            re_ = rs + self.logn(3 if loops == 0 else 2, 0.4) * H
            self.mes(plant, mid, 'BR_REVIEW', rs, re_, miss_p=0.05)
            if loops < 2 and self.p(p_rw if loops == 0 else 0.3):
                self.mes(plant, mid, 'BR_RETURNED', '', re_ + self.u(0.05, 0.3) * H)
                t = re_ + self.logn(30, 0.5) * H
                self.mes(plant, mid, 'BR_CORRECTED', '', t)
                loops += 1
                continue
            break
        doc_done = re_
        truth['doc_loops'] = loops

        # QA disposition review (QMS)
        qid = self.qms_id(charg)
        ready_nodev = max(doc_done, qc_done)
        ready = max(ready_nodev, dev_done) if dev_done else ready_nodev
        seq_exception = bool(dev_done and dev_done > ready_nodev and self.p(0.12))
        med_q = (62 if plant == '1100' else 38)
        if post_int:
            med_q = 40
        if august:
            med_q *= 1.15
        if exc:
            med_q += 24
        base = ready_nodev if seq_exception else ready
        qs = self.working(base + self.logn(med_q, 0.6) * H)
        qe = qs + self.logn(4, 0.4) * H
        if seq_exception:
            qe = max(qe, dev_done + self.u(1, 4) * H)
        miss_q = 0.18 if plant == '2200' else 0.04
        self.qms(plant, qid, 'DISP_REVIEW', qs, qe, miss_q)
        if self.p(0.10):                      # repeat QA query
            self.qms(plant, qid, 'QA_QUERY', '', qe + self.u(0.05, 0.2) * H, 0)
            qs = self.working(qe + self.logn(24, 0.5) * H)
            qe = qs + self.logn(2, 0.4) * H
            self.qms(plant, qid, 'DISP_REVIEW', qs, qe, miss_q)
        truth['seq_exception'] = seq_exception

        # usage decision (QAVE)
        ud = self.working(qe + self.logn(10, 0.6) * H)
        code = 'R' if self.p(0.005) else 'A'
        if self.p(0.015) and code == 'A':     # changed usage decision
            self.rows['QAVE'].append({'PRUEFLOS': lots[-1], 'VCODE': 'A2', 'VDATUM_TS': ud, 'KZART': 'initial'})
            ud2 = self.working(ud + self.logn(20, 0.5) * H)
            self.rows['QAVE'].append({'PRUEFLOS': lots[-1], 'VCODE': 'A', 'VDATUM_TS': ud2, 'KZART': 'change'})
            truth['ud_changed'] = True
        else:
            self.rows['QAVE'].append({'PRUEFLOS': lots[-1], 'VCODE': code, 'VDATUM_TS': ud, 'KZART': 'initial'})
            truth['ud_changed'] = False
        truth['cycle_d'] = (ud - mfg_complete).total_seconds() / 86400
        truth['ud'] = ud
        self.truth.append(truth)

    def qamr(self, lot, s, e, res, plant):
        miss = self.p(0.25 if plant == '2200' else 0.12)
        self.rows['QAMR'].append({'PRUEFLOS': lot, 'MERKNR': '0010', 'PRUEFDATUV_TS': '' if miss else s,
                                  'PRUEFDATUB_TS': e, 'RESULT': res})
        if miss and self.p(0.6):
            self.status('QALS', lot, 'INSP_START', s, 'JCDS')

    def mes(self, plant, mid, ev, s, e, miss_p=0.0):
        rid = 'MES%07d' % self.nxt('mes')
        miss = bool(s) and self.p(miss_p)
        self.rows['MES_BATCH_RECORD'].append({'REC_ID': rid, 'PLANT': plant, 'MES_BATCH_ID': mid, 'EVENT': ev,
                                              'TS_START': '' if miss else s, 'TS_END': e})
        if miss and self.p(0.5):
            self.status('MES_BR', rid, 'IN_REVIEW', s, 'CDHDR/CDPOS')

    def qms(self, plant, qid, ev, s, e, miss_p):
        rid = 'QMS%06d' % self.nxt('qms')
        miss = bool(s) and self.p(miss_p)
        self.rows['QMS_DISPOSITION'].append({'REC_ID': rid, 'SITE': plant, 'QMS_BATCH_REF': qid, 'EVENT': ev,
                                             'TS_START': '' if miss else s, 'TS_END': e})
        if miss and self.p(0.4):
            self.status('QMS_DR', rid, 'IN_REVIEW', s, 'CDHDR/CDPOS')

    # ------------------------------------------------------------------ driver
    def run(self):
        day = C.PERIOD_START
        prod = []
        while day <= C.PERIOD_END_PRODUCTION:
            if day.weekday() < 5:
                for plant in C.SITES:
                    lam = 1.9 if plant == '1100' else 1.7
                    for _ in range(int(self.r.poisson(lam))):
                        mats = C.SITE_PRODUCTS[plant]
                        w = [0.4, 0.35, 0.25] if plant == '1100' else [0.35, 0.4, 0.25]
                        mat = mats[int(self.r.choice(3, p=w))]
                        prod.append(self.produce(plant, mat, day))
            day += timedelta(days=1)
        i = 0
        while i < len(prod):
            pp = prod[i]
            x = self.r.random()
            if x < 0.03:                       # split: one production batch -> two packaged child batches
                for _ in range(2):
                    ch = self.new_charg(pp['plant'])
                    self.lineage(pp, ch, 'split')
                    self.release(pp['plant'], pp['mat'], ch, [pp], 'split-child')
                i += 1
                continue
            if x < 0.045:                      # merge with the next batch of the same site/material
                j = next((k for k in range(i + 1, min(i + 8, len(prod)))
                          if prod[k]['plant'] == pp['plant'] and prod[k]['mat'] == pp['mat']), None)
                if j is not None:
                    q = prod.pop(j)
                    ch = self.new_charg(pp['plant'])
                    self.lineage(pp, ch, 'merge')
                    self.lineage(q, ch, 'merge')
                    self.release(pp['plant'], pp['mat'], ch, [pp, q], 'merge-child')
                    i += 1
                    continue
            self.release(pp['plant'], pp['mat'], pp['charg'], [pp], 'none')
            i += 1

    def lineage(self, parent, child, rel):
        self.rows['LINEAGE'].append({'PARENT_WERKS': parent['plant'], 'PARENT_MATNR': parent['mat'],
                                     'PARENT_CHARG': parent['charg'], 'CHILD_WERKS': parent['plant'],
                                     'CHILD_MATNR': parent['mat'], 'CHILD_CHARG': child, 'RELATION': rel,
                                     'TS': parent['complete'] + timedelta(hours=2)})

    def finalize(self):
        """Apply the extract cut-off and inject exact duplicate rows from overlapping extracts."""
        ts_cols = {'AFRU': ['ISDD', 'IEDD'], 'MSEG': ['BUDAT_TS'], 'QALS': ['ENSTEHDAT_TS'],
                   'QAMR': ['PRUEFDATUV_TS', 'PRUEFDATUB_TS'], 'QMEL': ['QMDAT_TS'], 'QAVE': ['VDATUM_TS'],
                   'STATUS_LOG': ['UDATE_TS'], 'MES_BATCH_RECORD': ['TS_END'], 'QMS_DISPOSITION': ['TS_END'],
                   'LINEAGE': ['TS']}
        for t, rows in self.rows.items():
            keep = []
            for r in rows:
                if any(isinstance(r[c], datetime) and r[c] > C.CUTOFF for c in ts_cols[t]):
                    continue
                if t == 'QMEL' and isinstance(r['QMDAB_TS'], datetime) and r['QMDAB_TS'] > C.CUTOFF:
                    r = dict(r, QMDAB_TS='')          # still open at cut-off
                keep.append(r)
            if t in ('AFRU', 'MSEG', 'QAMR', 'MES_BATCH_RECORD', 'QALS'):
                dup = [dict(r) for r in keep if self.r.random() < 0.03]
                keep = keep + dup
                keep.sort(key=lambda r: str(r[ts_cols[t][-1]]))
            self.rows[t] = keep


def fmt(v):
    if isinstance(v, datetime):
        return v.strftime('%Y-%m-%d %H:%M:%S')
    return v


def write_csv(path, rows):
    if not rows:
        return
    cols = list(rows[0].keys())
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: fmt(r[k]) for k in cols})


def generate(out_dir, seed=C.SEED):
    out = Path(out_dir) / 'raw'
    out.mkdir(parents=True, exist_ok=True)
    g = Gen(seed)
    g.run()
    g.finalize()
    for t, rows in g.rows.items():
        write_csv(out / ('%s.csv' % t), rows)
    write_csv(out / 'EXCEPTIONAL_EVENTS.csv', [dict(e) for e in C.EXCEPTIONAL_EVENTS])
    write_csv(out / 'INTERVENTIONS.csv', [{k: (json.dumps(v) if isinstance(v, list) else v) for k, v in e.items()}
                                           for e in C.INTERVENTIONS])
    return {t: len(r) for t, r in g.rows.items()}
