"""Analytics on the case table: internal benchmark, driver gaps, opportunities, fast vs slow,
fact / hypothesis statements, explainable maturity score, intervention pre/post test, scenarios.

Everything is deterministic (fixed bootstrap seed). The site (assets/engine.js) re-implements the
filterable parts with the same formulas; tests/test_js_parity.py checks both agree.
"""
import numpy as np
import pandas as pd
from scipy import stats

from . import config as C
from .kpis import aggregate, decompose

# ------------------------------------------------------------------ explainable maturity score
MATURITY_DIMS = [
    # key, label, weight, how the 0-100 score is computed
    ('performance', 'Performance', 0.20, 'share of batches released within the product target'),
    ('predictability', 'Predictability', 0.15, '100 x (1 - coefficient of variation of cycle/target), floored at 0'),
    ('quality', 'Quality', 0.20, 'right-first-time %'),
    ('standardization', 'Standardization', 0.10, 'share of batches following the expected path'),
    ('efficiency', 'Efficiency', 0.15, '70% QA-waiting score (100 at <=1 d, 0 at >=5 d) + 30% hand-off score (100 at <=6, 0 at >=12)'),
    ('compliance', 'Compliance / adherence', 0.10, 'share of batches with all expected controls in the required order'),
    ('improvement', 'Continuous improvement', 0.10, '50 + 50 x share of batches produced under an intervention with a sustained, significant benefit'),
]


def clip(x, lo=0.0, hi=100.0):
    return float(min(hi, max(lo, x)))


def maturity(T, mask=None, sustained=None):
    d = T if mask is None else T[mask]
    c = d[d['closed']]
    if len(c) == 0:
        return None
    ratio = c['cycle_d'] / c['target_d']
    qa = c['qa_wait_d'].dropna()
    qa_mean = float(qa.mean()) if len(qa) else 3.0
    s = {
        'performance': 100 * float(c['ontime'].mean()),
        'predictability': clip(100 * (1 - float(ratio.std(ddof=0) / ratio.mean()))),
        'quality': 100 * float(c['rft'].mean()),
        'standardization': 100 * float(c['conformant'].mean()),
        'efficiency': 0.7 * clip(100 * (1 - (qa_mean - 1) / 4)) + 0.3 * clip(100 * (1 - (float(c['handoffs'].mean()) - 6) / 6)),
        'compliance': 100 * float(c['compliance_ok'].mean()),
        'improvement': 50 + 50 * ci_share(c, sustained or {}),
    }
    contrib = {k: w * s[k] for k, _, w, _ in MATURITY_DIMS}
    return {'score': float(sum(contrib.values())), 'dims': s, 'contrib': contrib, 'n': int(len(c))}


def ci_share(c, sustained):
    """Share of batches produced under a recorded intervention whose benefit is sustained (0 if none)."""
    if not len(c):
        return 0.0
    m = pd.Series(False, index=c.index)
    for iv, ok in sustained.items():
        if ok and iv + '_exposed' in c:
            m |= c[iv + '_exposed'].astype(bool)
    return float(m.mean())


def maturity_change(m0, m1):
    """Per-dimension contribution to the score change; sums exactly to m1.score - m0.score."""
    return {k: m1['contrib'][k] - m0['contrib'][k] for k, _, _, _ in MATURITY_DIMS}


# ------------------------------------------------------------------ internal benchmark
BENCH_KPIS = [
    # key in aggregate(), label, unit, lower_is_better
    ('cycle_mean_d', 'Release cycle time (mean)', 'd', True),
    ('qa_wait_mean_d', 'QA review waiting', 'd', True),
    ('qc_delay_mean_d', 'QC result availability', 'd', True),
    ('dev_res_mean_d', 'Deviation resolution time', 'd', True),
    ('doc_rework_pct', 'Documentation rework', '%', True),
    ('qa_repeat_pct', 'Repeat QA queries', '%', True),
    ('rft_pct', 'Right first time', '%', False),
    ('handoffs_mean', 'Hand-offs per batch', '', True),
    ('deviation_rate_pct', 'Batches with deviation', '%', True),
    ('conformance_pct', 'Expected-path conformance', '%', False),
]
TARGETS = {'qa_wait_mean_d': 2.0, 'doc_rework_pct': 8.0, 'qa_repeat_pct': 5.0, 'rft_pct': 75.0, 'handoffs_mean': 6.0,
           'deviation_rate_pct': 15.0, 'conformance_pct': 70.0, 'qc_delay_mean_d': None, 'dev_res_mean_d': 7.0}


def quarter(m):
    y, mm = m.split('-')
    return '%s-Q%d' % (y, (int(mm) - 1) // 3 + 1)


def internal_best(T, mask=None, min_n=20):
    """Best site-quarter value per KPI inside the (product/period) scope; site filter is ignored on purpose."""
    d = T if mask is None else T[mask]
    d = d.assign(q=d['month'].map(quarter))
    best = {}
    groups = [aggregate(g) | {'group': '%s %s' % (C.SITES[s]['name'], q)}
              for (s, q), g in d.groupby(['site', 'q']) if g['closed'].sum() >= min_n]
    for k, _, _, lower in BENCH_KPIS:
        vals = [(g[k], g['group']) for g in groups if g.get(k) is not None]
        if vals:
            best[k] = (min if lower else max)(vals)
    return best


# ------------------------------------------------------------------ opportunities
EFFORT = {'qa_wait': 2.0, 'deviation': 3.0, 'doc_rework': 1.5, 'qc': 2.5, 'approval': 1.0}   # SME assumption (1-3)


def opportunities(T, mask=None):
    """Rank = impact (days/batch to internal best) x frequency (share affected) x confidence (data coverage)
    / effort-risk (assumption). Every input is returned so the ranking is explainable."""
    d = T if mask is None else T[mask]
    c = d[d['closed'] & d['seg_qa_stage'].notna()]
    if len(c) < 10:
        return []
    allc = T[T['closed'] & T['seg_qa_stage'].notna()]
    q = allc.assign(q=allc['month'].map(quarter))
    out = []

    def best_of(col, sel=None):
        vals = []
        for _, g in q.groupby(['site', 'q']):
            g = g if sel is None else g[sel(g)]
            if len(g) >= 15:
                vals.append(float(g[col].mean()))
        return min(vals) if vals else None

    def add(key, title, col, affected, coverage, rec, sel=None):
        cc = c if sel is None else c[sel(c)]
        cur = float(cc[col].mean()) if len(cc) and cc[col].notna().any() else None
        b = best_of(col, sel)
        if cur is None or b is None:
            return
        impact = max(0.0, cur - b)
        freq = float(affected.mean())
        conf = float(coverage)
        score = impact * freq * conf / EFFORT[key]
        out.append({'key': key, 'title': title, 'current_d': cur, 'internal_best_d': b, 'impact_d': impact,
                    'frequency': freq, 'frequency_pct': 100 * freq, 'confidence': conf, 'effort': EFFORT[key], 'score': score,
                    'recommendation': rec})
    add('qa_wait', 'QA review waiting', 'qa_wait_d', c['qa_wait_d'].fillna(0) > 2, c['qa_wait_d'].notna().mean(),
        'Daily QA release stand-up with a visible queue and a review-ready trigger from QC/MES')
    add('deviation', 'Deviation closure on the critical path', 'seg_deviation', c['binding'] == 'Deviation closure', 1.0,
        'Triage deviations at batch completion; fast lane for minor documentation deviations')
    add('doc_rework', 'Batch record documentation rework', 'seg_documentation', c['doc_rework'], 1.0,
        'Right-first-time pre-check of batch records before QA review (replicate INT-01)')
    add('qc', 'QC result availability (oral solid)', 'qc_delay_d', (c['family'] == 'Oral solid') & (c['binding'] == 'QC results'),
        1.0, 'Prioritise QC test queue by release due date; review lab capacity at peaks',
        sel=lambda x: x['family'] == 'Oral solid')
    add('approval', 'Usage-decision approval wait', 'seg_approval', c['seg_approval'] > 1, 1.0,
        'Release authorisations closer to QA review completion (e.g. extended QA release coverage)')
    return sorted(out, key=lambda r: -r['score'])


# ------------------------------------------------------------------ fast vs slow, facts
def fast_slow(T, mask=None):
    d = T if mask is None else T[mask]
    c = d[d['closed']].copy()
    c['ratio'] = c['cycle_d'] / c['target_d']
    lo, hi = c['ratio'].quantile(0.25), c['ratio'].quantile(0.75)
    fast, slow = c[c['ratio'] <= lo], c[c['ratio'] >= hi]

    def prof(x):
        return {'n': int(len(x)), 'cycle_mean_d': float(x['cycle_d'].mean()), 'deviation_pct': 100 * float(x['has_dev'].mean()),
                'doc_rework_pct': 100 * float(x['doc_rework'].mean()), 'doc_loops2_pct': 100 * float((x['doc_loops'] >= 2).mean()),
                'qa_repeat_pct': 100 * float(x['qa_repeat'].mean()), 'retest_pct': 100 * float(x['retest'].mean()),
                'qa_wait_mean_d': float(x['qa_wait_d'].mean()), 'handoffs_mean': float(x['handoffs'].mean()),
                'conformance_pct': 100 * float(x['conformant'].mean()),
                'site_a_share_pct': 100 * float((x['site'] == '1100').mean())}
    return {'fast': prof(fast), 'slow': prof(slow), 'fast_max_ratio': float(lo), 'slow_min_ratio': float(hi)}


def facts(T, mask=None):
    d = T if mask is None else T[mask]
    c = d[d['closed']]
    late, ok = c[~c['ontime']], c[c['ontime']]
    late5 = c[c['cycle_d'] > c['target_d'] + 5]
    return {
        'late_with_dev_pct': 100 * float(late['has_dev'].mean()) if len(late) else None,
        'ontime_with_dev_pct': 100 * float(ok['has_dev'].mean()) if len(ok) else None,
        'late5_with_dev_pct': 100 * float(late5['has_dev'].mean()) if len(late5) else None,
        'n_late': int(len(late)), 'n_ontime': int(len(ok)), 'n_late5': int(len(late5)),
    }


# ------------------------------------------------------------------ intervention pre/post
def _boot(fn, a, b, n=2000, seed=7):
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a, float), np.asarray(b, float)
    vals = [fn(rng.choice(b, len(b)), rng.choice(a, len(a))) for _ in range(n)]
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def intervention_effect(T, iv=None, exclude_exceptional=True):
    """Pre vs post comparison for the intervention site plus a difference-in-differences against the other site.
    Continuous KPIs: Mann-Whitney U (two-sided) + bootstrap 95% CI of the median difference.
    Rates: Fisher exact test + bootstrap 95% CI of the difference in proportions."""
    iv = iv or C.INTERVENTIONS[0]
    c = T[T['closed']]
    if exclude_exceptional:
        c = c[c['exc_event'] == '']
    pre0, pre1 = map(pd.Timestamp, iv['pre_window'])
    post0, post1 = map(pd.Timestamp, iv['post_window'])
    post1 = post1 + pd.Timedelta(hours=23, minutes=59)
    pre1 = pre1 + pd.Timedelta(hours=23, minutes=59)
    inpre = (c['mfg_complete'] >= pre0) & (c['mfg_complete'] <= pre1)
    inpost = (c['mfg_complete'] >= post0) & (c['mfg_complete'] <= post1)
    site = c['site'] == iv['site']
    open_in_post = T[(~T['closed']) & (T['site'] == iv['site']) & (T['mfg_complete'] >= post0) & (T['mfg_complete'] <= post1)]
    res = {'intervention': iv, 'exclude_exceptional': exclude_exceptional, 'open_cases_in_post_window': int(len(open_in_post)),
           'kpis': []}
    for key, label, kind in [('doc_rework', 'Documentation rework', 'rate'), ('qa_wait_d', 'QA review waiting', 'cont'),
                             ('cycle_d', 'Release cycle time', 'cont'), ('rft', 'Right first time', 'rate')]:
        a = c[site & inpre][key].dropna()
        b = c[site & inpost][key].dropna()
        ca = c[~site & inpre][key].dropna()
        cb = c[~site & inpost][key].dropna()
        r = {'kpi': key, 'label': label, 'kind': kind, 'n_pre': int(len(a)), 'n_post': int(len(b))}
        if kind == 'rate':
            a, b, ca, cb = (x.astype(float) for x in (a, b, ca, cb))
            r['pre'], r['post'] = 100 * a.mean(), 100 * b.mean()
            tab = [[int(b.sum()), int(len(b) - b.sum())], [int(a.sum()), int(len(a) - a.sum())]]
            r['test'] = 'Fisher exact (two-sided)'
            r['p_value'] = float(stats.fisher_exact(tab)[1])
            lo, hi = _boot(lambda x, y: 100 * (x.mean() - y.mean()), a, b)
        else:
            r['pre'], r['post'] = float(a.median()), float(b.median())
            r['pre_mean'], r['post_mean'] = float(a.mean()), float(b.mean())
            r['test'] = 'Mann-Whitney U (two-sided)'
            r['p_value'] = float(stats.mannwhitneyu(b, a, alternative='two-sided').pvalue)
            lo, hi = _boot(lambda x, y: np.median(x) - np.median(y), a, b)
        r['change'] = r['post'] - r['pre']
        r['change_pct'] = 100 * r['change'] / r['pre'] if r['pre'] else None
        r['ci95'] = [lo, hi]
        scale = 100 if kind == 'rate' else 1
        r['comparison_site_change'] = float(scale * (cb.astype(float).mean() - ca.astype(float).mean()))
        r['did_means'] = float(scale * ((b.astype(float).mean() - a.astype(float).mean()) -
                                       (cb.astype(float).mean() - ca.astype(float).mean())))
        r['significant'] = r['p_value'] < 0.05 and not (lo <= 0 <= hi)
        res['kpis'].append(r)
    # where the remaining delay sits after the intervention (critical-path segments, post window)
    post = c[site & inpost]
    dec = decompose(post)
    tot = dec['_cycle_mean_d']
    res['post_segments_share_pct'] = {k: 100 * v / tot for k, v in dec.items() if not k.startswith('_')}
    # sustained? doc rework in the last 6 weeks of the post window still significantly below pre
    late = c[site & (c['mfg_complete'] > post1 - pd.Timedelta(days=42)) & inpost]['doc_rework'].astype(float)
    pre_r = c[site & inpre]['doc_rework'].astype(float)
    p_late = float(stats.fisher_exact([[int(late.sum()), int(len(late) - late.sum())],
                                       [int(pre_r.sum()), int(len(pre_r) - pre_r.sum())]])[1]) if len(late) else 1.0
    res['sustained'] = bool(len(late) >= 10 and late.mean() < pre_r.mean() and p_late < 0.05)
    res['sustained_detail'] = {'last6w_doc_rework_pct': 100 * float(late.mean()) if len(late) else None,
                               'n_last6w': int(len(late)), 'p_value': p_late}
    return res


# ------------------------------------------------------------------ scenario: exclude exceptional event(s)
def scenario_exclude(T, event_ids, mask=None, prior_mask=None):
    d = T if mask is None else T[mask]
    excl = d['exc_event'].isin(event_ids)
    rep = aggregate(d)
    adj = aggregate(d[~excl])
    out = {'events': list(event_ids), 'excluded_batches': int((excl & d['closed']).sum()),
           'reported_cycle_mean_d': rep.get('cycle_mean_d'), 'adjusted_cycle_mean_d': adj.get('cycle_mean_d'),
           'target_mean_d': adj.get('target_mean_d'),
           'event_effect_d': (rep.get('cycle_mean_d') or 0) - (adj.get('cycle_mean_d') or 0),
           'gap_to_target_d': (adj.get('cycle_mean_d') or 0) - (adj.get('target_mean_d') or 0),
           'kpi_changes': {k: {'reported': rep.get(k), 'adjusted': adj.get(k)} for k, _, _, _ in BENCH_KPIS}}
    if prior_mask is not None:
        pr = aggregate(T[prior_mask & ~T['exc_event'].isin(event_ids)])
        out['prior_cycle_mean_d'] = pr.get('cycle_mean_d')
        out['prior_target_mean_d'] = pr.get('target_mean_d')
    return out


def like_for_like(T, mask=None):
    """Site comparison restricted to materials produced at both sites, per material (removes product-mix effect)."""
    d = T if mask is None else T[mask]
    both = [m for m in C.PRODUCTS if all(m in C.SITE_PRODUCTS[s] for s in C.SITES)]
    out = []
    for m in both:
        for s in C.SITES:
            a = aggregate(d[(d['material'] == m) & (d['site'] == s)])
            dec = decompose(d[(d['material'] == m) & (d['site'] == s)])
            out.append({'material': m, 'product': C.PRODUCTS[m]['name'], 'site': C.SITES[s]['name'], **a,
                        'segments': {k: v for k, v in dec.items() if not k.startswith('_')}})
    return out


def open_batches(T):
    """Team-lead view: batches without usage decision at the cut-off, with age and the next expected step."""
    o = T[~T['closed']].copy()
    cut = pd.Timestamp(C.CUTOFF)
    o['age_d'] = (cut - o['mfg_complete']).dt.total_seconds() / 86400
    o['at_risk'] = o['age_d'] > 0.8 * o['target_d']
    return o.sort_values('age_d', ascending=False)
