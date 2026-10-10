"""Analytics, copilot grounding and the full synthetic pipeline."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from brpi import analysis as AN
from brpi import config as C
from brpi import copilot as CP
from brpi.kpis import aggregate


def test_maturity_is_additive_and_change_explained(full):
    T = full['T']
    sus = {'INT-01': True}
    m0 = AN.maturity(T, T['month'].between('2026-01', '2026-03'), sus)
    m1 = AN.maturity(T, T['month'].between('2026-06', '2026-08'), sus)
    for m in (m0, m1):
        assert m['score'] == pytest.approx(sum(m['contrib'].values()))
        assert all(0 <= v <= 100 for v in m['dims'].values())
    ch = AN.maturity_change(m0, m1)
    assert sum(ch.values()) == pytest.approx(m1['score'] - m0['score'])
    assert sum(w for _, _, w, _ in AN.MATURITY_DIMS) == pytest.approx(1.0)


def test_intervention_has_real_effect_and_control_site_does_not(full):
    r = AN.intervention_effect(full['T'], C.INTERVENTIONS[0], True)
    k = {x['kpi']: x for x in r['kpis']}
    assert k['doc_rework']['significant'] and k['doc_rework']['change'] < -10
    assert k['doc_rework']['ci95'][1] < 0
    assert abs(k['doc_rework']['comparison_site_change']) < 5          # Site B had no pre-check
    assert k['qa_wait_d']['significant'] and k['qa_wait_d']['change'] < 0
    assert r['sustained']


def test_scenario_exclude_is_exact(full):
    T = full['T']
    m = T['month'].between('2026-06', '2026-08')
    r = AN.scenario_exclude(T, ['EXC-2026-02'], m)
    adj = aggregate(T, m & (T['exc_event'] != 'EXC-2026-02'))
    assert r['adjusted_cycle_mean_d'] == pytest.approx(adj['cycle_mean_d'])
    assert r['event_effect_d'] == pytest.approx(r['reported_cycle_mean_d'] - r['adjusted_cycle_mean_d'])
    assert r['event_effect_d'] > 0 and r['excluded_batches'] >= 10


def test_opportunity_score_formula(full):
    ops = AN.opportunities(full['T'])
    assert ops == sorted(ops, key=lambda o: -o['score'])
    for o in ops:
        assert o['score'] == pytest.approx(o['impact_d'] * o['frequency'] * o['confidence'] / o['effort'])


def test_exceptional_event_cluster_and_lineage_in_generated_data(full):
    T, dq = full['T'], full['dq']
    assert 600 <= len(T) <= 1000
    assert (T['exc_event'] == 'EXC-2026-02').sum() >= 10
    assert dq['rules']['R4_lineage']['splits'] > 0 and dq['rules']['R4_lineage']['merges'] > 0
    assert dq['rules']['R2_duplicates_collapsed']['total'] > 0
    assert any(m['method'].startswith('fuzzy') for m in dq['rules']['R5_crosswalk']['by_method'])
    assert set(T['site']) == set(C.SITES) and set(T['material']) == set(C.PRODUCTS)


def test_grounding_checker():
    res = {'a': 15.234, 'b': [3, {'c': -0.4567}], 'txt': 'coverage 82.1%'}
    assert CP.grounded('Mean 15.2 d, n = 3, change -0.46, coverage 82.1%.', res)[0]
    ok, bad = CP.grounded('Mean 15.2 d and 7.7 d.', res)
    assert not ok and bad == [7.7]
    assert CP.grounded('INT-01 on 2026-06-01, ICH Q10 3.2.1, EXC-2026-02.', {})[0]   # identifiers are not numbers


def test_router_and_unsupported():
    assert CP.route('Which operator causes the most deviations?') == 'unsupported_actor'
    assert CP.route('Predict next month\'s cycle time') == 'unsupported_forecast'
    assert CP.route('Did the intervention work?') == 'intervention'
    assert CP.route('Exclude the HVAC event') == 'exclude'
    assert CP.route('Tell me a joke about cats') == 'unsupported'


def test_transcript_fully_grounded_and_traced(full):
    turns = CP.run_transcript(full['T'])
    assert 8 <= len(turns) <= 12
    for t in turns:
        assert t['grounded'], (t['question'], t['ungrounded_numbers'])
        for c in t['tool_calls']:
            assert c['tool'] in CP.TOOLS and c['query'].startswith('SELECT') and isinstance(c['rows'], int)
    uns = [t for t in turns if not t['tool_calls']]
    assert uns and all(t['answer'][0]['text'].startswith(CP.UNSUPPORTED) for t in uns)
    types = {s['type'] for t in turns for s in t['answer']}
    assert {'fact', 'hypothesis', 'framework', 'inference', 'unsupported'} <= types


def test_tool_schemas_are_valid_json_schema_shapes():
    for name, spec in CP.TOOLS.items():
        assert spec['parameters']['type'] == 'object' and spec['description']
        json.dumps(spec)


def test_generator_is_deterministic(tmp_path):
    from brpi.generate import generate
    a, b = tmp_path / 'a', tmp_path / 'b'
    generate(a)
    generate(b)
    for f in sorted((a / 'raw').glob('*.csv')):
        assert f.read_bytes() == (b / 'raw' / f.name).read_bytes(), f.name


def _node():
    env = Path(__file__).resolve().parents[1] / '..' / '..' / '_tools' / 'env.sh'
    n = shutil.which('node')
    if n:
        return [n], dict(os.environ)
    if env.exists():
        out = subprocess.run(['bash', '-c', 'source %s >/dev/null 2>&1; command -v node; echo; env -0' % env],
                             capture_output=True, text=True)
        path = out.stdout.splitlines()[0] if out.stdout else ''
        if path:
            e = dict(os.environ)
            e['PATH'] = os.path.dirname(path) + ':' + e.get('PATH', '')
            return [path], e
    return None, None


JS = r'''
const fs=require('fs'),vm=require('vm');const root=process.argv[2];
const ctx={window:{}};vm.createContext(ctx);vm.runInContext(fs.readFileSync(root+'/assets/data.js','utf8'),ctx);
const E=require(root+'/assets/engine.js');const D=ctx.window.BRPI;const C=E.hydrate(D);
const ja=E.filter(C,{from:'2026-06',to:'2026-08'});
console.log(JSON.stringify({agg:E.agg(C),dec:E.decompose(E.filter(C,{to:'2026-08'})),mat:E.maturity(ja,D.maturity_dims,D.ci_sustained),
 opp:E.opportunities(ja,C,D.effort),pp:E.prePost(C,'1100',['2026-03-01','2026-05-31'],['2026-06-01','2026-08-31'],{excludeExc:true})}));
'''


def test_js_engine_matches_python(full, tmp_path):
    """Per-case values are exported at 0.001 d precision, hence the 2e-3 tolerance."""
    node, env = _node()
    if not node:
        pytest.skip('node not available')
    root = full['root']
    shutil.copy(Path(__file__).resolve().parents[1] / 'assets' / 'engine.js', root / 'assets' / 'engine.js')
    p = tmp_path / 'p.js'
    p.write_text(JS)
    js = json.loads(subprocess.run(node + [str(p), str(root)], capture_output=True, text=True, env=env, check=True).stdout)
    T = full['T']
    py = aggregate(T)
    for k, v in py.items():
        if v is not None:
            assert js['agg'][k] == pytest.approx(v, abs=2e-3), k
    from brpi.kpis import decompose
    for k, v in decompose(T, T['month'] <= '2026-08').items():
        assert js['dec'][k] == pytest.approx(v, abs=2e-3), k
    iv = AN.intervention_effect(T, C.INTERVENTIONS[0], True)
    m = AN.maturity(T, T['month'].between('2026-06', '2026-08'), {'INT-01': iv['sustained']})
    assert js['mat']['score'] == pytest.approx(m['score'], abs=2e-3)
    ops = AN.opportunities(T, T['month'].between('2026-06', '2026-08'))
    assert [o['key'] for o in js['opp']] == [o['key'] for o in ops]
    for a, b in zip(ops, js['opp']):
        assert b['score'] == pytest.approx(a['score'], abs=2e-3)
    for a, b in zip(iv['kpis'], js['pp']):
        assert b['pre'] == pytest.approx(a['pre'], abs=2e-3) and b['post'] == pytest.approx(a['post'], abs=2e-3)
        assert b['p_value'] == pytest.approx(a['p_value'], rel=2e-2, abs=1e-4), a['kpi']
