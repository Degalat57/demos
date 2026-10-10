/* UI for the Batch Release Process Intelligence demo. All numbers are computed by assets/engine.js from the
 * precomputed, synthetic event-log bundle (assets/data.js). */
(function () {
  'use strict';
  const D = window.BRPI, E = window.Engine;
  const CASES = E.hydrate(D);
  const ACT = D.activities, ROLES = D.roles;
  const SITE = (s) => D.sites[s].name;
  const MONTHS = [...new Set(CASES.map((c) => c.month))].sort();
  const COMPLETE = D.meta.complete_through;
  const EXC_IDS = D.exceptional_events.map((e) => e.id);
  const $ = (s, r) => (r || document).querySelector(s);
  const esc = (s) => String(s === null || s === undefined ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const isNum = (x) => x !== null && x !== undefined && !Number.isNaN(x);
  const f1 = (x) => (isNum(x) ? x.toFixed(1) : '–'), f0 = (x) => (isNum(x) ? x.toFixed(0) : '–'), f2 = (x) => (isNum(x) ? x.toFixed(2) : '–');
  const fp = (p) => (!isNum(p) ? '–' : p < 0.001 ? '< 0.001' : '= ' + p.toFixed(3));
  const sgn = (x, d = 1) => { if (!isNum(x)) return '–'; const t = x.toFixed(d); return +t === 0 ? (0).toFixed(d) : (x > 0 ? '+' : '') + t; };
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const SERIES = () => ['--s1', '--s2', '--s3', '--s4', '--s5', '--s6', '--s7', '--s8'].map(css);
  const SITE_COLOR = (s) => (s === '1100' ? css('--s1') : css('--s2'));
  const ROLE_LIST = [...new Set(ROLES)];

  const state = { site: 'all', mat: 'all', from: MONTHS[0], to: COMPLETE, exc: false, tab: 'framework', level: 'L1',
    fws: new Set(['EU GMP Annex 16', 'ICH Q10', 'APQC Life Sciences PCF']), analyzed: false, kpi: 'cycle_mean_d',
    pmMode: 'freq', pmMin: 15, ivSite: '1100', ivDate: '2026-06-01', ivDays: 92, ivExc: true };
  const F = () => ({ site: state.site, mat: state.mat, from: state.from, to: state.to, exclude: state.exc ? EXC_IDS : [] });
  const scope = () => E.filter(CASES, F());
  const scopeNoSite = () => E.filter(CASES, Object.assign(F(), { site: 'all' }));
  const scopeLabel = () => [state.site === 'all' ? 'both sites' : SITE(state.site), state.mat === 'all' ? 'all products' : D.products[state.mat].name,
    state.from + ' to ' + state.to, state.exc ? 'exceptional events excluded' : 'all batches'].join(' · ');

  // ---------------------------------------------------------------- charts
  const charts = {};
  function chart(id, opt) {
    const node = document.getElementById(id);
    if (!node) return;
    if (!window.echarts) { node.innerHTML = '<p class="muted small">Chart library not loaded (offline). The tables show the same numbers.</p>'; return; }
    if (charts[id]) charts[id].dispose();
    const c = window.echarts.init(node, null, { renderer: 'svg' });
    const ink = css('--ink-2'), line = css('--line'), muted = css('--muted');
    c.setOption(Object.assign({ animation: false, textStyle: { fontFamily: 'system-ui, sans-serif', color: ink },
      grid: { left: 48, right: 16, top: 30, bottom: 36, containLabel: true },
      tooltip: { trigger: 'axis', backgroundColor: css('--surface'), borderColor: css('--line-2'), textStyle: { color: css('--ink'), fontSize: 12 } },
      legend: { top: 0, textStyle: { color: ink, fontSize: 12 }, itemWidth: 14, itemHeight: 8 } }, opt));
    if (opt.xAxis && !Array.isArray(opt.xAxis)) c.setOption({ xAxis: { axisLine: { lineStyle: { color: line } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: line } } } });
    if (opt.yAxis && !Array.isArray(opt.yAxis)) c.setOption({ yAxis: { axisLine: { lineStyle: { color: line } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: line } } } });
    charts[id] = c;
  }
  window.addEventListener('resize', () => Object.values(charts).forEach((c) => c.resize()));

  // ---------------------------------------------------------------- shared computations
  function monthly(cs, fn) {
    const g = E.groupBy(cs, (c) => c.month);
    return MONTHS.filter((m) => m >= state.from && m <= state.to).map((m) => {
      const x = g.get(m) || []; return { m, v: x.length ? fn(x) : null, open: x.filter((c) => !c.closed).length, n: x.length };
    });
  }
  const provisional = (m) => m > COMPLETE;
  const lastMonths = (k) => MONTHS.filter((m) => m >= state.from && m <= state.to && m <= COMPLETE).slice(-k);
  function trendOf(key, cs) {
    const ms = MONTHS.filter((m) => m >= state.from && m <= state.to && m <= COMPLETE);
    if (ms.length < 4) return null;
    const k = Math.min(3, Math.floor(ms.length / 2));
    const a = E.agg(cs.filter((c) => ms.slice(-2 * k, -k).includes(c.month)))[key];
    const b = E.agg(cs.filter((c) => ms.slice(-k).includes(c.month)))[key];
    return isNum(a) && isNum(b) ? b - a : null;
  }
  function trendCell(key, cs, lower) {
    const t = trendOf(key, cs);
    if (!isNum(t)) return '<span class="muted">–</span>';
    const good = lower ? t < 0 : t > 0;
    const arrow = Math.abs(t) < 1e-9 ? '→' : t < 0 ? '↓' : '↑';
    return '<span class="' + (good ? 'trend-down' : 'trend-up') + '" title="last 3 complete months vs previous 3">' + arrow + ' ' + sgn(t) + '</span>';
  }
  function frameworkAssess(cs) {
    const c = cs.filter((x) => x.closed), dev = c.filter((x) => x.hasDev);
    const v = { ud_after_qc: E.pct(c.map((x) => x.udAfterQc)), ud_after_dev: dev.length ? E.pct(dev.map((x) => x.udAfterDev)) : 100,
      seq_exception: dev.length ? E.pct(dev.map((x) => x.seqExc)) : 0, monitoring: E.pct(c.map((x) => x.split)),
      reopen: dev.length ? E.pct(dev.map((x) => x.devReo)) : 0, internal: E.pct(c.map((x) => x.ontime)) };
    return D.framework.mapping.map((m) => {
      const k = m.check, val = v[k]; let status, ev;
      if (k === 'seq_exception') { status = val === 0 ? 'aligned' : 'investigate'; ev = f1(val) + '% of ' + dev.length + ' batches with deviations'; }
      else if (k === 'ud_after_qc' || k === 'ud_after_dev') { status = val >= 99.95 ? 'aligned' : 'investigate'; ev = f1(val) + '% of ' + (k === 'ud_after_qc' ? c.length : dev.length) + ' batches'; }
      else if (k === 'monitoring') { status = val >= 80 ? 'aligned' : 'missing evidence'; ev = 'start-time coverage for the waiting/processing split: ' + f1(val) + '%'; }
      else if (k === 'reopen') { status = val <= 5 ? 'aligned' : 'investigate'; ev = f1(val) + '% of batches with deviations had a reopened deviation'; }
      else if (k === 'internal') { status = val >= 80 ? 'aligned' : 'investigate'; ev = f1(val) + '% released within target'; }
      else if (k === 'review') { status = 'aligned'; ev = 'maturity score and intervention tracking produced by this tool'; }
      else if (k === 'risk') { status = 'missing evidence'; ev = 'exceptional events linked via deviation references; formal risk assessments are not in the extract'; }
      else { status = 'aligned'; ev = '14 activities mapped to 5 L3 areas'; }
      return Object.assign({}, m, { value: val, evidence_value: ev, status });
    });
  }
  const statusPill = (s) => '<span class="pill ' + (s === 'aligned' ? 'good' : s === 'investigate' ? 'bad' : 'warn') + '">' +
    (s === 'aligned' ? '✓ ' : s === 'investigate' ? '! ' : '? ') + esc(s) + '</span>';
  function benchRows(cs) {
    const a = E.agg(cs), best = E.internalBest(scopeNoSite(), D.bench_kpis);
    return D.bench_kpis.map((b) => {
      let target = b.key === 'cycle_mean_d' ? a.target_mean_d : D.targets[b.key];
      const v = a[b.key];
      const gap = isNum(v) && isNum(target) ? v - target : null;
      const cov = b.key === 'qa_wait_mean_d' ? a.qa_wait_coverage_pct : 100;
      return Object.assign({}, b, { value: v, target, best: best[b.key], gap, bad: isNum(gap) && (b.lower ? gap > 0 : gap < 0), cov });
    });
  }
  const unitFmt = (v, u) => (isNum(v) ? (u === '%' ? f1(v) + '%' : u === 'd' ? f1(v) + ' d' : f1(v)) : '–');
  const gapFmt = (g, u) => (isNum(g) ? sgn(g) + (u === '%' ? ' pts' : u === 'd' ? ' d' : '') : '–');

  // ---------------------------------------------------------------- tab 1: framework & process selection
  const FW_OPTS = [
    ['EU GMP Annex 16', 'GMP', 'Practices, controls and compliance expectations (QP certification & batch release)'],
    ['ICH Q9(R1)', 'ICH Q9(R1)', 'Quality risk management lens: identify, evaluate, control, review'],
    ['ICH Q10', 'ICH Q10', 'Pharmaceutical quality system and continual-improvement lens'],
    ['APQC Life Sciences PCF', 'APQC Life Sciences', 'Standard process hierarchy (L1-L4) and comparable measures'],
    ['Internal framework', 'Internal framework', 'SOPs, internal targets and best-site practice'],
  ];
  function renderFramework() {
    const p = $('#p-framework');
    p.innerHTML = `<h2>Framework &amp; process selection</h2>
      <p class="lead">Choose the lens, the process and the scope, then let the system reconstruct the process from the event log, compute the KPIs deterministically and assess it against the selected frameworks.</p>
      <div class="grid g32">
        <div class="card"><h3>1 · Frameworks</h3><div class="fw-opts">${FW_OPTS.map(([k, t, d]) => `<label class="fw-opt ${state.fws.has(k) ? 'on' : ''}"><input type="checkbox" data-fw="${esc(k)}" ${state.fws.has(k) ? 'checked' : ''}><div><b>${esc(t)}</b><span>${esc(d)}</span></div></label>`).join('')}</div>
          <p class="small muted" style="margin-bottom:0">APQC answers <i>what process is this and how do we measure it</i>; GMP / ICH Q9 / Q10 answer <i>which quality, risk and control principles it must reflect</i>; the internal framework answers <i>what good means here</i>. They are evaluated differently, not as one checklist.</p></div>
        <div class="card"><h3>2 · Process &amp; 3 · Scope</h3>
          <label class="small muted">Process</label><br><select id="proc" style="width:100%;margin:4px 0 10px"><option>Manufacturing quality → Batch Review &amp; Release</option><option disabled>Deviation management (next process)</option><option disabled>CAPA (next process)</option></select>
          <div class="note">Scope: <b>${esc(scopeLabel())}</b><br>Change site, product and period in the filter bar at the top; every screen recalculates in the browser.</div>
          <div style="margin-top:14px;text-align:center"><button class="btn primary big" id="analyze">ANALYZE MY PROCESS</button></div></div>
      </div>
      <div id="analyze-out" class="analyze-out"></div>`;
    p.querySelectorAll('[data-fw]').forEach((i) => i.addEventListener('change', () => {
      i.checked ? state.fws.add(i.dataset.fw) : state.fws.delete(i.dataset.fw); renderFramework();
    }));
    $('#analyze').addEventListener('click', () => { state.analyzed = true; renderAnalyze(); $('#analyze-out').scrollIntoView({ behavior: 'smooth' }); });
    if (state.analyzed) renderAnalyze();
  }
  function ring(score) {
    const r = 50, c = 2 * Math.PI * r, v = Math.max(0, Math.min(100, score));
    return `<svg class="ring" viewBox="0 0 120 120" role="img" aria-label="Process health ${f0(score)} of 100"><circle cx="60" cy="60" r="${r}" fill="none" stroke="${css('--surface-2')}" stroke-width="12"/>
      <circle cx="60" cy="60" r="${r}" fill="none" stroke="${css('--accent')}" stroke-width="12" stroke-linecap="round" stroke-dasharray="${(c * v) / 100} ${c}" transform="rotate(-90 60 60)"/>
      <text x="60" y="60" text-anchor="middle" font-size="30" font-weight="700" fill="${css('--ink')}">${f0(score)}</text><text x="60" y="80" text-anchor="middle" font-size="12" fill="${css('--muted')}">/ 100</text></svg>`;
  }
  function renderAnalyze() {
    const cs = scope(), a = E.agg(cs), m = E.maturity(cs, D.maturity_dims, D.ci_sustained);
    if (!m) { $('#analyze-out').innerHTML = '<div class="card">No closed batches in this scope.</div>'; return; }
    const rows = benchRows(cs).filter((r) => ['cycle_mean_d', 'qa_wait_mean_d', 'doc_rework_pct', 'rft_pct', 'dev_res_mean_d', 'handoffs_mean'].includes(r.key));
    const ops = E.opportunities(cs, CASES, D.effort).slice(0, 3);
    const fw = frameworkAssess(cs).filter((r) => [...state.fws].some((f) => r.framework.startsWith(f.split(' ')[0] === 'EU' ? 'EU GMP' : f)));
    const groups = { aligned: [], investigate: [], 'missing evidence': [] };
    fw.forEach((r) => groups[r.status].push(r));
    const dq = D.dq.rules;
    $('#analyze-out').innerHTML = `<div class="grid g3">
      <div class="card"><h3>1 · Process health</h3><div class="health">${ring(m.score)}<div class="small">Explainable maturity score: weighted sum of ${D.maturity_dims.length} dimensions (see Improvement &amp; maturity).<br><b>${a.n_closed}</b> released batches, <b>${a.n_open}</b> open at cut-off.</div></div></div>
      <div class="card"><h3>3 · Top issues</h3><ol class="issues">${ops.map((o) => `<li><b>${esc(o.title)}</b> <span class="muted small">${f1(o.impact_d)} d/batch above internal best · ${f0(o.frequency_pct)}% of batches</span></li>`).join('')}</ol></div>
      <div class="card"><h3>Data foundation</h3><div class="small">${D.meta.n_events.toLocaleString()} events from 10 source tables · ${dq.R2_duplicates_collapsed.total} duplicates collapsed · ${dq.R4_lineage.splits} split / ${dq.R4_lineage.merges} merge links · ${dq.R5_crosswalk.rows_excluded.MES + dq.R5_crosswalk.rows_excluded.QMS} MES/QMS rows not matched (reported) · QA-waiting coverage ${f1(a.qa_wait_coverage_pct)}%.</div><button class="btn" style="margin-top:8px" data-goto="explorer">See event log &amp; data quality →</button></div>
    </div>
    <div class="card" style="margin-top:14px"><h3>2 · Current KPI performance</h3><div class="tbl-wrap"><table><thead><tr><th>KPI</th><th class="num">Current</th><th class="num">Target</th><th class="num">Gap</th><th class="num">Trend</th></tr></thead><tbody>
      ${rows.map((r) => `<tr><td class="kpi-name">${esc(r.label)}</td><td class="num">${unitFmt(r.value, r.unit)}</td><td class="num">${unitFmt(r.target, r.unit)}</td><td class="num ${r.bad ? 'trend-up' : 'trend-down'}">${gapFmt(r.gap, r.unit)}</td><td class="num">${trendCell(r.key, cs, r.lower)}</td></tr>`).join('')}
      </tbody></table></div><p class="small muted">Targets are illustrative internal targets (cycle target is product-weighted: oral solids 9 d, sterile 19-21 d because of the 14-day sterility test).</p></div>
    <div class="grid g2" style="margin-top:14px">
      <div class="card"><h3>4 · Framework assessment <span class="pill warn">DRAFT for SME sign-off</span></h3>
        ${['investigate', 'missing evidence', 'aligned'].map((s) => groups[s].length ? `<h4 style="margin:10px 0 4px">${s === 'aligned' ? 'Aligned with selected framework' : s === 'investigate' ? 'Requires investigation' : 'Missing evidence / data'}</h4>` +
          groups[s].map((r) => `<div class="callout ${s === 'aligned' ? '' : 'hyp'}"><b>${esc(r.framework)}</b> · ${esc(r.ref)}<br><span class="pill fw">reference</span> ${esc(r.expectation)}<br><span class="pill fact">evidence</span> ${esc(r.evidence_value)} &nbsp;${statusPill(r.status)}</div>`).join('') : '').join('')}
        ${fw.length ? '' : '<p class="muted">Select at least one framework above.</p>'}</div>
      <div class="card"><h3>5 · Top improvement opportunities</h3><p class="sub">Ranked by impact × frequency × confidence ÷ effort/risk</p>
        <div class="tbl-wrap"><table><thead><tr><th>Opportunity</th><th class="num">Impact</th><th class="num">Freq.</th><th class="num">Conf.</th><th class="num">Effort</th><th class="num">Score</th></tr></thead><tbody>
        ${ops.map((o) => `<tr><td><b>${esc(o.title)}</b><br><span class="small muted">${esc(o.recommendation)}</span></td><td class="num">${f1(o.impact_d)} d</td><td class="num">${f0(o.frequency_pct)}%</td><td class="num">${f2(o.confidence)}</td><td class="num">${f1(o.effort)}</td><td class="num"><b>${f2(o.score)}</b></td></tr>`).join('')}
        </tbody></table></div><p class="small muted">Impact = mean days per batch above the internal best site-quarter. Effort/risk weights are assumptions for the process owner to confirm.</p></div>
    </div>`;
    bindGoto($('#analyze-out'));
  }
  function bindGoto(root) { root.querySelectorAll('[data-goto]').forEach((b) => b.addEventListener('click', () => showTab(b.dataset.goto))); }

  // ---------------------------------------------------------------- tab 2: executive cockpit
  function tiles(cs) {
    const a = E.agg(cs), m = E.maturity(cs, D.maturity_dims, D.ci_sustained);
    const ms = lastMonths(3), ms0 = MONTHS.filter((x) => x >= state.from && x <= COMPLETE).slice(0, 3);
    const m0 = E.maturity(cs.filter((c) => ms0.includes(c.month)), D.maturity_dims, D.ci_sustained);
    const m1 = E.maturity(cs.filter((c) => ms.includes(c.month)), D.maturity_dims, D.ci_sustained);
    const t = (k, v, d) => `<div class="card tile"><div class="k">${k}</div><div class="v">${v}</div><div class="d">${d}</div></div>`;
    return `<div class="grid g4">
      ${t('Quality-process maturity', f0(m ? m.score : null) + '<small>/100</small>', m0 && m1 ? `${f0(m0.score)} → ${f0(m1.score)} (first vs last 3 complete months)` : '')}
      ${t('Release cycle time (outcome)', f1(a.cycle_mean_d) + '<small>d mean</small>', `target ${f1(a.target_mean_d)} d · median ${f1(a.cycle_median_d)} d · P90 ${f1(a.cycle_p90_d)} d`)}
      ${t('Released within target', f0(a.ontime_pct) + '<small>%</small>', `right first time ${f0(a.rft_pct)}% · rework ${f0(a.rework_pct)}%`)}
      ${t('Waiting share of elapsed time', f0(a.waiting_share_pct) + '<small>%</small>', `on ${f0(a.split_coverage_pct)}% of batches with complete start times; rest "elapsed, unsplit"`)}
    </div>`;
  }
  function decompBar(id, cs) {
    const d = E.decompose(cs);
    const keys = E.SEGS.map((s) => s[0]);
    const col = SERIES();
    chart(id, { tooltip: { trigger: 'item', formatter: (p) => `${p.seriesName}: <b>${f2(p.value)} d</b>` }, legend: { top: 0 },
      grid: { left: 10, right: 20, top: 64, bottom: 10, containLabel: true },
      xAxis: { type: 'value' }, yAxis: { type: 'category', data: ['Cycle'] },
      series: keys.map((k, i) => ({ name: k, type: 'bar', stack: 'a', data: [+(d[k] || 0).toFixed(3)], itemStyle: { color: col[i], borderColor: css('--surface'), borderWidth: 2 }, barWidth: 34 })) });
    return d;
  }
  function trendChart(id, cs, key, label, withTarget) {
    const sites = state.site === 'all' ? Object.keys(D.sites) : [state.site];
    const ms = MONTHS.filter((m) => m >= state.from && m <= state.to);
    const series = sites.map((s) => ({ name: SITE(s), type: 'line', symbolSize: 7, lineStyle: { width: 2 }, itemStyle: { color: SITE_COLOR(s) },
      data: ms.map((m) => { const v = E.agg(cs.filter((c) => c.site === s && c.month === m))[key]; return isNum(v) ? +v.toFixed(2) : null; }) }));
    if (withTarget) series.push({ name: 'Target', type: 'line', symbol: 'none', lineStyle: { type: 'dashed', width: 1.5, color: css('--muted') }, itemStyle: { color: css('--muted') },
      data: ms.map((m) => { const v = E.agg(cs.filter((c) => c.month === m)).target_mean_d; return isNum(v) ? +v.toFixed(2) : null; }) });
    const prov = ms.filter(provisional);
    if (prov.length) series[0].markArea = { silent: true, itemStyle: { color: css('--surface-2') }, label: { show: true, color: css('--muted'), fontSize: 11, position: 'insideTop' }, data: [[{ name: 'provisional', xAxis: prov[0] }, { xAxis: prov[prov.length - 1] }]] };
    chart(id, { xAxis: { type: 'category', data: ms }, yAxis: { type: 'value', name: label, nameTextStyle: { color: css('--muted') } }, series });
  }
  function siteMaturityRows() {
    const ms = lastMonths(3), ms0 = MONTHS.filter((x) => x >= state.from && x <= COMPLETE).slice(0, 3);
    return Object.keys(D.sites).map((s) => {
      const cs = E.filter(CASES, Object.assign(F(), { site: s }));
      const m1 = E.maturity(cs.filter((c) => ms.includes(c.month)), D.maturity_dims, D.ci_sustained);
      const m0 = E.maturity(cs.filter((c) => ms0.includes(c.month)), D.maturity_dims, D.ci_sustained);
      const gap = m1 ? 80 - m1.score : null;
      return { s, m1, m0, gap, prio: !isNum(gap) ? '–' : gap > 20 ? 'High' : gap > 10 ? 'Medium' : 'Low' };
    });
  }
  function renderCockpit() {
    const cs = scope();
    const lv = state.level;
    const p = $('#p-cockpit');
    p.innerHTML = `<h2>Executive quality-process cockpit</h2><p class="lead">${esc(scopeLabel())}</p>
      <div class="level-ctl"><span class="small muted">View as</span><div class="seg-ctl" id="lv">${[['L1', 'Head of PEx / MQ'], ['L2', 'Site / process owner'], ['L3', 'Quality manager'], ['L4', 'Team lead']].map(([k, t]) => `<button data-l="${k}" class="${lv === k ? 'on' : ''}">${t}</button>`).join('')}</div><span class="small muted">Drill path: enterprise → site → process → sub-process → activity → batch</span></div>
      ${tiles(cs)}
      <div class="grid g2" style="margin-top:14px">
        <div class="card"><h3>Outcome KPI → process KPI drivers</h3><p class="sub">Mean release cycle split along the critical path; segments add up exactly to the outcome.</p><div id="c-dec" class="chart short"></div><div id="dec-txt" class="small"></div></div>
        <div class="card"><h3>Trend · release cycle time by site</h3><p class="sub">Months after ${COMPLETE} are provisional (open batches, right-censored).</p><div id="c-trend" class="chart short"></div></div>
      </div>
      <div id="lv-panel" style="margin-top:14px"></div>`;
    p.querySelectorAll('#lv button').forEach((b) => b.addEventListener('click', () => { state.level = b.dataset.l; renderCockpit(); }));
    const d = decompBar('c-dec', cs);
    const tot = d._cycle_mean_d;
    $('#dec-txt').innerHTML = `<b>${f1(tot)} d</b> = ` + E.SEGS.map(([k]) => `${f1(d[k])} d ${esc(k.replace(' binding', ''))}`).join(' + ') + ` <span class="muted">(n = ${d._n})</span>`;
    trendChart('c-trend', cs, 'cycle_mean_d', 'days', true);
    const lp = $('#lv-panel');
    if (lv === 'L1') {
      const sm = siteMaturityRows();
      const fw = frameworkAssess(cs).filter((r) => r.status !== 'aligned');
      const ops = E.opportunities(cs, CASES, D.effort).slice(0, 3);
      lp.innerHTML = `<div class="grid g3"><div class="card"><h3>Maturity by site</h3><table><thead><tr><th>Site</th><th class="num">Maturity</th><th class="num">Trend</th><th class="num">Gap to 80</th><th>Priority</th></tr></thead><tbody>
        ${sm.map((r) => `<tr><td>${SITE(r.s)}</td><td class="num">${f0(r.m1 && r.m1.score)}</td><td class="num">${r.m0 && r.m1 ? sgn(r.m1.score - r.m0.score, 0) : '–'}</td><td class="num">${f0(r.gap)}</td><td><span class="pill ${r.prio === 'High' ? 'bad' : r.prio === 'Medium' ? 'warn' : 'good'}">${r.prio}</span></td></tr>`).join('')}</tbody></table><p class="small muted">Last 3 complete months vs first 3 months of scope. 80 = illustrative ambition level.</p></div>
        <div class="card"><h3>Top framework gaps</h3>${fw.map((r) => `<div class="callout hyp"><b>${esc(r.framework)}</b>: ${esc(r.evidence_value)} ${statusPill(r.status)}</div>`).join('') || '<p class="muted">None in scope.</p>'}</div>
        <div class="card"><h3>Top systemic opportunities</h3><ol class="issues">${ops.map((o) => `<li><b>${esc(o.title)}</b><br><span class="small muted">${f1(o.impact_d)} d/batch to internal best · ${f0(o.frequency_pct)}% of batches · score ${f2(o.score)}</span></li>`).join('')}</ol></div></div>`;
    } else if (lv === 'L2') {
      const both = Object.keys(D.products).filter((m) => Object.values(D.sites).length && ['1100', '2200'].every((s) => CASES.some((c) => c.site === s && c.mat === m)));
      const all = E.filter(CASES, Object.assign(F(), { site: 'all' }));
      const vs = variantStats(cs).slice(0, 5);
      lp.innerHTML = `<div class="grid g2"><div class="card"><h3>Site comparison, like-for-like products</h3><p class="sub">Only materials made at both sites, so product mix does not distort the comparison.</p><div class="tbl-wrap"><table><thead><tr><th>Product</th><th>Site</th><th class="num">n</th><th class="num">Cycle</th><th class="num">QA stage</th><th class="num">Doc rework</th><th class="num">RFT</th></tr></thead><tbody>
        ${both.map((m) => ['1100', '2200'].map((s) => { const x = all.filter((c) => c.mat === m && c.site === s); const a = E.agg(x), d = E.decompose(x); return `<tr><td>${esc(D.products[m].name)}</td><td><span class="dot" style="background:${SITE_COLOR(s)}"></span> ${SITE(s)}</td><td class="num">${a.n_closed}</td><td class="num">${f1(a.cycle_mean_d)} d</td><td class="num">${f1(d['QA queue + disposition review'])} d</td><td class="num">${f0(a.doc_rework_pct)}%</td><td class="num">${f0(a.rft_pct)}%</td></tr>`; }).join('')).join('')}</tbody></table></div></div>
        <div class="card"><h3>Process variants (top 5)</h3>${variantTable(vs, cs.filter((c) => c.closed).length)}<button class="btn" data-goto="explorer">Open process explorer →</button></div></div>`;
      bindGoto(lp);
    } else if (lv === 'L3') {
      const a = E.agg(cs), d = E.decompose(cs), ops = E.opportunities(cs, CASES, D.effort);
      lp.innerHTML = `<div class="grid g3"><div class="card"><h3>Waiting</h3>${barRows([['QA queue + review', d['QA queue + disposition review']], ['of which waiting', a.qa_wait_mean_d], ['Approval wait', d['Usage-decision approval wait']], ['QC result availability', a.qc_delay_mean_d], ['Deviation resolution', a.dev_res_mean_d]], 'd')}</div>
        <div class="card"><h3>Rework &amp; exceptions</h3>${barRows([['Any rework', a.rework_pct], ['Documentation rework', a.doc_rework_pct], ['Repeat QA queries', a.qa_repeat_pct], ['Batches with deviation', a.deviation_rate_pct], ['Off expected path', 100 - a.conformance_pct]], '%')}<p class="small muted">Hand-offs per batch: <b>${f1(a.handoffs_mean)}</b> (consecutive role changes).</p></div>
        <div class="card"><h3>Actions</h3><ol class="issues">${ops.slice(0, 4).map((o) => `<li><b>${esc(o.recommendation)}</b><br><span class="small muted">${esc(o.title)} · score ${f2(o.score)}</span></li>`).join('')}</ol></div></div>`;
    } else {
      const ob = D.open_batches.filter((o) => (state.site === 'all' || o.site === state.site) && (state.mat === 'all' || o.id.split('|')[1] === state.mat));
      const recent = cs.filter((c) => c.closed && c.rework && c.month >= lastMonths(1)[0]).slice(0, 12);
      lp.innerHTML = `<div class="grid g2"><div class="card"><h3>Needs attention today · open batches at data cut-off (${esc(D.meta.cutoff)})</h3><div class="tbl-wrap"><table><thead><tr><th>Batch</th><th>Site</th><th>Product</th><th class="num">Age</th><th class="num">Target</th><th>Last step</th><th>Risk</th></tr></thead><tbody>
        ${ob.map((o) => `<tr><td class="mono">${esc(o.batch)}</td><td>${SITE(o.site)}</td><td>${esc(o.product)}</td><td class="num">${f1(o.age_d)} d</td><td class="num">${f0(o.target_d)} d</td><td>${esc(o.last_step)}</td><td>${o.at_risk ? '<span class="pill bad">! at risk</span>' : '<span class="pill good">on track</span>'}${o.has_dev ? ' <span class="pill warn">deviation</span>' : ''}</td></tr>`).join('') || '<tr><td colspan="7" class="muted">No open batches in scope.</td></tr>'}</tbody></table></div><p class="small muted">At risk = age above 80% of the product target.</p></div>
        <div class="card"><h3>Repeat / rework cases · latest complete month</h3><div class="tbl-wrap"><table><thead><tr><th>Batch</th><th>Site</th><th class="num">Cycle</th><th>What repeated</th></tr></thead><tbody>
        ${recent.map((c) => `<tr><td class="mono">${esc(c.batch)}</td><td>${SITE(c.site)}</td><td class="num">${f1(c.cycle)} d</td><td class="small">${[c.docRw && 'batch record returned', c.qaRep && 'QA query', c.retest && 'retest lot', c.devReo && 'deviation reopened', c.udChg && 'UD changed'].filter(Boolean).join(', ')}</td></tr>`).join('') || '<tr><td colspan="4" class="muted">None.</td></tr>'}</tbody></table></div></div></div>`;
    }
  }
  function barRows(items, unit) {
    const mx = Math.max(...items.map((i) => i[1] || 0), 1e-9);
    return items.map(([k, v]) => `<div class="bar-row"><span>${esc(k)}</span><div class="bar-track"><div class="bar-fill" style="width:${(100 * (v || 0)) / mx}%"></div></div><span class="num">${unit === '%' ? f0(v) + '%' : f1(v) + ' d'}</span></div>`).join('');
  }

  // ---------------------------------------------------------------- tab 3: process explorer
  function variantStats(cs) {
    const c = cs.filter((x) => x.closed); const g = E.groupBy(c, (x) => x.variant); const out = [];
    g.forEach((v, k) => out.push({ k, n: v.length, cycle: E.mean(v.map((x) => x.cycle)), conf: v[0].conf }));
    return out.sort((a, b) => b.n - a.n);
  }
  function variantTable(vs, n) {
    return `<div class="tbl-wrap"><table><thead><tr><th>Variant</th><th class="num">Batches</th><th class="num">Mean cycle</th></tr></thead><tbody>${vs.map((v) => `<tr><td><div class="chips">${D.variants[v.k].map((a) => `<span class="chip ${D.expected_once.includes(ACT[a]) ? '' : 'x'}">${esc(ACT[a])}</span>`).join('')}</div>${v.conf ? '<span class="pill good">expected path</span>' : ''}</td><td class="num">${v.n} <span class="muted">(${f0((100 * v.n) / n)}%)</span></td><td class="num">${f1(v.cycle)} d</td></tr>`).join('')}</tbody></table></div>`;
  }
  const POS = { 'Manufacturing Executed': [1, 0], 'Goods Receipt': [1, 1], 'Deviation Raised': [3, 1], 'Inspection Lot Created': [0, 2], 'Batch Record Completed': [2, 2],
    'QC Results Recorded': [0, 3], 'Batch Record Review': [2, 3], 'Deviation Closed': [3, 3], 'Batch Record Returned': [2, 4.15], 'Deviation Reopened': [3, 4.15],
    'Batch Record Corrected': [2, 5.15], 'QA Disposition Review': [1, 6.2], 'QA Query Raised': [0, 6.2], 'Usage Decision': [1, 7.3] };
  const REWORK = new Set(['Batch Record Corrected>Batch Record Review', 'Batch Record Review>Batch Record Returned', 'QA Query Raised>QA Disposition Review',
    'QA Disposition Review>QA Query Raised', 'Deviation Closed>Deviation Reopened', 'Deviation Reopened>Deviation Closed', 'QC Results Recorded>Inspection Lot Created',
    'Usage Decision>Usage Decision', 'Batch Record Review>Batch Record Review', 'QA Disposition Review>QA Disposition Review']);
  function processMap(cs) {
    const edges = E.dfg(cs.filter((c) => c.closed), D.trans);
    const n = cs.filter((c) => c.closed).length;
    const W = 860, colW = 210, rowH = 78, nw = 172, nh = 40, x0 = 30, y0 = 16;
    const xy = (a) => { const [cx, cy] = POS[ACT[a]]; return [x0 + cx * colW, y0 + cy * rowH]; };
    const counts = {}; cs.filter((c) => c.closed).forEach((c) => new Set(D.variants[c.variant]).forEach((a) => { counts[a] = (counts[a] || 0) + 1; }));
    const shown = edges.filter((e) => e.count >= state.pmMin);
    const maxC = Math.max(...shown.map((e) => e.count), 1), maxW = Math.max(...shown.map((e) => e.median_wait_h), 1);
    const ramp = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b'];
    const col = (e) => (state.pmMode === 'wait' ? ramp[Math.min(6, Math.floor((e.median_wait_h / maxW) * 6.99))] : css('--muted'));
    const H = y0 + 7.3 * rowH + nh + 20;
    let s = `<svg class="pmap" viewBox="0 0 ${W} ${H}" role="img" aria-label="Process map"><defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${css('--ink-2')}"/></marker><marker id="arr-r" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${css('--s8')}"/></marker></defs>`;
    const lab = [];
    shown.sort((a, b) => a.count - b.count).forEach((e) => {
      const [ax, ay] = xy(e.from), [bx, by] = xy(e.to);
      const back = REWORK.has(ACT[e.from] + '>' + ACT[e.to]);
      const side = back || (by < ay - 1);
      const w = 1 + 6 * Math.sqrt(e.count / maxC);
      const sx = ax + nw / 2, sy = ay + nh, tx = bx + nw / 2, ty = by;
      let d, lx, ly;
      if (side) { const ox = Math.max(ax, bx) + nw + 18; d = `M${ax + nw},${ay + nh / 2} C${ox},${ay + nh / 2} ${ox},${by + nh / 2} ${bx + nw},${by + nh / 2}`; lx = ox - 4; ly = (ay + by) / 2 + nh / 2; }
      else if (Math.abs(by - ay) < 1) { d = `M${ax + nw},${ay + nh / 2} L${bx},${by + nh / 2}`; if (bx < ax) d = `M${ax},${ay + nh / 2} L${bx + nw},${by + nh / 2}`; lx = (ax + bx + nw) / 2; ly = ay + nh / 2 - 6; }
      else { const my = (sy + ty) / 2; d = `M${sx},${sy} C${sx},${my} ${tx},${my} ${tx},${ty}`; lx = (sx + tx) / 2; ly = my; }
      const stroke = back ? css('--s8') : col(e);
      s += `<path d="${d}" fill="none" stroke="${stroke}" stroke-width="${w.toFixed(1)}" stroke-opacity="${back ? 0.9 : 0.75}" ${back ? 'stroke-dasharray="5 4"' : ''} marker-end="url(#${back ? 'arr-r' : 'arr'})" data-tip="${esc(ACT[e.from])} → ${esc(ACT[e.to])}<br>${e.count} batches (${f0((100 * e.count) / n)}%) · median wait ${f1(e.median_wait_h / 24)} d"/>`;
      if (e.count >= maxC * 0.12 || back) lab.push(`<text class="elabel" x="${lx}" y="${ly}" text-anchor="middle">${state.pmMode === 'wait' ? f1(e.median_wait_h / 24) + ' d' : e.count}</text>`);
    });
    s += lab.join('');
    ACT.forEach((a, i) => {
      if (!counts[i]) return;
      const [x, y] = xy(i); const rc = SERIES()[ROLE_LIST.indexOf(ROLES[i]) % 8];
      s += `<g class="node ${D.expected_once.includes(a) ? 'exp' : ''}" data-tip="${esc(a)}<br>role: ${esc(ROLES[i])}<br>${counts[i]} of ${n} batches"><rect x="${x}" y="${y}" width="${nw}" height="${nh}" rx="8" stroke-width="${D.expected_once.includes(a) ? 1.6 : 1}" ${D.expected_once.includes(a) ? '' : 'stroke-dasharray="4 3"'}/><rect x="${x}" y="${y}" width="5" height="${nh}" rx="2" fill="${rc}" stroke="none"/>
        <text class="nlabel" x="${x + 12}" y="${y + 17}">${esc(a)}</text><text class="ncount" x="${x + 12}" y="${y + 32}">${counts[i]} batches · ${f0((100 * counts[i]) / n)}%</text></g>`;
    });
    return s + '</svg>';
  }
  function renderExplorer() {
    const cs = scope(), c = cs.filter((x) => x.closed), n = c.length;
    const vs = variantStats(cs);
    const edges = E.dfg(c, D.trans).filter((e) => e.count >= 20).sort((a, b) => b.median_wait_h - a.median_wait_h).slice(0, 6);
    const a = E.agg(cs);
    const issues = {}; c.forEach((x) => (x.issues || '').split('; ').filter(Boolean).forEach((i) => { issues[i] = (issues[i] || 0) + 1; }));
    const dq = D.dq.rules;
    const p = $('#p-explorer');
    p.innerHTML = `<h2>Process explorer</h2><p class="lead">Actual process reconstructed from ${D.meta.n_events.toLocaleString()} events (${esc(scopeLabel())}). Solid nodes = expected path, dashed = exception activities, red dashed arrows = backward movement (rework loops).</p>
      <div class="grid g32"><div class="card"><h3>Process map <span class="seg-ctl" id="pm-mode"><button data-m="freq" class="${state.pmMode === 'freq' ? 'on' : ''}">Frequency</button><button data-m="wait" class="${state.pmMode === 'wait' ? 'on' : ''}">Median waiting</button></span>
        <label class="small muted" style="margin-left:auto">hide edges below <input type="range" id="pm-min" min="1" max="60" value="${state.pmMin}" style="vertical-align:middle"> <b id="pm-min-v">${state.pmMin}</b> batches</label></h3>
        <div class="legend">${ROLE_LIST.map((r, i) => `<span><span class="dot" style="background:${SERIES()[i % 8]}"></span>${esc(r)}</span>`).join('')}</div>
        <div class="pmap-wrap" id="pmap">${processMap(cs)}</div></div>
        <div class="grid" style="align-content:start"><div class="card"><h3>Expected vs actual</h3><div class="tile"><div class="v">${f0(a.conformance_pct)}<small>% follow the expected path</small></div></div>
          <p class="small muted">Expected: each of ${D.expected_once.length} core steps exactly once (QC and documentation in parallel), no exception activity. Checked with declarative rules, not one fixed sequence.</p>
          ${barRows(Object.entries(issues).sort((x, y) => y[1] - x[1]).slice(0, 7).map(([k, v]) => [k, (100 * v) / n]), '%')}</div>
          <div class="card"><h3>Bottleneck transitions</h3><p class="sub">Largest median wait between consecutive activities (≥ 20 batches)</p><table><thead><tr><th>From → to</th><th class="num">Batches</th><th class="num">Median wait</th></tr></thead><tbody>${edges.map((e) => `<tr><td class="small">${esc(ACT[e.from])} → ${esc(ACT[e.to])}</td><td class="num">${e.count}</td><td class="num">${f1(e.median_wait_h / 24)} d</td></tr>`).join('')}</tbody></table></div></div></div>
      <div class="grid g2" style="margin-top:14px"><div class="card"><h3>Variants · ${vs.length} distinct in scope</h3><p class="sub">Red chips = activities outside the expected path</p>${variantTable(vs.slice(0, 8), n)}</div>
        <div class="card"><h3>Loops &amp; repeated activities</h3>${barRows([['Batch record returned and re-reviewed', a.doc_rework_pct], ['Returned twice or more', E.pct(c.map((x) => x.docLoops >= 2))], ['Repeated QA review (query)', a.qa_repeat_pct], ['Second inspection lot (retest)', E.pct(c.map((x) => x.retest))], ['Deviation reopened', E.pct(c.map((x) => x.devReo))], ['Usage decision changed', E.pct(c.map((x) => x.udChg))]], '%')}
          <h3 style="margin-top:14px">Hand-offs</h3><p class="small">Mean <b>${f1(a.handoffs_mean)}</b> role changes per batch (fast quartile ${f1(E.fastSlow(cs).fast.handoffs_mean)}, slow quartile ${f1(E.fastSlow(cs).slow.handoffs_mean)}).</p></div></div>
      <div class="grid g2" style="margin-top:14px"><div class="card"><h3>Event log · one batch down to the source transaction</h3><p class="sub">case_id = plant | material | batch. start_source shows how each start time was established.</p><div class="tbl-wrap"><table><thead><tr><th>Activity</th><th>Start</th><th>End</th><th>Role</th><th>Source</th><th>Key</th><th>Start from</th></tr></thead><tbody>
        ${D.sample_events.map((e) => `<tr><td>${esc(e.activity)}</td><td class="mono">${esc(e.ts_start)}</td><td class="mono">${esc(e.ts_end)}</td><td class="small">${esc(e.role)}</td><td class="small">${esc(e.source_table)}</td><td class="mono">${esc(e.source_key)}</td><td class="small">${esc(e.start_source)}${e.inherited_from ? ' · inherited' : ''}</td></tr>`).join('')}</tbody></table></div><p class="small muted mono">${esc(D.sample_events[0] ? D.sample_events[0].case_id : '')}</p></div>
        <div class="card"><h3>Data-quality report (full extract)</h3><table><tbody>
          <tr><td>Start times (R1)</td><td class="small">${Object.entries(dq.R1_start_times).map(([k, v]) => `${esc(k)}: ${v.explicit} explicit, ${v.status_log} from status log, ${v.none} none → <b>${f1(v.coverage_pct)}%</b>`).join('<br>')}<br><span class="muted">No start → "elapsed, unsplit": excluded from the processing/waiting split; coverage is shown per KPI.</span></td></tr>
          <tr><td>Duplicates (R2)</td><td class="small">${dq.R2_duplicates_collapsed.total} collapsed on (case, activity, timestamp, source key): ${Object.entries(dq.R2_duplicates_collapsed.by_source).map(([k, v]) => esc(k) + ' ' + v).join(', ')}</td></tr>
          <tr><td>Re-sends (R3)</td><td class="small">${dq.R3_suspected_resends.count} same activity + same timestamp + new key → suspected re-send, kept out of rework. Same activity with a new key and new time = repeat / rework candidate.</td></tr>
          <tr><td>Splits / merges (R4)</td><td class="small">${dq.R4_lineage.splits} split and ${dq.R4_lineage.merges} merge links; children inherit ${dq.R4_lineage.inherited_events} upstream manufacturing events; ${dq.R4_lineage.lineage_parents_excluded_from_release_kpis} parent batches are not release cases.</td></tr>
          <tr><td>ID crosswalk (R5)</td><td class="small">${dq.R5_crosswalk.distinct_source_ids} MES/QMS batch IDs: ${dq.R5_crosswalk.by_method.map((m) => `${esc(m.source_system)} ${esc(m.method)}: ${m.ids}`).join('; ')}. Included at confidence ≥ ${dq.R5_crosswalk.included_min_conf}; ${dq.R5_crosswalk.rows_excluded.MES} MES + ${dq.R5_crosswalk.rows_excluded.QMS} QMS rows excluded and listed.</td></tr>
          <tr><td>Start after end (R6)</td><td class="small">${dq.R6_start_after_end_dropped} starts dropped</td></tr></tbody></table></div></div>`;
    p.querySelectorAll('#pm-mode button').forEach((b) => b.addEventListener('click', () => { state.pmMode = b.dataset.m; renderExplorer(); }));
    $('#pm-min').addEventListener('input', (e) => { state.pmMin = +e.target.value; $('#pm-min-v').textContent = state.pmMin; $('#pmap').innerHTML = processMap(scope()); });
  }

  // ---------------------------------------------------------------- tab 4: KPI & benchmark drilldown
  const SEG_TRANS = {
    'Documentation (incl. rework) binding': [['Batch Record Completed', 'Batch Record Review'], ['Batch Record Review', 'Batch Record Returned'], ['Batch Record Returned', 'Batch Record Corrected'], ['Batch Record Corrected', 'Batch Record Review']],
    'QC results binding': [['Inspection Lot Created', 'QC Results Recorded'], ['QC Results Recorded', 'Inspection Lot Created']],
    'Deviation closure binding': [['Deviation Raised', 'Deviation Closed'], ['Deviation Closed', 'Deviation Reopened'], ['Deviation Reopened', 'Deviation Closed']],
    'QA queue + disposition review': [['Batch Record Review', 'QA Disposition Review'], ['QC Results Recorded', 'QA Disposition Review'], ['Deviation Closed', 'QA Disposition Review'], ['QA Disposition Review', 'QA Query Raised'], ['QA Query Raised', 'QA Disposition Review']],
    'Usage-decision approval wait': [['QA Disposition Review', 'Usage Decision']],
  };
  function sparkline(vals, color) {
    const v = vals.map((x) => x.v); const ok = v.filter(isNum); if (ok.length < 2) return '';
    const mn = Math.min(...ok), mx = Math.max(...ok), w = 90, h = 24;
    const pts = v.map((x, i) => (isNum(x) ? `${((i / (v.length - 1)) * w).toFixed(1)},${(h - 2 - ((x - mn) / (mx - mn || 1)) * (h - 4)).toFixed(1)}` : null)).filter(Boolean);
    return `<svg width="${w}" height="${h}" aria-hidden="true"><polyline points="${pts.join(' ')}" fill="none" stroke="${color}" stroke-width="1.6"/></svg>`;
  }
  function renderKpi() {
    const cs = scope(); const rows = benchRows(cs);
    const p = $('#p-kpi');
    p.innerHTML = `<h2>KPI &amp; benchmark analysis</h2><p class="lead">Every KPI: actual · target · internal best (best site-quarter in the same product/period scope) · gap · trend. Click a KPI to drill down from outcome to process to activity.</p>
      <div class="card"><div class="tbl-wrap"><table><thead><tr><th>KPI</th><th class="num">Actual</th><th class="num">Target</th><th class="num">Internal best</th><th class="num">Gap to target</th><th class="num">Trend</th><th>Monthly</th><th class="num">Data coverage</th></tr></thead><tbody>
      ${rows.map((r) => `<tr class="click ${state.kpi === r.key ? 'sel' : ''}" data-k="${r.key}"><td class="kpi-name">${esc(r.label)}</td><td class="num">${unitFmt(r.value, r.unit)}</td><td class="num">${unitFmt(r.target, r.unit)}</td><td class="num">${r.best ? unitFmt(r.best[0], r.unit) + ' <span class="muted small">' + esc(r.best[1]) + '</span>' : '–'}</td><td class="num ${r.bad ? 'trend-up' : 'trend-down'}">${gapFmt(r.gap, r.unit)}</td><td class="num">${trendCell(r.key, cs, r.lower)}</td><td>${sparkline(monthly(cs.filter((c) => c.month <= COMPLETE), (x) => E.agg(x)[r.key]), css('--accent'))}</td><td class="num">${f0(r.cov)}%</td></tr>`).join('')}
      </tbody></table></div><p class="small muted">External benchmarks (e.g. APQC Open Standards Benchmarking) need licensed data and are not included; the internal best is a real, achievable reference from the same data.</p></div>
      <div class="grid g2" style="margin-top:14px"><div class="card"><h3 id="dd-title"></h3><div id="c-kpi" class="chart"></div></div><div class="card"><h3>Outcome → process → activity</h3><div id="tree"></div></div></div>`;
    p.querySelectorAll('tr.click').forEach((tr) => tr.addEventListener('click', () => { state.kpi = tr.dataset.k; renderKpi(); }));
    const sel = rows.find((r) => r.key === state.kpi) || rows[0];
    $('#dd-title').textContent = sel.label + ' · monthly by site';
    trendChart('c-kpi', cs, sel.key, sel.unit === '%' ? '%' : sel.unit === 'd' ? 'days' : '', sel.key === 'cycle_mean_d');
    const d = E.decompose(cs), edges = E.dfg(cs.filter((c) => c.closed), D.trans);
    const ed = (a, b) => edges.find((e) => ACT[e.from] === a && ACT[e.to] === b);
    $('#tree').innerHTML = `<div class="callout"><b>Release cycle time ${f1(d._cycle_mean_d)} d</b> (outcome KPI, n = ${d._n})</div>` + E.SEGS.map(([k]) => {
      const tr = SEG_TRANS[k].map(([a, b]) => [a, b, ed(a, b)]).filter((x) => x[2]);
      return `<div style="margin:8px 0 8px 14px"><div class="bar-row"><span><b>${esc(k.replace(' binding', ''))}</b></span><div class="bar-track"><div class="bar-fill" style="width:${(100 * (d[k] || 0)) / (d._cycle_mean_d || 1)}%"></div></div><span class="num">${f1(d[k])} d</span></div>
        <div style="margin-left:18px" class="small">${tr.map(([a, b, e]) => `↳ ${esc(a)} → ${esc(b)}: ${e.count} batches, median wait ${f1(e.median_wait_h / 24)} d`).join('<br>')}</div></div>`;
    }).join('') + '<p class="small muted">Process KPI = mean days per batch on the critical path. Activity level = directly-follows transitions with their median waits.</p>';
  }

  // ---------------------------------------------------------------- tab 5: quality intelligence
  function renderQuality() {
    const cs = scope(), c = cs.filter((x) => x.closed), ids = new Set(cs.map((x) => x.id));
    const fs = E.fastSlow(cs), fa = E.facts(cs);
    const devs = D.deviations.filter((d) => ids.has(d[0]));
    const cats = [...new Set(D.deviations.map((d) => d[1]))].sort();
    const p = $('#p-quality');
    const fact = (t, ev) => `<div class="callout"><span class="pill fact">fact</span> ${t}<div class="small muted">evidence: ${ev}</div></div>`;
    const hyp = (t, test) => `<div class="callout hyp"><span class="pill hyp">hypothesis</span> ${t}<div class="small muted">how to test: ${test}</div></div>`;
    const bind = {}; c.forEach((x) => { bind[x.binding] = (bind[x.binding] || 0) + 1; });
    p.innerHTML = `<h2>Quality intelligence</h2><p class="lead">Associations between release performance and quality events. Facts are measured; hypotheses are labelled and come with a test. ${esc(scopeLabel())}</p>
      <div class="grid g2"><div class="card"><h3>What the data says</h3>
        ${fact(`${f0(fa.late5_with_dev_pct)}% of batches released more than 5 days over target had a deviation, vs ${f0(fa.ontime_with_dev_pct)}% of batches released on time.`, `${fa.n_late5} vs ${fa.n_ontime} closed batches; SELECT has_dev FROM cases WHERE cycle_d &gt; target_d + 5`)}
        ${fact(`${f0(fs.slow.doc_loops2_pct)}% of slow-release batches went through two or more extra documentation-review cycles (fast: ${f0(fs.fast.doc_loops2_pct)}%).`, `slowest quartile n = ${fs.slow.n} (cycle ≥ ${f2(fs.slow_min_ratio)} × target)`)}
        ${fact(`The binding constraint (last path to finish before QA review) is QC results for ${f0((100 * (bind['QC results'] || 0)) / c.length)}%, documentation for ${f0((100 * (bind['Documentation'] || 0)) / c.length)}% and deviation closure for ${f0((100 * (bind['Deviation closure'] || 0)) / c.length)}% of batches.`, `${c.length} closed batches, critical-path decomposition`)}
        ${hyp('Deviation-resolution latency appears to be a major contributor to release delay.', 'compare cycle time of deviation batches by category and resolution time; exclude exceptional events; check whether triage-at-completion shortens closure (intervention record).')}
        ${hyp('QA queueing, not QA review effort, drives the QA stage.', `review effort is ${f2(E.mean(c.map((x) => x.qaRev)))} d vs waiting ${f1(E.agg(cs).qa_wait_mean_d)} d per batch; test with a pilot of review-ready triggers.`)}</div>
        <div class="card"><h3>Fast vs slow batches</h3><p class="sub">Quartiles of cycle time relative to the product target (removes product-mix effects)</p><table><thead><tr><th>Profile</th><th class="num">Fast</th><th class="num">Slow</th></tr></thead><tbody>
          ${[['Batches', fs.fast.n, fs.slow.n, 0, ''], ['Mean cycle', fs.fast.cycle_mean_d, fs.slow.cycle_mean_d, 1, ' d'], ['With deviation', fs.fast.deviation_pct, fs.slow.deviation_pct, 0, '%'], ['Documentation rework', fs.fast.doc_rework_pct, fs.slow.doc_rework_pct, 0, '%'], ['Repeat QA query', fs.fast.qa_repeat_pct, fs.slow.qa_repeat_pct, 0, '%'], ['Retest', fs.fast.retest_pct, fs.slow.retest_pct, 0, '%'], ['Mean QA waiting', fs.fast.qa_wait_mean_d, fs.slow.qa_wait_mean_d, 1, ' d'], ['Hand-offs', fs.fast.handoffs_mean, fs.slow.handoffs_mean, 1, ''], ['Expected path', fs.fast.conformance_pct, fs.slow.conformance_pct, 0, '%'], ['Share from Site A', fs.fast.site_a_share_pct, fs.slow.site_a_share_pct, 0, '%']].map(([k, a, b, d, u]) => `<tr><td>${k}</td><td class="num">${isNum(a) ? a.toFixed(d) + u : '–'}</td><td class="num">${isNum(b) ? b.toFixed(d) + u : '–'}</td></tr>`).join('')}</tbody></table></div></div>
      <div class="grid g2" style="margin-top:14px"><div class="card"><h3>Deviation patterns · count by category and site</h3><div id="c-dev" class="chart"></div></div>
        <div class="card"><h3>Deviation resolution time by category</h3><div id="c-devres" class="chart"></div></div></div>
      <div class="grid g2" style="margin-top:14px"><div class="card"><h3>Site / product differences</h3><div class="tbl-wrap"><table><thead><tr><th>Product</th><th>Site</th><th class="num">n</th><th class="num">Cycle</th><th class="num">Target</th><th class="num">On time</th><th class="num">RFT</th></tr></thead><tbody>
        ${Object.keys(D.products).flatMap((m) => Object.keys(D.sites).map((s) => { const x = cs.filter((y) => y.mat === m && y.site === s); if (!x.length) return ''; const a = E.agg(x); return `<tr><td>${esc(D.products[m].name)}</td><td>${SITE(s)}</td><td class="num">${a.n_closed}</td><td class="num">${f1(a.cycle_mean_d)} d</td><td class="num">${f0(D.products[m].target_days)} d</td><td class="num">${f0(a.ontime_pct)}%</td><td class="num">${f0(a.rft_pct)}%</td></tr>`; })).join('')}</tbody></table></div></div>
        <div class="card"><h3>Rework patterns</h3>${barRows([['Documentation returned', E.pct(c.map((x) => x.docRw))], ['QA query', E.pct(c.map((x) => x.qaRep))], ['Retest (2nd inspection lot)', E.pct(c.map((x) => x.retest))], ['Deviation reopened', E.pct(c.map((x) => x.devReo))], ['Usage decision changed', E.pct(c.map((x) => x.udChg))]], '%')}<p class="small muted">Deviations with CAPA required: ${devs.filter((d) => d[3]).length} of ${devs.length}. Linked to exceptional events: ${devs.filter((d) => d[4]).length}.</p></div></div>`;
    const sites = state.site === 'all' ? Object.keys(D.sites) : [state.site];
    chart('c-dev', { xAxis: { type: 'value' }, yAxis: { type: 'category', data: cats }, grid: { left: 10, right: 16, top: 30, bottom: 10, containLabel: true },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      series: sites.map((s) => ({ name: SITE(s), type: 'bar', stack: 'a', itemStyle: { color: SITE_COLOR(s), borderColor: css('--surface'), borderWidth: 1 }, data: cats.map((k) => devs.filter((d) => d[1] === k && d[0].startsWith(s)).length) })) });
    chart('c-devres', { xAxis: { type: 'value', name: 'days (mean)' }, yAxis: { type: 'category', data: cats }, grid: { left: 10, right: 16, top: 30, bottom: 24, containLabel: true },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      series: sites.map((s) => ({ name: SITE(s), type: 'bar', itemStyle: { color: SITE_COLOR(s) }, data: cats.map((k) => { const v = E.mean(devs.filter((d) => d[1] === k && d[0].startsWith(s) && isNum(d[2])).map((d) => d[2])); return isNum(v) ? +v.toFixed(2) : null; }) })) });
  }

  // ---------------------------------------------------------------- tab 6: improvement & maturity
  const DIM_DRIVER = { performance: 'more batches within target', predictability: 'lower process variation', quality: 'improved right-first-time',
    standardization: 'more batches on the expected path', efficiency: 'reduced QA waiting / hand-offs', compliance: 'controls executed in order',
    improvement: 'sustained intervention benefits' };
  function renderImprove() {
    const cs = scope();
    const ms = MONTHS.filter((m) => m >= state.from && m <= COMPLETE);
    const A = ms.slice(0, 3), B = ms.slice(-3);
    const m0 = E.maturity(cs.filter((c) => A.includes(c.month)), D.maturity_dims, D.ci_sustained);
    const m1 = E.maturity(cs.filter((c) => B.includes(c.month)), D.maturity_dims, D.ci_sustained);
    const p = $('#p-improve');
    const iv = D.interventions[0];
    const ops = E.opportunities(cs, CASES, D.effort);
    const pre = [addDays(state.ivDate, -state.ivDays), addDays(state.ivDate, -1)], post = [state.ivDate, addDays(state.ivDate, state.ivDays - 1)];
    const pp = E.prePost(CASES, state.ivSite, pre, post, { excludeExc: state.ivExc, mat: state.mat });
    const k = Object.fromEntries(pp.map((r) => [r.kpi, r]));
    let ch = '';
    if (m0 && m1) {
      const deltas = D.maturity_dims.map((d) => [d, m1.contrib[d.key] - m0.contrib[d.key]]).sort((x, y) => Math.abs(y[1]) - Math.abs(x[1]));
      ch = `<div class="health"><div><div class="muted small">${A[0]} – ${A[A.length - 1]}</div><div style="font-size:34px;font-weight:700">${f0(m0.score)}</div></div><div style="font-size:24px">→</div><div><div class="muted small">${B[0]} – ${B[B.length - 1]}</div><div style="font-size:34px;font-weight:700">${f0(m1.score)}</div></div></div>
        <div class="contrib" style="margin-top:10px">${deltas.map(([d, v]) => `<span>from ${esc(DIM_DRIVER[d.key])} <span class="muted small">(${esc(d.label)})</span></span><span class="${v >= 0 ? 'pos' : 'neg'}">${sgn(v)}</span>`).join('')}<span><b>Total change</b></span><span><b>${sgn(m1.score - m0.score)}</b></span></div>`;
    }
    p.innerHTML = `<h2>Improvement &amp; maturity tracker</h2><p class="lead">Measure → diagnose → intervene → measure again. The maturity score is a weighted sum of named dimensions; every point of change is attributed to a dimension and its KPI. No unexplained score.</p>
      <div class="grid g2"><div class="card"><h3>Maturity change, explained</h3>${ch || '<p class="muted">Need at least 4 complete months in scope.</p>'}</div>
        <div class="card"><h3>Maturity trend (monthly)</h3><div id="c-mat" class="chart short"></div><div id="c-wf" class="chart short"></div></div></div>
      <div class="card" style="margin-top:14px"><h3>Dimensions and rules</h3><div class="tbl-wrap"><table><thead><tr><th>Dimension</th><th class="num">Weight</th><th>Score rule (0-100)</th><th class="num">${A[0] || ''}…</th><th class="num">…${B[B.length - 1] || ''}</th></tr></thead><tbody>
        ${D.maturity_dims.map((d) => `<tr><td><b>${esc(d.label)}</b></td><td class="num">${f0(100 * d.weight)}%</td><td class="small">${esc(d.rule)}</td><td class="num">${m0 ? f0(m0.dims[d.key]) : '–'}</td><td class="num">${m1 ? f0(m1.dims[d.key]) : '–'}</td></tr>`).join('')}</tbody></table></div></div>
      <div class="card" style="margin-top:14px"><h3>Improvement tracker</h3><div class="tbl-wrap"><table><thead><tr><th>Opportunity</th><th>Recommendation</th><th>Owner</th><th>Intervention</th><th>Before → after</th><th>Benefit</th><th>Status</th></tr></thead><tbody>
        <tr><td>Batch record documentation rework (Site A)</td><td>${esc(iv.title)}</td><td class="small">${esc(iv.owner)}</td><td class="mono">${esc(iv.id)} · ${esc(iv.date)}</td><td class="small">${(() => { const r = D.intervention_result.kpis; return r.map((x) => `${esc(x.label)}: ${x.kind === 'rate' ? f1(x.pre) + '% → ' + f1(x.post) + '%' : f1(x.pre) + ' → ' + f1(x.post) + ' d'}`).join('<br>'); })()}</td><td class="small">${(() => { const x = D.intervention_result.kpis[0]; return `${f1(x.change)} pts rework (p ${fp(x.p_value)})`; })()}</td><td>${D.intervention_result.sustained ? '<span class="pill good">✓ implemented · sustained</span>' : '<span class="pill warn">implemented · not yet sustained</span>'}</td></tr>
        ${ops.slice(0, 3).map((o) => `<tr><td>${esc(o.title)}</td><td class="small">${esc(o.recommendation)}</td><td class="small muted">to assign</td><td class="muted">–</td><td class="small">${f1(o.current_d)} d → ${f1(o.internal_best_d)} d (internal best)</td><td class="small">up to ${f2(o.impact_d * o.frequency)} d per batch on average</td><td><span class="pill">proposed</span></td></tr>`).join('')}
      </tbody></table></div></div>
      <div class="card" style="margin-top:14px"><h3>"We implemented something. Did it work?"</h3>
        <div class="filters" style="margin-bottom:10px"><label>Site<select id="iv-site">${Object.keys(D.sites).map((s) => `<option value="${s}" ${s === state.ivSite ? 'selected' : ''}>${SITE(s)}</option>`).join('')}</select></label>
          <label>Intervention date<input type="date" id="iv-date" value="${state.ivDate}" min="2026-02-01" max="2026-08-31"></label>
          <label>Window (days each side)<select id="iv-days">${[42, 61, 92, 120].map((d) => `<option ${d === state.ivDays ? 'selected' : ''}>${d}</option>`).join('')}</select></label>
          <label class="chk"><input type="checkbox" id="iv-exc" ${state.ivExc ? 'checked' : ''}> exclude exceptional events</label></div>
        <p class="small muted">Recorded: <b>${esc(iv.id)}</b> ${esc(iv.title)} at ${SITE(iv.site)} on ${esc(iv.date)}. Change the date to test any other change point. Windows by manufacturing-completion date: ${pre[0]} … ${pre[1]} vs ${post[0]} … ${post[1]}${post[1] > '2026-08-31' ? ' <span class="pill warn">post window reaches into provisional months</span>' : ''}.</p>
        <div class="tbl-wrap"><table><thead><tr><th>KPI</th><th class="num">Before</th><th class="num">After</th><th class="num">Change</th><th class="num">95% CI (bootstrap)</th><th>Test</th><th class="num">p</th><th class="num">Other site change</th><th class="num">Diff-in-diff</th><th></th></tr></thead><tbody>
          ${pp.map((r) => isNum(r.pre) ? `<tr><td class="kpi-name">${esc(r.label)}</td><td class="num">${r.kind === 'rate' ? f1(r.pre) + '%' : f1(r.pre) + ' d'}</td><td class="num">${r.kind === 'rate' ? f1(r.post) + '%' : f1(r.post) + ' d'}</td><td class="num">${sgn(r.change)}${r.kind === 'rate' ? ' pts' : ' d'} <span class="muted small">(${sgn(r.change_pct, 0)}%)</span></td><td class="num">${f1(r.ci95[0])} … ${f1(r.ci95[1])}</td><td class="small">${esc(r.test)}${r.kind === 'cont' ? ' · medians' : ''}</td><td class="num">${fp(r.p_value)}</td><td class="num">${sgn(r.comparison_site_change)}</td><td class="num">${sgn(r.did_means)}</td><td>${r.significant ? '<span class="pill good">significant</span>' : '<span class="pill">not significant</span>'}</td></tr>` : `<tr><td>${esc(r.label)}</td><td colspan="9" class="muted">not enough batches</td></tr>`).join('')}</tbody></table></div>
        <div class="grid g2" style="margin-top:10px"><div>${k.docRw && isNum(k.docRw.pre) ? `<div class="callout"><span class="pill fact">fact</span> Documentation rework ${f1(k.docRw.pre)}% → ${f1(k.docRw.post)}% (${sgn(k.docRw.change)} pts, Fisher p ${fp(k.docRw.p_value)}, n = ${k.docRw.n_pre} / ${k.docRw.n_post}); the other site moved ${sgn(k.docRw.comparison_site_change)} pts over the same windows.</div>
          <div class="callout hyp"><span class="pill hyp">hypothesis</span> The change caused the reduction. Rule out concurrent changes (staffing, SOP revisions, product mix) before attributing the benefit; the comparison site controls for common seasonal effects only.</div>` : ''}
          <p class="small muted">Continuous KPIs: Mann-Whitney U on medians (robust to the long right tail of cycle times); rates: Fisher exact. CIs: 1,000 bootstrap resamples. The Python engine uses the same tests (2,000 resamples) for the recorded intervention.</p></div>
          <div id="c-iv" class="chart short"></div></div></div>`;
    ['iv-site', 'iv-date', 'iv-days', 'iv-exc'].forEach((id) => $('#' + id).addEventListener('change', (e) => {
      if (id === 'iv-site') state.ivSite = e.target.value; if (id === 'iv-date' && e.target.value) state.ivDate = e.target.value;
      if (id === 'iv-days') state.ivDays = +e.target.value; if (id === 'iv-exc') state.ivExc = e.target.checked; renderImprove();
    }));
    const msAll = MONTHS.filter((m) => m >= state.from && m <= state.to);
    const sites = state.site === 'all' ? Object.keys(D.sites) : [state.site];
    chart('c-mat', { xAxis: { type: 'category', data: msAll }, yAxis: { type: 'value', min: 30, max: 90, name: 'score' },
      series: sites.map((s) => ({ name: SITE(s), type: 'line', symbolSize: 7, itemStyle: { color: SITE_COLOR(s) }, lineStyle: { width: 2 },
        data: msAll.map((m) => { const r = E.maturity(cs.filter((c) => c.site === s && c.month === m), D.maturity_dims, D.ci_sustained); return r && r.n >= 8 ? +r.score.toFixed(1) : null; }) })) });
    if (m0 && m1) {
      const steps = D.maturity_dims.map((d) => [d.label, m1.contrib[d.key] - m0.contrib[d.key]]);
      let run = m0.score; const base = [], pos = [], neg = [];
      steps.forEach(([, v]) => { base.push(+(v >= 0 ? run : run + v).toFixed(2)); pos.push(v >= 0 ? +v.toFixed(2) : 0); neg.push(v < 0 ? +(-v).toFixed(2) : 0); run += v; });
      chart('c-wf', { tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: (ps) => { const i = ps[0].dataIndex; return `${steps[i][0]}: <b>${sgn(steps[i][1], 2)}</b>`; } }, legend: { show: false },
        xAxis: { type: 'category', data: steps.map((s) => s[0].split(' ')[0]), axisLabel: { interval: 0, fontSize: 10 } }, yAxis: { type: 'value', min: Math.floor(Math.min(m0.score, m1.score) - 3) },
        series: [{ type: 'bar', stack: 'w', data: base, itemStyle: { color: 'transparent' } }, { name: 'gain', type: 'bar', stack: 'w', data: pos, itemStyle: { color: css('--good') } }, { name: 'loss', type: 'bar', stack: 'w', data: neg, itemStyle: { color: css('--crit') } }] });
    }
    const dmon = MONTHS.filter((m) => m <= COMPLETE);
    chart('c-iv', { xAxis: { type: 'category', data: dmon }, yAxis: { type: 'value', name: 'documentation rework %' },
      series: Object.keys(D.sites).map((s) => ({ name: SITE(s), type: 'line', symbolSize: 6, itemStyle: { color: SITE_COLOR(s) }, lineStyle: { width: s === state.ivSite ? 2.5 : 1.5 },
        data: dmon.map((m) => { const v = E.agg(CASES.filter((c) => c.site === s && c.month === m && (!state.ivExc || !c.exc))).doc_rework_pct; return isNum(v) ? +v.toFixed(1) : null; }),
        markLine: s === state.ivSite ? { symbol: 'none', label: { formatter: 'intervention', color: css('--muted') }, lineStyle: { color: css('--ink-2'), type: 'dashed' }, data: [{ xAxis: state.ivDate.slice(0, 7) }] } : undefined })) });
  }
  function addDays(d, n) { const t = new Date(d + 'T00:00:00Z'); t.setUTCDate(t.getUTCDate() + n); return t.toISOString().slice(0, 10); }

  // ---------------------------------------------------------------- tab 7: copilot (scripted transcript + tools)
  const TYPE_PILL = { fact: ['fact', 'Fact'], hypothesis: ['hyp', 'Hypothesis'], framework: ['fw', 'Framework reference'], inference: ['inf', 'System inference'], unsupported: ['uns', 'Not supported'] };
  function answerHtml(statements, calls, grounded) {
    return `<div class="ans">${statements.map((s) => `<p><span class="pill ${TYPE_PILL[s.type][0]}">${TYPE_PILL[s.type][1]}</span>${esc(s.text)}</p>`).join('')}
      ${calls && calls.length ? `<details class="trace"><summary>Trace: ${calls.length} tool call${calls.length > 1 ? 's' : ''} · ${calls.map((c) => esc(c.tool) + ' (' + c.rows + ' rows)').join(', ')}${grounded === undefined ? '' : grounded ? ' · <span class="pill good">✓ all numbers grounded</span>' : ' · <span class="pill bad">ungrounded number</span>'}</summary>
        ${calls.map((c) => `<pre>${esc(c.tool)}(${esc(JSON.stringify(c.args))})\nquery: ${esc(c.query)}\nrows: ${c.rows}\nresult: ${esc(JSON.stringify(c.result, (k, v) => (typeof v === 'number' ? +v.toFixed(3) : v)).slice(0, 1500))}</pre>`).join('')}</details>` : ''}</div>`;
  }
  function renderCopilot() {
    const p = $('#p-copilot');
    p.innerHTML = `<h2>Copilot · traced answers</h2><p class="lead">This conversation was executed against the real tool layer (Python, spec Option C: no LLM). Each answer separates <span class="pill fact">fact</span> <span class="pill hyp">hypothesis</span> <span class="pill fw">framework reference</span> <span class="pill inf">system inference</span>, and its trace shows the tool, filters, SQL-equivalent query, row count and returned values. A checker verifies that every number in the answer appears in the tool results. The same tools can be exposed to an approved enterprise LLM endpoint (Option A) as function calls.</p>
      <div class="grid g32"><div>${D.transcript.map((t, i) => `<div class="card" style="margin-bottom:12px"><div class="msg q"><span>${esc(t.question)}</span></div>${answerHtml(t.answer, t.tool_calls, t.grounded)}<div class="small muted" style="margin-top:6px">intent: ${esc(t.intent)} · question ${i + 1} of ${D.transcript.length}</div></div>`).join('')}</div>
      <div><div class="card"><h3>Guardrails</h3><ul class="small"><li>KPIs, tests and scenarios are computed deterministically; the copilot only selects tools and phrases results.</li><li>Every quoted number must come from a tool result (checked).</li><li>Unsupported questions get "Not supported by the data".</li><li>Decision support only: never decides disposition, closes deviations, approves CAPA or writes to GxP records.</li></ul></div>
      <div class="card" style="margin-top:12px"><h3>Tool layer (JSON schemas)</h3>${D.tools.map((t) => `<details class="trace"><summary class="mono">${esc(t.name)}</summary><p class="small">${esc(t.description)}</p><pre>${esc(JSON.stringify(t.parameters, null, 1))}</pre></details>`).join('')}</div></div></div>`;
  }

  // ---------------------------------------------------------------- live copilot drawer (deterministic router over engine.js)
  const INTENTS = [
    ['unsupported_actor', /\b(operator|person|who|employee|name)\b/], ['unsupported_forecast', /\b(predict|forecast|next month|will be)\b/],
    ['intervention', /\b(intervention|pre-?check|did it work|working|implemented)\b/], ['exclude', /\b(exclude|without|except|exceptional)\b/],
    ['fast_slow', /\b(fast|slow)\b|differently/], ['compare_sites', /\bsite\b.*\b(slower|faster|best|compare|differ)\b|\b(slower|faster|best)\b.*\bsite\b|\bwhich site\b/],
    ['why', /\b(why|deteriorat|worse|drop|driver|cause)\b/], ['opportunities', /\b(improve|address first|issues|priorit|what next|what should)\b/],
    ['framework', /\b(gmp|annex|ich|q10|q9|apqc|framework)\b/], ['performance', /\b(perform|how is|how are|status|kpi|cycle)\b/],
  ];
  function liveAnswer(q) {
    const intent = (INTENTS.find(([, re]) => re.test(q.toLowerCase())) || ['unsupported'])[0];
    const f = F(), cs = scope(), rows = cs.filter((c) => c.closed).length;
    const call = (tool, args, result, n) => ({ tool, args, query: 'engine.' + tool + ' over cases WHERE ' + JSON.stringify(args), rows: n === undefined ? rows : n, result });
    if (intent.startsWith('unsupported') || intent === 'unsupported') {
      return { st: [{ type: 'unsupported', text: 'Not supported by the data. ' + (intent === 'unsupported_actor' ? 'The extract carries roles only; actors are anonymised.' : intent === 'unsupported_forecast' ? 'No validated forecasting model is part of this PoC.' : 'Try: performance, why, compare sites, exclude exceptional events, intervention, fast vs slow, what to improve, GMP.') }], calls: [] };
    }
    if (intent === 'performance') {
      const a = E.agg(cs);
      return { st: [{ type: 'fact', text: `In scope (${scopeLabel()}): ${a.n_closed} released batches, mean release cycle ${f1(a.cycle_mean_d)} d vs target ${f1(a.target_mean_d)} d, ${f0(a.ontime_pct)}% within target, right first time ${f0(a.rft_pct)}%, QA waiting ${f1(a.qa_wait_mean_d)} d (coverage ${f0(a.qa_wait_coverage_pct)}%).` }], calls: [call('agg', f, a)] };
    }
    if (intent === 'why') {
      const d = E.decompose(cs); const best = E.decompose(E.filter(CASES, Object.assign({}, f, { site: 'all' })));
      const segs = E.SEGS.map(([k]) => [k, d[k]]).sort((x, y) => y[1] - x[1]);
      return { st: [{ type: 'fact', text: `Mean cycle ${f1(d._cycle_mean_d)} d splits into ${segs.map(([k, v]) => `${k.replace(' binding', '')} ${f1(v)} d`).join(', ')}.` },
        { type: 'inference', text: `Largest driver in this scope: ${segs[0][0].replace(' binding', '')}. Open the KPI drilldown to see the activity-level waits.` }], calls: [call('decompose', f, d, d._n)] };
    }
    if (intent === 'compare_sites') {
      const res = Object.keys(D.sites).map((s) => [s, E.agg(E.filter(CASES, Object.assign({}, f, { site: s })))]);
      return { st: [{ type: 'fact', text: res.map(([s, a]) => `${SITE(s)}: cycle ${f1(a.cycle_mean_d)} d vs target ${f1(a.target_mean_d)} d (gap ${sgn(a.cycle_mean_d - a.target_mean_d)} d), RFT ${f0(a.rft_pct)}%, QA waiting ${f1(a.qa_wait_mean_d)} d`).join('; ') + '.' },
        { type: 'inference', text: 'Gap to the product-weighted target removes most of the product-mix effect; the Site / process owner view shows the like-for-like comparison.' }], calls: res.map(([s, a]) => call('agg', Object.assign({}, f, { site: s }), a, a.n_closed)) };
    }
    if (intent === 'exclude') {
      const all = E.filter(CASES, Object.assign({}, f, { exclude: [] })), ex = E.filter(CASES, Object.assign({}, f, { exclude: EXC_IDS }));
      const a = E.agg(all), b = E.agg(ex);
      return { st: [{ type: 'fact', text: `Reported mean cycle ${f1(a.cycle_mean_d)} d; excluding batches linked to ${EXC_IDS.join(', ')} (${a.n_closed - b.n_closed} batches) it is ${f1(b.cycle_mean_d)} d, so the events add ${f1(a.cycle_mean_d - b.cycle_mean_d)} d. Remaining gap to target: ${sgn(b.cycle_mean_d - b.target_mean_d)} d.` },
        { type: 'inference', text: 'Tick "Exclude exceptional events" in the filter bar to apply this to every screen.' }], calls: [call('agg', Object.assign({}, f, { exclude: [] }), a, a.n_closed), call('agg', Object.assign({}, f, { exclude: EXC_IDS }), b, b.n_closed)] };
    }
    if (intent === 'intervention') {
      const iv = D.interventions[0];
      const pp = E.prePost(CASES, iv.site, iv.pre_window, iv.post_window, { excludeExc: true, mat: state.mat });
      const r = pp[0], w = pp[1];
      return { st: [{ type: 'fact', text: `${iv.id} (${iv.title}, ${SITE(iv.site)}, ${iv.date}): documentation rework ${f1(r.pre)}% → ${f1(r.post)}% (Fisher p ${fp(r.p_value)}); median QA waiting ${f1(w.pre)} → ${f1(w.post)} d (Mann-Whitney p ${fp(w.p_value)}). Other site changed ${sgn(r.comparison_site_change)} pts in rework.` },
        { type: 'hypothesis', text: 'The pre-check caused the reduction; concurrent changes must be ruled out by the process owner.' }], calls: [call('prePost', { site: iv.site, pre: iv.pre_window, post: iv.post_window }, pp, r.n_pre + r.n_post)] };
    }
    if (intent === 'fast_slow') {
      const fs = E.fastSlow(cs);
      return { st: [{ type: 'fact', text: `Fast quartile (n = ${fs.fast.n}) vs slow quartile (n = ${fs.slow.n}): deviation ${f0(fs.fast.deviation_pct)}% vs ${f0(fs.slow.deviation_pct)}%, documentation rework ${f0(fs.fast.doc_rework_pct)}% vs ${f0(fs.slow.doc_rework_pct)}%, QA waiting ${f1(fs.fast.qa_wait_mean_d)} vs ${f1(fs.slow.qa_wait_mean_d)} d, expected path ${f0(fs.fast.conformance_pct)}% vs ${f0(fs.slow.conformance_pct)}%.` },
        { type: 'hypothesis', text: 'Fast batches avoid deviations and documentation loops; association, not proven causation.' }], calls: [call('fastSlow', f, fs)] };
    }
    if (intent === 'opportunities') {
      const ops = E.opportunities(cs, CASES, D.effort).slice(0, 3);
      return { st: [{ type: 'inference', text: 'Top 3 by impact × frequency × confidence ÷ effort: ' + ops.map((o, i) => `${i + 1}) ${o.title} (${f1(o.impact_d)} d/batch above internal best, ${f0(o.frequency_pct)}% of batches, score ${f2(o.score)}): ${o.recommendation}`).join('; ') + '.' }], calls: [call('opportunities', f, ops)] };
    }
    const fw = frameworkAssess(cs);
    return { st: fw.filter((r) => /gmp|annex/i.test(q) ? r.framework.startsWith('EU GMP') : /q10/i.test(q) ? r.framework === 'ICH Q10' : /q9/i.test(q) ? r.framework.startsWith('ICH Q9') : /apqc/i.test(q) ? r.framework.startsWith('APQC') : true)
      .flatMap((r) => [{ type: 'framework', text: `${r.framework} (${r.ref}): ${r.expectation}` }, { type: 'fact', text: 'Evidence: ' + r.evidence_value + '.' }, { type: 'inference', text: 'Status: ' + r.status + ' (draft mapping, SME sign-off required).' }]), calls: [call('frameworkAssess', f, fw)] };
  }
  function ask(q) {
    if (!q.trim()) return;
    const chat = $('#chat');
    const r = liveAnswer(q);
    chat.insertAdjacentHTML('beforeend', `<div class="msg q"><span>${esc(q)}</span></div><div class="msg">${answerHtml(r.st, r.calls)}</div>`);
    chat.scrollTop = chat.scrollHeight;
  }
  function initDrawer() {
    const sug = ['How is batch release performing?', 'Why is the cycle long?', 'Which site has the best release process?', 'Exclude the exceptional events', 'Did the documentation pre-check work?', 'What do fast-release batches do differently?', 'Which three issues should I address first?', 'Analyze this process against GMP', 'Which operator causes the most deviations?'];
    $('#chat').innerHTML = `<p class="small muted">Answers use the current filters and the same deterministic engine as the screens. Each answer shows its trace. For the full scripted demo conversation see the Copilot tab.</p><div class="sugg">${sug.map((s) => `<button>${esc(s)}</button>`).join('')}</div>`;
    $('#chat').querySelectorAll('.sugg button').forEach((b) => b.addEventListener('click', () => ask(b.textContent)));
    $('#fab').addEventListener('click', () => $('#drawer').classList.add('open'));
    $('#drawer-x').addEventListener('click', () => $('#drawer').classList.remove('open'));
    $('#ask-go').addEventListener('click', () => { ask($('#ask').value); $('#ask').value = ''; });
    $('#ask').addEventListener('keydown', (e) => { if (e.key === 'Enter') { ask(e.target.value); e.target.value = ''; } });
  }

  // ---------------------------------------------------------------- shell
  const TABS = [['framework', 'Framework & process', renderFramework], ['cockpit', 'Executive cockpit', renderCockpit], ['explorer', 'Process explorer', renderExplorer],
    ['kpi', 'KPI & benchmark', renderKpi], ['quality', 'Quality intelligence', renderQuality], ['improve', 'Improvement & maturity', renderImprove], ['copilot', 'Copilot', renderCopilot]];
  function showTab(id) {
    state.tab = id;
    document.querySelectorAll('.tab').forEach((t) => t.setAttribute('aria-selected', t.dataset.t === id ? 'true' : 'false'));
    document.querySelectorAll('section.panel').forEach((s) => s.classList.toggle('on', s.id === 'p-' + id));
    try { history.replaceState(null, '', '#' + id); } catch (e) { /* file:// */ }
    render();
    window.scrollTo({ top: 0 });
  }
  function render() { const t = TABS.find((x) => x[0] === state.tab); t[2](); }
  function initFilters() {
    $('#f-site').innerHTML = '<option value="all">Both sites</option>' + Object.keys(D.sites).map((s) => `<option value="${s}">${esc(D.sites[s].label)}</option>`).join('');
    $('#f-mat').innerHTML = '<option value="all">All products</option>' + Object.keys(D.products).map((m) => `<option value="${m}">${esc(D.products[m].name)}</option>`).join('');
    const mo = MONTHS.map((m) => `<option value="${m}">${m}${provisional(m) ? ' (provisional)' : ''}</option>`).join('');
    $('#f-from').innerHTML = mo; $('#f-to').innerHTML = mo;
    $('#f-from').value = state.from; $('#f-to').value = state.to;
    const on = () => {
      state.site = $('#f-site').value; state.mat = $('#f-mat').value; state.from = $('#f-from').value; state.to = $('#f-to').value; state.exc = $('#f-exc').checked;
      if (state.from > state.to) { state.to = state.from; $('#f-to').value = state.to; }
      render();
    };
    ['#f-site', '#f-mat', '#f-from', '#f-to', '#f-exc'].forEach((s) => $(s).addEventListener('change', on));
    $('#tabs').innerHTML = TABS.map(([id, t], i) => `<button class="tab" role="tab" data-t="${id}"><span class="n">${i + 1}</span>${esc(t)}</button>`).join('');
    document.querySelectorAll('.tab').forEach((t) => t.addEventListener('click', () => showTab(t.dataset.t)));
    $('#theme').addEventListener('click', () => {
      const cur = document.documentElement.getAttribute('data-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      document.documentElement.setAttribute('data-theme', cur === 'dark' ? 'light' : 'dark'); render();
    });
    const tip = $('#tip');
    document.addEventListener('mousemove', (e) => {
      const t = e.target.closest && e.target.closest('[data-tip]');
      if (!t) { tip.style.display = 'none'; return; }
      tip.innerHTML = t.getAttribute('data-tip'); tip.style.display = 'block';
      tip.style.left = Math.min(e.clientX + 14, innerWidth - 290) + 'px'; tip.style.top = (e.clientY + 14) + 'px';
    });
  }
  function boot() {
    initFilters(); initDrawer();
    const h = (location.hash || '').slice(1);
    showTab(TABS.some((t) => t[0] === h) ? h : 'framework');
  }
  if (window.echarts) boot(); else { let n = 0; const w = setInterval(() => { if (window.echarts || ++n > 40) { clearInterval(w); boot(); } }, 50); }
})();
