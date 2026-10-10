"""Process mining on the event log: variants, directly-follows graph, bottlenecks, loops, conformance."""
from collections import defaultdict

import numpy as np
import pandas as pd


def variants(T, top=10):
    c = T[T['closed']]
    g = c.groupby('variant').agg(cases=('case_id', 'size'), cycle_mean_d=('cycle_d', 'mean'),
                                 conformant=('conformant', 'first')).sort_values('cases', ascending=False)
    g['share_pct'] = 100 * g['cases'] / len(c)
    g['cum_share_pct'] = g['share_pct'].cumsum()
    return g.head(top).reset_index(), int(len(g))


def dfg(trans, cases):
    """Directly-follows graph over the given cases: {(a, b): {count, median_wait_h, mean_wait_h}}."""
    acc = defaultdict(list)
    for cid in cases:
        for a, b, w in trans.get(cid, []):
            acc[(a, b)].append(w)
    return {k: {'count': len(v), 'median_wait_h': float(np.median(v)), 'mean_wait_h': float(np.mean(v))}
            for k, v in acc.items()}


def bottlenecks(graph, min_count=20, top=5):
    rows = [{'from': a, 'to': b, **v} for (a, b), v in graph.items() if v['count'] >= min_count]
    return sorted(rows, key=lambda r: -r['median_wait_h'])[:top]


def loops(T):
    c = T[T['closed']]
    n = len(c)
    return {
        'Batch record returned and re-reviewed': 100 * float(c['doc_rework'].mean()),
        'Batch record returned twice or more': 100 * float((c['doc_loops'] >= 2).mean()),
        'Repeated QA disposition review (query)': 100 * float(c['qa_repeat'].mean()),
        'Second inspection lot (retest)': 100 * float(c['retest'].mean()),
        'Deviation reopened': 100 * float(c['dev_reopened'].mean()),
        'Usage decision changed': 100 * float(c['ud_changed'].mean()),
        '_n': n,
    }


def conformance_summary(T):
    c = T[T['closed']]
    iss = c['issues'].str.split('; ').explode()
    iss = iss[iss.fillna('') != '']
    return {'conformant_pct': 100 * float(c['conformant'].mean()),
            'issues': iss.value_counts().head(12).to_dict(), '_n': int(len(c))}
