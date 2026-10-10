"""Copilot tool layer (spec Option C: no LLM in the loop).

* Every number the copilot may quote comes from a tool call below. Tools are plain functions over the
  deterministic case table, each with a JSON schema, so the same layer can later be exposed to an
  approved enterprise LLM endpoint as function-calling tools (Option A) without changing the maths.
* Every tool returns {result, query, rows, filters}: the KPI, the filters, an SQL-equivalent of the
  query and the row count, which the UI shows as the answer's trace.
* grounded() verifies that every number in an answer appears in the tool results of that answer.
* Questions outside the tool set are answered "Not supported by the data" (see route()).
"""
import json
import re

import pandas as pd

from . import analysis as AN
from . import config as C
from . import frameworks as FW
from .kpis import aggregate, decompose

FILTER_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'properties': {
        'site': {'type': 'string', 'enum': ['all'] + list(C.SITES), 'default': 'all'},
        'material': {'type': 'string', 'enum': ['all'] + list(C.PRODUCTS), 'default': 'all'},
        'month_from': {'type': 'string', 'pattern': r'^\d{4}-\d{2}$'},
        'month_to': {'type': 'string', 'pattern': r'^\d{4}-\d{2}$'},
        'exclude_events': {'type': 'array', 'items': {'type': 'string'}, 'default': []},
    },
}

TOOLS = {
    'get_kpis': {'description': 'Aggregate release KPIs over closed batches in scope, optionally versus a comparison scope.',
                 'parameters': {'type': 'object', 'required': ['filters'], 'properties': {
                     'filters': FILTER_SCHEMA, 'compare_to': FILTER_SCHEMA}}},
    'decompose_cycle_time': {'description': 'Split mean release cycle time into critical-path segments that sum exactly to it.',
                             'parameters': {'type': 'object', 'required': ['filters'], 'properties': {
                                 'filters': FILTER_SCHEMA, 'compare_to': FILTER_SCHEMA}}},
    'compare_sites_like_for_like': {'description': 'Compare sites on materials produced at both sites, per material.',
                                    'parameters': {'type': 'object', 'required': ['filters'], 'properties': {'filters': FILTER_SCHEMA}}},
    'list_exceptional_events': {'description': 'List registered exceptional events, optionally similar to one event (same category or site).',
                                'parameters': {'type': 'object', 'properties': {'similar_to': {'type': 'string'}}}},
    'scenario_exclude': {'description': 'Recompute KPIs with the batches linked to the given exceptional events excluded.',
                         'parameters': {'type': 'object', 'required': ['event_ids', 'filters'], 'properties': {
                             'event_ids': {'type': 'array', 'items': {'type': 'string'}}, 'filters': FILTER_SCHEMA,
                             'prior': FILTER_SCHEMA}}},
    'intervention_effect': {'description': 'Pre/post test for a recorded intervention (Mann-Whitney / Fisher + bootstrap CI, '
                                           'difference-in-differences against the other site).',
                            'parameters': {'type': 'object', 'required': ['intervention_id'], 'properties': {
                                'intervention_id': {'type': 'string'}, 'exclude_exceptional': {'type': 'boolean', 'default': True}}}},
    'fast_vs_slow': {'description': 'Profile fastest vs slowest quartile of batches (cycle time relative to product target).',
                     'parameters': {'type': 'object', 'required': ['filters'], 'properties': {'filters': FILTER_SCHEMA}}},
    'rank_opportunities': {'description': 'Rank improvement opportunities by impact x frequency x confidence / effort.',
                           'parameters': {'type': 'object', 'required': ['filters'], 'properties': {'filters': FILTER_SCHEMA}}},
    'framework_assessment': {'description': 'Evaluate the DRAFT framework mapping against the data.',
                             'parameters': {'type': 'object', 'required': ['framework'], 'properties': {
                                 'framework': {'type': 'string'}, 'filters': FILTER_SCHEMA}}},
}


def mask_of(T, f):
    f = f or {}
    m = pd.Series(True, index=T.index)
    if f.get('site', 'all') != 'all':
        m &= T['site'] == f['site']
    if f.get('material', 'all') != 'all':
        m &= T['material'] == f['material']
    if f.get('month_from'):
        m &= T['month'] >= f['month_from']
    if f.get('month_to'):
        m &= T['month'] <= f['month_to']
    if f.get('exclude_events'):
        m &= ~T['exc_event'].isin(f['exclude_events'])
    return m


def sql_of(f, what='*'):
    f = f or {}
    w = ['closed']
    if f.get('site', 'all') != 'all':
        w.append("site = '%s'" % f['site'])
    if f.get('material', 'all') != 'all':
        w.append("material = '%s'" % f['material'])
    if f.get('month_from'):
        w.append("month >= '%s'" % f['month_from'])
    if f.get('month_to'):
        w.append("month <= '%s'" % f['month_to'])
    if f.get('exclude_events'):
        w.append('exc_event NOT IN (%s)' % ', '.join("'%s'" % e for e in f['exclude_events']))
    return 'SELECT %s FROM cases WHERE %s' % (what, ' AND '.join(w))


class Tools:
    def __init__(self, T):
        self.T = T

    def _rows(self, f):
        m = mask_of(self.T, f)
        return int((m & self.T['closed']).sum())

    def get_kpis(self, filters, compare_to=None):
        a = aggregate(self.T, mask_of(self.T, filters))
        res = {'scope': a}
        q = sql_of(filters, 'AVG(cycle_d), AVG(rft), AVG(ontime), ...')
        if compare_to:
            b = aggregate(self.T, mask_of(self.T, compare_to))
            res['compare'] = b
            res['diff'] = {k: a[k] - b[k] for k in a if isinstance(a.get(k), float) and isinstance(b.get(k), float)}
            q += ' ; ' + sql_of(compare_to, 'same KPIs')
        return {'result': res, 'query': q, 'rows': self._rows(filters), 'filters': filters}

    def decompose_cycle_time(self, filters, compare_to=None):
        a = decompose(self.T, mask_of(self.T, filters))
        res = {'scope': a}
        q = sql_of(filters, 'AVG(seg_documentation), AVG(seg_qc), AVG(seg_deviation), AVG(seg_qa_stage), AVG(seg_approval)')
        if compare_to:
            b = decompose(self.T, mask_of(self.T, compare_to))
            res['compare'] = b
            res['diff'] = {k: a[k] - b[k] for k in a if not k.startswith('_')}
            q += ' ; ' + sql_of(compare_to, 'same segments')
        return {'result': res, 'query': q, 'rows': a['_n'], 'filters': filters}

    def compare_sites_like_for_like(self, filters):
        r = AN.like_for_like(self.T, mask_of(self.T, filters))
        slim = [{k: x.get(k) for k in ['product', 'site', 'n_closed', 'cycle_mean_d', 'qa_wait_mean_d', 'doc_rework_pct',
                                        'rft_pct', 'segments']} for x in r]
        return {'result': slim, 'query': sql_of(filters, 'material, site, AVG(...)') + ' AND material IN (made at both sites) GROUP BY material, site',
                'rows': int(sum(x['n_closed'] for x in r)), 'filters': filters}

    def list_exceptional_events(self, similar_to=None):
        ev = C.EXCEPTIONAL_EVENTS
        if similar_to:
            ref = next(e for e in ev if e['id'] == similar_to)
            ev = [e for e in ev if e['type'] == ref['type']]
        out = []
        for e in ev:
            linked = self.T[(self.T['exc_event'] == e['id']) & self.T['closed']]
            month = linked['month'].mode().iloc[0] if len(linked) else ''
            same = self.T[(self.T['site'] == e['site']) & self.T['closed'] & (self.T['exc_event'] == '') &
                          (self.T['month'] == month)]
            out.append({**e, 'linked_batches': int(len(linked)), 'linked_cycle_mean_d': float(linked['cycle_d'].mean()),
                        'same_site_month_unaffected_cycle_mean_d': float(same['cycle_d'].mean())})
        out = {'count': len(out), 'events': out}
        return {'result': out, 'query': "SELECT exc_event, COUNT(*), AVG(cycle_d) FROM cases WHERE closed AND exc_event <> '' GROUP BY exc_event",
                'rows': int(sum(x['linked_batches'] for x in out['events'])), 'filters': {'similar_to': similar_to}}

    def scenario_exclude(self, event_ids, filters, prior=None):
        r = AN.scenario_exclude(self.T, event_ids, mask_of(self.T, filters), mask_of(self.T, prior) if prior else None)
        if prior:
            r['improvement_vs_prior_d'] = r['prior_cycle_mean_d'] - r['adjusted_cycle_mean_d']
            r['prior_gap_to_target_d'] = r['prior_cycle_mean_d'] - r['prior_target_mean_d']
            r['gap_improvement_d'] = r['prior_gap_to_target_d'] - r['gap_to_target_d']
        ch = {k: v['adjusted'] - v['reported'] for k, v in r['kpi_changes'].items()
              if v['adjusted'] is not None and v['reported'] is not None}
        r['largest_relative_change'] = max(ch, key=lambda k: abs(ch[k]) / max(abs(r['kpi_changes'][k]['reported']), 1e-9))
        r['largest_change_value'] = ch[r['largest_relative_change']]
        q = sql_of(filters, 'AVG(cycle_d)') + ' ; ' + sql_of(dict(filters, exclude_events=event_ids), 'AVG(cycle_d)')
        return {'result': r, 'query': q, 'rows': self._rows(filters), 'filters': filters}

    def intervention_effect(self, intervention_id, exclude_exceptional=True):
        iv = next(i for i in C.INTERVENTIONS if i['id'] == intervention_id)
        r = AN.intervention_effect(self.T, iv, exclude_exceptional)
        q = ("SELECT kpi FROM cases WHERE closed AND site = '%s' AND mfg_complete BETWEEN '%s' AND '%s' (pre) / BETWEEN '%s' AND '%s' (post)"
             "%s ; same for the other site (difference-in-differences)" %
             (iv['site'], iv['pre_window'][0], iv['pre_window'][1], iv['post_window'][0], iv['post_window'][1],
              " AND exc_event = ''" if exclude_exceptional else ''))
        return {'result': r, 'query': q, 'rows': int(sum(k['n_pre'] + k['n_post'] for k in r['kpis'][:1])),
                'filters': {'intervention_id': intervention_id, 'exclude_exceptional': exclude_exceptional}}

    def fast_vs_slow(self, filters):
        r = AN.fast_slow(self.T, mask_of(self.T, filters))
        r['facts'] = AN.facts(self.T, mask_of(self.T, filters))
        return {'result': r, 'query': sql_of(filters, 'cycle_d / target_d AS ratio, ...') + ' ; quartiles of ratio',
                'rows': self._rows(filters), 'filters': filters}

    def rank_opportunities(self, filters):
        r = AN.opportunities(self.T, mask_of(self.T, filters))
        return {'result': r, 'query': sql_of(filters, 'segment means') + ' ; internal best = min over site-quarter groups (n >= 15)',
                'rows': self._rows(filters), 'filters': filters}

    def framework_assessment(self, framework, filters=None):
        rows = [r for r in FW.assess(self.T, mask_of(self.T, filters)) if framework.lower() in r['framework'].lower()]
        return {'result': rows, 'query': sql_of(filters or {}, 'control checks per mapping row'),
                'rows': self._rows(filters or {}), 'filters': dict(filters or {}, framework=framework)}


# ------------------------------------------------------------------ grounding
_SKIP = [r'\d{4}-\d{2}-\d{2}', r'\d{4}-\d{2}', r'(EXC|INT)-[\d-]+', r'Q\d+(\(R\d\))?', r'\b\d+\.\d+\.\d+\b',
         r'Annex \d+', r'\bL[1-4]\b', r'\bP90\b', r'\b(1100|2200)\b', r'MAT-\d+', r'\b(19|21|9) d target\b',
         r'95%', r'14-day', r'<\s?0\.001', r'\b(one|two|three)\b', r'\bpre[- ]?\d+\b']


def numbers_in(text):
    t = text
    for p in _SKIP:
        t = re.sub(p, ' ', t)
    return [float(x.replace(',', '')) for x in re.findall(r'-?\d+(?:\.\d+)?', t)]


def _collect(o, acc):
    if isinstance(o, bool):
        return
    if isinstance(o, (int, float)):
        if o == o:
            for d in (0, 1, 2, 3):
                acc.add(round(float(o), d))
                acc.add(round(abs(float(o)), d))
        return
    if isinstance(o, str):
        for x in numbers_in(o):
            _collect(x, acc)
        return
    if isinstance(o, dict):
        for v in o.values():
            _collect(v, acc)
    elif isinstance(o, (list, tuple)):
        for v in o:
            _collect(v, acc)


def grounded(text, results):
    """True iff every number in text equals some number returned by the tools (at the shown precision)."""
    acc = set()
    _collect(results, acc)
    bad = [n for n in numbers_in(text) if round(n, 3) not in acc]
    return len(bad) == 0, bad


# ------------------------------------------------------------------ routing (deterministic)
UNSUPPORTED = 'Not supported by the data.'
INTENTS = [
    ('unsupported_actor', r'\b(operator|person|who|employee|name)\b'),
    ('unsupported_forecast', r'\b(predict|forecast|next month|will be)\b'),
    ('intervention', r'\b(intervention|pre-?check|did it work|working|implemented)\b'),
    ('similar_events', r'\b(similar|all .*events?)\b'),
    ('exclude', r'\b(exclude|without|except)\b'),
    ('fast_slow', r'\b(fast|slow)\b.*\b(batch|batches|release)\b|differently'),
    ('compare_sites', r'\bsite\b.*\b(slower|faster|best|compare)\b|\b(slower|faster)\b.*\bsite\b'),
    ('deteriorate', r'\b(why|deteriorat|worse|drop)\b'),
    ('opportunities', r'\b(improve|address first|issues|priorit|what next)\b'),
    ('framework', r'\b(gmp|annex|ich|q10|q9|apqc|framework)\b'),
    ('performance', r'\b(perform|how is|status|kpi)\b'),
]


def route(question):
    q = question.lower()
    for name, pat in INTENTS:
        if re.search(pat, q):
            return name
    return 'unsupported'


def fp(p):
    return '< 0.001' if p < 0.001 else '= %.3f' % p


def f1(x):
    return '%.1f' % x


def f0(x):
    return '%.0f' % x


def run_transcript(T):
    """Execute the scripted copilot conversation against the real tools. Returns a list of turns."""
    tl = Tools(T)
    turns = []

    def turn(q, calls, statements):
        results = [c['result'] for c in calls]
        text = ' '.join(s['text'] for s in statements)
        ok, bad = grounded(text, results)
        turns.append({'question': q, 'intent': route(q), 'tool_calls': calls, 'answer': statements,
                      'grounded': ok, 'ungrounded_numbers': bad})

    def call(name, **args):
        out = getattr(tl, name)(**args)
        return {'tool': name, 'args': args, 'query': out['query'], 'rows': out['rows'], 'result': out['result']}

    # 1 performance this month
    aug, jul = {'month_from': '2026-08', 'month_to': '2026-08'}, {'month_from': '2026-07', 'month_to': '2026-07'}
    sep = {'month_from': '2026-09', 'month_to': '2026-09'}
    c1, c1b = call('get_kpis', filters=aug, compare_to=jul), call('get_kpis', filters=sep)
    a, d = c1['result']['scope'], c1['result']['diff']
    s = c1b['result']['scope']
    turn('How is batch release performing this month?', [c1, c1b], [
        {'type': 'fact', 'text': 'Latest complete month (2026-08, %d batches released): mean release cycle %s d against a '
                                 'product-weighted target of %s d; %s%% released within target; right first time %s%%.'
                                 % (a['n_closed'], f1(a['cycle_mean_d']), f1(a['target_mean_d']), f0(a['ontime_pct']), f0(a['rft_pct']))},
        {'type': 'fact', 'text': 'Versus 2026-07 the mean cycle changed by %s d and right first time by %s points.'
                                 % (('+' if d['cycle_mean_d'] >= 0 else '') + f1(d['cycle_mean_d']), f1(d['rft_pct']))},
        {'type': 'inference', 'text': 'September is shown as provisional: %d of %d batches completed in 2026-09 have no usage '
                                      'decision yet, so its average is biased towards fast batches (right-censoring).'
                                      % (s['n_open'], s['n_cases'])},
    ])

    # 2 why deteriorate
    c2 = call('decompose_cycle_time', filters=aug, compare_to=jul)
    diff = c2['result']['diff']
    top = max(diff, key=lambda k: diff[k])
    c2b = call('list_exceptional_events')
    ev2 = next(e for e in c2b['result']['events'] if e['id'] == 'EXC-2026-02')
    turn('Why did performance deteriorate in August?', [c2, c2b], [
        {'type': 'fact', 'text': 'Mean cycle went from %s d (July) to %s d (August). The largest increase is in "%s": +%s d per batch.'
                                 % (f1(c2['result']['compare']['_cycle_mean_d']), f1(c2['result']['scope']['_cycle_mean_d']),
                                    top, f1(diff[top]))},
        {'type': 'fact', 'text': '%d batches at Site B are linked to exceptional event EXC-2026-02 (%s); their mean cycle is %s d '
                                 'versus %s d for unaffected Site B batches of the same month.'
                                 % (ev2['linked_batches'], ev2['title'], f1(ev2['linked_cycle_mean_d']),
                                    f1(ev2['same_site_month_unaffected_cycle_mean_d']))},
        {'type': 'hypothesis', 'text': 'The August deterioration is mostly driven by the HVAC excursion through longer deviation '
                                       'closure. Test: exclude the event and recompute (next question).'},
    ])

    # 3 exclude
    q3f, q3p = {'month_from': '2026-06', 'month_to': '2026-08'}, {'month_from': '2026-03', 'month_to': '2026-05'}
    c3 = call('scenario_exclude', event_ids=['EXC-2026-02'], filters=q3f, prior=q3p)
    r = c3['result']
    turn('Exclude the batches affected by the HVAC excursion. Is our performance actually improving?', [c3], [
        {'type': 'fact', 'text': 'Jun-Aug reported mean cycle %s d; excluding the %d affected batches it is %s d, so the event '
                                 'added about %s d to the reported average.'
                                 % (f1(r['reported_cycle_mean_d']), r['excluded_batches'], f1(r['adjusted_cycle_mean_d']),
                                    f1(r['event_effect_d']))},
        {'type': 'fact', 'text': 'Underlying performance improved versus Mar-May (%s d, exceptional events excluded) by %s d, but '
                                 'remains %s d above the product-weighted target of %s d.'
                                 % (f1(r['prior_cycle_mean_d']), f1(r['improvement_vs_prior_d']), f1(r['gap_to_target_d']),
                                    f1(r['target_mean_d']))},
    ])

    # 4 similar events, exclude from last six months
    c4 = call('list_exceptional_events', similar_to='EXC-2026-02')
    six = {'month_from': '2026-03', 'month_to': '2026-08'}
    ids = [e['id'] for e in c4['result']['events']]
    c4b = call('scenario_exclude', event_ids=ids, filters=six)
    r4 = c4b['result']
    lab = {'cycle_mean_d': 'release cycle time', 'qa_wait_mean_d': 'QA review waiting', 'dev_res_mean_d': 'deviation resolution time',
           'deviation_rate_pct': 'share of batches with a deviation', 'rft_pct': 'right first time', 'qc_delay_mean_d': 'QC result availability',
           'doc_rework_pct': 'documentation rework', 'qa_repeat_pct': 'repeat QA queries', 'handoffs_mean': 'hand-offs',
           'conformance_pct': 'expected-path conformance'}
    kc = r4['kpi_changes'][r4['largest_relative_change']]
    turn('Show me all similar exceptional events and exclude them from the last six months. Which KPI changed most?', [c4, c4b], [
        {'type': 'fact', 'text': 'The register holds %d exceptional events: %s.' % (c4['result']['count'], '; '.join(
            '%s %s at %s (%d batches, mean cycle %s d)' % (e['id'], e['title'], C.SITES[e['site']]['name'], e['linked_batches'],
                                                          f1(e['linked_cycle_mean_d'])) for e in c4['result']['events']))},
        {'type': 'fact', 'text': 'Excluding both from Mar-Aug removes %d batches: mean cycle %s d -> %s d. The KPI that changed most '
                                 '(relative) is %s: %s -> %s.'
                                 % (r4['excluded_batches'], f1(r4['reported_cycle_mean_d']), f1(r4['adjusted_cycle_mean_d']),
                                    lab.get(r4['largest_relative_change'], r4['largest_relative_change']), f1(kc['reported']), f1(kc['adjusted']))},
        {'type': 'inference', 'text': 'Events are matched by an explicit reference on the deviation notification, not by text '
                                      'similarity; unlinked batches are never excluded silently.'},
    ])

    # 5 why is Site A slower (like for like)
    pre = {'month_from': '2026-01', 'month_to': '2026-05', 'exclude_events': ids}
    c5 = call('compare_sites_like_for_like', filters=pre)
    rows = c5['result']
    st = []
    for prod in sorted({x['product'] for x in rows}):
        A = next(x for x in rows if x['product'] == prod and x['site'] == 'Site A')
        B = next(x for x in rows if x['product'] == prod and x['site'] == 'Site B')
        st.append('%s: Site A %s d vs Site B %s d (QA stage %s vs %s d; documentation rework %s%% vs %s%%)' % (
            prod, f1(A['cycle_mean_d']), f1(B['cycle_mean_d']), f1(A['segments']['QA queue + disposition review']),
            f1(B['segments']['QA queue + disposition review']), f0(A['doc_rework_pct']), f0(B['doc_rework_pct'])))
    turn('Why is Site A slower than Site B on the same products?', [c5], [
        {'type': 'fact', 'text': 'Like-for-like, Jan-May, exceptional events excluded. ' + '; '.join(st) + '.'},
        {'type': 'inference', 'text': 'Comparing only materials made at both sites removes the product-mix effect (Site B makes '
                                      'more sterile product with a 14-day sterility test).'},
        {'type': 'hypothesis', 'text': 'Site A is slower mainly because batches queue longer for QA disposition review, and '
                                       'documentation is sent back more often. Both are addressable process drivers.'},
    ])

    # 6 intervention
    c6 = call('intervention_effect', intervention_id='INT-01', exclude_exceptional=True)
    k = {x['kpi']: x for x in c6['result']['kpis']}
    dr, qw, cy = k['doc_rework'], k['qa_wait_d'], k['cycle_d']
    seg = c6['result']['post_segments_share_pct']
    big = max(seg, key=lambda x: seg[x])
    turn('We introduced a quality-documentation pre-check at Site A on 1 June. Is it working?', [c6], [
        {'type': 'fact', 'text': 'Documentation rework at Site A: %s%% before -> %s%% after (%s points; 95%% CI %s to %s; Fisher p %s; '
                                 'n = %d / %d).' % (f1(dr['pre']), f1(dr['post']), f1(dr['change']), f1(dr['ci95'][0]),
                                                    f1(dr['ci95'][1]), fp(dr['p_value']), dr['n_pre'], dr['n_post'])},
        {'type': 'fact', 'text': 'Median QA review waiting %s d -> %s d (Mann-Whitney p %s); median release cycle %s d -> %s d '
                                 '(p %s).' % (f1(qw['pre']), f1(qw['post']), fp(qw['p_value']), f1(cy['pre']),
                                               f1(cy['post']), fp(cy['p_value']))},
        {'type': 'fact', 'text': 'Over the same windows Site B (no pre-check) changed by %s points in documentation rework; the '
                                 'difference-in-differences is %s points.' % (f1(dr['comparison_site_change']), f1(dr['did_means']))},
        {'type': 'fact', 'text': 'After the intervention, %s%% of the remaining Site A cycle sits in "%s".' % (f0(seg[big]), big)},
        {'type': 'hypothesis', 'text': 'The pre-check caused the reduction in documentation rework. The comparison site makes a '
                                       'common seasonal cause unlikely, but staffing or SOP changes in the same window would need '
                                       'to be ruled out by the process owner.'},
    ])

    # 7 fast vs slow
    allf = {'month_from': '2026-01', 'month_to': '2026-08'}
    c7 = call('fast_vs_slow', filters=allf)
    fs = c7['result']
    F, S, fa = fs['fast'], fs['slow'], fs['facts']
    turn('What do fast-release batches do differently?', [c7], [
        {'type': 'fact', 'text': 'Fastest quartile (cycle <= %s x target, n = %d) vs slowest quartile (>= %s x target, n = %d): '
                                 'deviation %s%% vs %s%%; documentation rework %s%% vs %s%%; mean QA waiting %s d vs %s d; '
                                 'hand-offs %s vs %s; expected-path conformance %s%% vs %s%%.'
                                 % (f1(fs['fast_max_ratio']), F['n'], f1(fs['slow_min_ratio']), S['n'], f0(F['deviation_pct']),
                                    f0(S['deviation_pct']), f0(F['doc_rework_pct']), f0(S['doc_rework_pct']), f1(F['qa_wait_mean_d']),
                                    f1(S['qa_wait_mean_d']), f1(F['handoffs_mean']), f1(S['handoffs_mean']),
                                    f0(F['conformance_pct']), f0(S['conformance_pct']))},
        {'type': 'fact', 'text': '%s%% of slow batches went through two or more extra documentation-review cycles. Of batches more '
                                 'than 5 days over target, %s%% had a deviation (vs %s%% of batches released on time).'
                                 % (f0(S['doc_loops2_pct']), f0(fa['late5_with_dev_pct']), f0(fa['ontime_with_dev_pct']))},
        {'type': 'hypothesis', 'text': 'Deviation-closure latency and QA queueing appear to be the main contributors to slow '
                                       'release; association, not proven causation.'},
    ])

    # 8 top three issues
    c8 = call('rank_opportunities', filters={'month_from': '2026-06', 'month_to': '2026-08'})
    ops = c8['result'][:3]
    turn('Which three issues should I address first?', [c8], [
        {'type': 'inference', 'text': 'Ranked by impact x frequency x confidence / effort (Jun-Aug, both sites): ' + '; '.join(
            '%d) %s: %s d/batch above internal best (%s d vs %s d), affects %s%% of batches, score %s'
            % (i + 1, o['title'], f1(o['impact_d']), f1(o['current_d']), f1(o['internal_best_d']), f0(o['frequency_pct']),
               '%.2f' % o['score']) for i, o in enumerate(ops)) + '.'},
        {'type': 'inference', 'text': 'Recommendations: ' + ' | '.join(o['recommendation'] for o in ops) + '. Effort/risk weights are '
                                      'SME assumptions and should be confirmed with the process owner.'},
    ])

    # 9 framework
    c9 = call('framework_assessment', framework='EU GMP Annex 16', filters={'month_from': '2026-01', 'month_to': '2026-08'})
    st9 = []
    for row in c9['result']:
        st9.append({'type': 'framework', 'text': 'Reference (%s, %s): %s' % (row['framework'], row['ref'], row['expectation'])})
        st9.append({'type': 'fact', 'text': 'Evidence: %s.' % row['evidence_value']})
        st9.append({'type': 'inference', 'text': 'Status: %s.' % row['status']})
    st9.append({'type': 'inference', 'text': 'The mapping is a DRAFT for SME sign-off; the system supports, and does not replace, '
                                             'QP / QA judgement.'})
    turn('Analyze this process against GMP.', [c9], st9)

    # 10 unsupported
    turn('Which operator causes the most deviations?', [], [
        {'type': 'unsupported', 'text': UNSUPPORTED + ' The extract carries organisational roles only (actors are anonymised), '
                                        'so per-person attribution is neither possible nor intended.'}])
    turn('Predict next month\'s release cycle time.', [], [
        {'type': 'unsupported', 'text': UNSUPPORTED + ' No validated forecasting model is part of this PoC; the copilot only '
                                        'reports measured history and recorded scenarios.'}])
    return turns


def tool_specs():
    return [{'name': k, **v} for k, v in TOOLS.items()]


def dumps(o):
    return json.dumps(o, default=str, indent=1)
