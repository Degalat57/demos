/* Deterministic KPI engine for the static site (no backend, no LLM).
 * Mirrors src/brpi/kpis.py + analysis.py formulas; tests/test_js_parity.py checks both agree.
 * Works in the browser (window.Engine) and in node (module.exports). */
(function (root) {
  'use strict';
  const isNum = (x) => x !== null && x !== undefined && !Number.isNaN(x);
  const mean = (a) => { const v = a.filter(isNum); return v.length ? v.reduce((s, x) => s + x, 0) / v.length : null; };
  const sum = (a) => a.filter(isNum).reduce((s, x) => s + x, 0);
  function quantile(a, q) {           // pandas default (linear interpolation)
    const v = a.filter(isNum).slice().sort((x, y) => x - y);
    if (!v.length) return null;
    const pos = (v.length - 1) * q, lo = Math.floor(pos), hi = Math.ceil(pos);
    return v[lo] + (v[hi] - v[lo]) * (pos - lo);
  }
  const median = (a) => quantile(a, 0.5);
  const pct = (a) => (a.length ? (100 * a.filter(Boolean).length) / a.length : null);
  const stdPop = (a) => { const m = mean(a); return Math.sqrt(mean(a.map((x) => (x - m) * (x - m)))); };
  const clip = (x, lo = 0, hi = 100) => Math.min(hi, Math.max(lo, x));

  function hydrate(D) {
    const idx = {}; D.cols.forEach((c, i) => { idx[c] = i; });
    return D.cases.map((r) => {
      const o = {}; D.cols.forEach((c, i) => { o[c] = r[i]; });
      ['closed', 'split', 'hasDev', 'docRw', 'qaRep', 'retest', 'devReo', 'udChg', 'rework', 'rft', 'conf', 'compl',
        'seqExc', 'ontime', 'udAfterQc', 'udAfterDev', 'int1'].forEach((k) => { o[k] = !!o[k]; });
      return o;
    });
  }

  function filter(cases, f) {
    f = f || {};
    const ex = new Set(f.exclude || []);
    return cases.filter((c) => (!f.site || f.site === 'all' || c.site === f.site) &&
      (!f.mat || f.mat === 'all' || c.mat === f.mat) &&
      (!f.from || c.month >= f.from) && (!f.to || c.month <= f.to) && !(c.exc && ex.has(c.exc)));
  }

  function agg(cs) {
    const c = cs.filter((x) => x.closed);
    const out = { n_cases: cs.length, n_closed: c.length, n_open: cs.length - c.length };
    if (!c.length) return out;
    const split = c.filter((x) => x.split);
    const qa = c.filter((x) => isNum(x.qaWait));
    const dev = c.filter((x) => x.hasDev);
    Object.assign(out, {
      cycle_mean_d: mean(c.map((x) => x.cycle)), cycle_median_d: median(c.map((x) => x.cycle)),
      cycle_p90_d: quantile(c.map((x) => x.cycle), 0.9), target_mean_d: mean(c.map((x) => x.target)),
      ontime_pct: pct(c.map((x) => x.ontime)),
      processing_mean_d: split.length ? mean(split.map((x) => x.proc)) : null,
      waiting_mean_d: split.length ? mean(split.map((x) => x.wait)) : null,
      waiting_share_pct: split.length ? (100 * sum(split.map((x) => x.wait))) / sum(split.map((x) => x.cycle)) : null,
      split_coverage_pct: (100 * split.length) / c.length,
      qa_wait_mean_d: qa.length ? mean(qa.map((x) => x.qaWait)) : null,
      qa_wait_coverage_pct: (100 * qa.length) / c.length,
      qc_delay_mean_d: mean(c.map((x) => x.qcDelay)),
      dev_res_mean_d: dev.length ? mean(dev.map((x) => x.devRes)) : null,
      deviation_rate_pct: pct(c.map((x) => x.hasDev)), rework_pct: pct(c.map((x) => x.rework)),
      doc_rework_pct: pct(c.map((x) => x.docRw)), qa_repeat_pct: pct(c.map((x) => x.qaRep)),
      rft_pct: pct(c.map((x) => x.rft)), handoffs_mean: mean(c.map((x) => x.handoffs)),
      conformance_pct: pct(c.map((x) => x.conf)), compliance_pct: pct(c.map((x) => x.compl)),
    });
    return out;
  }

  const SEGS = [['Documentation (incl. rework) binding', 'segDoc'], ['QC results binding', 'segQc'],
    ['Deviation closure binding', 'segDev'], ['QA queue + disposition review', 'segQa'], ['Usage-decision approval wait', 'segAppr']];
  function decompose(cs) {
    const c = cs.filter((x) => x.closed && isNum(x.segQa));
    const out = {}; SEGS.forEach(([k, f]) => { out[k] = mean(c.map((x) => x[f])); });
    out._cycle_mean_d = mean(c.map((x) => x.cycle)); out._n = c.length;
    return out;
  }

  function ciShare(c, sustained) {
    if (!c.length) return 0;
    return c.filter((x) => (sustained['INT-01'] && x.int1)).length / c.length;
  }
  function maturity(cs, dims, sustained) {
    const c = cs.filter((x) => x.closed);
    if (!c.length) return null;
    const ratio = c.map((x) => x.cycle / x.target);
    const qa = c.map((x) => x.qaWait).filter(isNum);
    const qaMean = qa.length ? mean(qa) : 3.0;
    const s = {
      performance: pct(c.map((x) => x.ontime)),
      predictability: clip(100 * (1 - stdPop(ratio) / mean(ratio))),
      quality: pct(c.map((x) => x.rft)),
      standardization: pct(c.map((x) => x.conf)),
      efficiency: 0.7 * clip(100 * (1 - (qaMean - 1) / 4)) + 0.3 * clip(100 * (1 - (mean(c.map((x) => x.handoffs)) - 6) / 6)),
      compliance: pct(c.map((x) => x.compl)),
      improvement: 50 + 50 * ciShare(c, sustained || {}),
    };
    const contrib = {}; let score = 0;
    dims.forEach((d) => { contrib[d.key] = d.weight * s[d.key]; score += contrib[d.key]; });
    return { score, dims: s, contrib, n: c.length };
  }

  const quarter = (m) => m.slice(0, 4) + '-Q' + (Math.floor((+m.slice(5, 7) - 1) / 3) + 1);
  const SITE_NAME = { 1100: 'Site A', 2200: 'Site B' };
  function groupBy(cs, keyFn) { const g = new Map(); cs.forEach((c) => { const k = keyFn(c); if (!g.has(k)) g.set(k, []); g.get(k).push(c); }); return g; }

  function internalBest(cs, benchKpis, minN = 20) {
    const groups = [];
    groupBy(cs, (c) => c.site + '|' + quarter(c.month)).forEach((g, k) => {
      if (g.filter((x) => x.closed).length >= minN) groups.push(Object.assign(agg(g), { group: SITE_NAME[k.split('|')[0]] + ' ' + k.split('|')[1] }));
    });
    const best = {};
    benchKpis.forEach((b) => {
      const vals = groups.filter((g) => isNum(g[b.key])).map((g) => [g[b.key], g.group]);
      if (vals.length) best[b.key] = vals.reduce((a, v) => ((b.lower ? v[0] < a[0] : v[0] > a[0]) ? v : a));
    });
    return best;
  }

  const OPP = [
    ['qa_wait', 'QA review waiting', 'qaWait', (x) => (x.qaWait || 0) > 2, 'cov', null, 'Daily QA release stand-up with a visible queue and a review-ready trigger from QC/MES'],
    ['deviation', 'Deviation closure on the critical path', 'segDev', (x) => x.binding === 'Deviation closure', 1, null, 'Triage deviations at batch completion; fast lane for minor documentation deviations'],
    ['doc_rework', 'Batch record documentation rework', 'segDoc', (x) => x.docRw, 1, null, 'Right-first-time pre-check of batch records before QA review (replicate INT-01)'],
    ['qc', 'QC result availability (oral solid)', 'qcDelay', (x) => x.family === 'Oral solid' && x.binding === 'QC results', 1, (x) => x.family === 'Oral solid', 'Prioritise QC test queue by release due date; review lab capacity at peaks'],
    ['approval', 'Usage-decision approval wait', 'segAppr', (x) => x.segAppr > 1, 1, null, 'Release authorisations closer to QA review completion (e.g. extended QA release coverage)'],
  ];
  function opportunities(cs, all, effort) {
    const c = cs.filter((x) => x.closed && isNum(x.segQa));
    if (c.length < 10) return [];
    const allc = all.filter((x) => x.closed && isNum(x.segQa));
    const groups = groupBy(allc, (x) => x.site + '|' + quarter(x.month));
    const out = [];
    OPP.forEach(([key, title, col, affected, conf, sel, rec]) => {
      const cc = sel ? c.filter(sel) : c;
      const cur = cc.length ? mean(cc.map((x) => x[col])) : null;
      const vals = [];
      groups.forEach((g) => { const gg = sel ? g.filter(sel) : g; if (gg.length >= 15) vals.push(mean(gg.map((x) => x[col]))); });
      if (!isNum(cur) || !vals.length) return;
      const b = Math.min(...vals);
      const impact = Math.max(0, cur - b);
      const freq = c.filter(affected).length / c.length;
      const cf = conf === 'cov' ? c.filter((x) => isNum(x.qaWait)).length / c.length : conf;
      out.push({ key, title, current_d: cur, internal_best_d: b, impact_d: impact, frequency: freq, frequency_pct: 100 * freq,
        confidence: cf, effort: effort[key], score: (impact * freq * cf) / effort[key], recommendation: rec });
    });
    return out.sort((a, b) => b.score - a.score);
  }

  function fastSlow(cs) {
    const c = cs.filter((x) => x.closed);
    const r = c.map((x) => x.cycle / x.target);
    const lo = quantile(r, 0.25), hi = quantile(r, 0.75);
    const prof = (x) => ({ n: x.length, cycle_mean_d: mean(x.map((y) => y.cycle)), deviation_pct: pct(x.map((y) => y.hasDev)),
      doc_rework_pct: pct(x.map((y) => y.docRw)), doc_loops2_pct: pct(x.map((y) => y.docLoops >= 2)),
      qa_repeat_pct: pct(x.map((y) => y.qaRep)), retest_pct: pct(x.map((y) => y.retest)),
      qa_wait_mean_d: mean(x.map((y) => y.qaWait)), handoffs_mean: mean(x.map((y) => y.handoffs)),
      conformance_pct: pct(x.map((y) => y.conf)), site_a_share_pct: pct(x.map((y) => y.site === '1100')) });
    return { fast: prof(c.filter((x, i) => r[i] <= lo)), slow: prof(c.filter((x, i) => r[i] >= hi)), fast_max_ratio: lo, slow_min_ratio: hi };
  }

  function facts(cs) {
    const c = cs.filter((x) => x.closed);
    const late = c.filter((x) => !x.ontime), ok = c.filter((x) => x.ontime), late5 = c.filter((x) => x.cycle > x.target + 5);
    return { late_with_dev_pct: pct(late.map((x) => x.hasDev)), ontime_with_dev_pct: pct(ok.map((x) => x.hasDev)),
      late5_with_dev_pct: pct(late5.map((x) => x.hasDev)), n_late: late.length, n_ontime: ok.length, n_late5: late5.length };
  }

  function dfg(cs, trans) {
    const acc = new Map();
    cs.forEach((c) => (trans[c.id] || []).forEach(([a, b, w]) => {
      const k = a + '>' + b; if (!acc.has(k)) acc.set(k, []); acc.get(k).push(w);
    }));
    const out = [];
    acc.forEach((v, k) => { const [a, b] = k.split('>').map(Number); out.push({ from: a, to: b, count: v.length, median_wait_h: median(v), mean_wait_h: mean(v) }); });
    return out;
  }

  // ---------------------------------------------------------------- statistics
  function rankTies(vals) {
    const idx = vals.map((v, i) => [v, i]).sort((a, b) => a[0] - b[0]);
    const ranks = new Array(vals.length); const ties = [];
    for (let i = 0; i < idx.length;) {
      let j = i; while (j + 1 < idx.length && idx[j + 1][0] === idx[i][0]) j++;
      const r = (i + j) / 2 + 1; for (let k = i; k <= j; k++) ranks[idx[k][1]] = r;
      if (j > i) ties.push(j - i + 1); i = j + 1;
    }
    return { ranks, ties };
  }
  function normSf(z) {                 // survival function of N(0,1)
    const t = 1 / (1 + 0.2316419 * Math.abs(z));
    const d = 0.3989422804014327 * Math.exp(-z * z / 2);
    const p = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    return z >= 0 ? p : 1 - p;
  }
  function mannWhitney(x, y) {          // two-sided, normal approximation with tie + continuity correction (as scipy 'asymptotic')
    const n1 = x.length, n2 = y.length; if (!n1 || !n2) return { U: null, p: null };
    const { ranks, ties } = rankTies(x.concat(y));
    const R1 = ranks.slice(0, n1).reduce((s, r) => s + r, 0);
    const U1 = R1 - (n1 * (n1 + 1)) / 2; const mu = (n1 * n2) / 2; const n = n1 + n2;
    const tieTerm = ties.reduce((s, t) => s + (t * t * t - t), 0);
    const sd = Math.sqrt((n1 * n2 / 12) * ((n + 1) - tieTerm / (n * (n - 1))));
    const U = Math.max(U1, n1 * n2 - U1);
    const z = (U - mu - 0.5) / sd;
    return { U: U1, p: Math.min(1, 2 * normSf(z)) };
  }
  const lf = (() => { const c = [0]; return (n) => { while (c.length <= n) c.push(c[c.length - 1] + Math.log(c.length)); return c[n]; }; })();
  function fisher(a, b, c, d) {          // two-sided Fisher exact for [[a,b],[c,d]]
    const r1 = a + b, r2 = c + d, c1 = a + c, n = r1 + r2;
    const lp = (x) => lf(r1) + lf(r2) + lf(c1) + lf(n - c1) - lf(n) - lf(x) - lf(r1 - x) - lf(c1 - x) - lf(r2 - c1 + x);
    const p0 = lp(a); let p = 0;
    for (let x = Math.max(0, c1 - r2); x <= Math.min(r1, c1); x++) { const v = lp(x); if (v <= p0 + 1e-7) p += Math.exp(v); }
    return Math.min(1, p);
  }
  function rng(seed) { let s = seed >>> 0; return () => { s += 0x6D2B79F5; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  function bootstrap(a, b, fn, n = 1000, seed = 7) {
    const r = rng(seed); const vals = [];
    const pick = (arr) => { const o = new Array(arr.length); for (let i = 0; i < arr.length; i++) o[i] = arr[Math.floor(r() * arr.length)]; return o; };
    for (let i = 0; i < n; i++) vals.push(fn(pick(b), pick(a)));
    return [quantile(vals, 0.025), quantile(vals, 0.975)];
  }
  function prePost(cases, site, pre, post, opts) {
    opts = opts || {};
    const inW = (c, w) => c.mfg >= w[0] && c.mfg <= w[1];
    const base = cases.filter((c) => c.closed && (!opts.excludeExc || !c.exc) && (!opts.mat || opts.mat === 'all' || c.mat === opts.mat));
    const S = base.filter((c) => c.site === site), O = base.filter((c) => c.site !== site);
    const defs = [['docRw', 'Documentation rework', 'rate'], ['qaWait', 'QA review waiting', 'cont'],
      ['cycle', 'Release cycle time', 'cont'], ['rft', 'Right first time', 'rate']];
    return defs.map(([k, label, kind]) => {
      const get = (arr, w) => arr.filter((c) => inW(c, w)).map((c) => c[k]).filter((v) => v !== null && v !== undefined);
      const a = get(S, pre), b = get(S, post), ca = get(O, pre), cb = get(O, post);
      const r = { kpi: k, label, kind, n_pre: a.length, n_post: b.length };
      if (!a.length || !b.length) return r;
      if (kind === 'rate') {
        const A = a.map(Number), B = b.map(Number);
        r.pre = 100 * mean(A); r.post = 100 * mean(B);
        const sa = sum(A), sb = sum(B);
        r.test = 'Fisher exact (two-sided)'; r.p_value = fisher(sb, B.length - sb, sa, A.length - sa);
        r.ci95 = bootstrap(A, B, (x, y) => 100 * (mean(x) - mean(y)));
        r.comparison_site_change = ca.length && cb.length ? 100 * (mean(cb.map(Number)) - mean(ca.map(Number))) : null;
      } else {
        r.pre = median(a); r.post = median(b);
        r.test = 'Mann-Whitney U (two-sided)'; r.p_value = mannWhitney(b, a).p;
        r.ci95 = bootstrap(a, b, (x, y) => median(x) - median(y));
        r.comparison_site_change = ca.length && cb.length ? mean(cb) - mean(ca) : null;
      }
      r.change = r.post - r.pre; r.change_pct = r.pre ? (100 * r.change) / r.pre : null;
      const scale = kind === 'rate' ? 100 : 1;
      r.did_means = ca.length && cb.length ? scale * ((mean(b.map(Number)) - mean(a.map(Number))) - (mean(cb.map(Number)) - mean(ca.map(Number)))) : null;
      r.significant = r.p_value < 0.05 && !(r.ci95[0] <= 0 && r.ci95[1] >= 0);
      return r;
    });
  }

  const api = { hydrate, filter, agg, decompose, maturity, internalBest, opportunities, fastSlow, facts, dfg, mannWhitney,
    fisher, bootstrap, prePost, quantile, median, mean, pct, SEGS, quarter, groupBy };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.Engine = api;
})(typeof window !== 'undefined' ? window : this);
