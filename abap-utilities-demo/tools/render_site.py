"""Optional static documentation build; pip install markdown-it-py first."""
from pathlib import Path
import html
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
md = MarkdownIt('commonmark', {'html': False}).enable('table')
record = md.render((ROOT / 'DEMO.md').read_text())
sales = md.render((ROOT / 'SALES-NOTE.md').read_text())
blocks = []
for path in sorted((ROOT / 'src').glob('*.abap')):
    label = 'Unit tests' if '.testclasses.' in path.name else 'Production source'
    blocks.append(f'<details class="source"><summary>{html.escape(path.name)} <small>{label}</small></summary>'
                  f'<p><a href="src/{html.escape(path.name)}" download>Download source</a></p>'
                  f'<pre><code>{html.escape(path.read_text())}</code></pre></details>')
page = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Synthetic utilities ABAP source and authored unit tests. Verified on the open-source abaplint/transpiler stack; no SAP system.">
<title>Utilities ABAP demo — source and verification record</title>
<style>
:root{color-scheme:light;--ink:#152c3a;--muted:#536574;--border:#cbd8dc;--accent:#00665e}
*{box-sizing:border-box}body{margin:0;background:#f6f8f8;color:var(--ink);font:16px/1.6 system-ui,sans-serif}
header,main,footer{max-width:1120px;margin:auto;padding:26px clamp(18px,4vw,48px)}
.notice{background:#fff0cc;border-bottom:1px solid #d8b65e;padding:10px 20px;text-align:center;font-weight:600}
.eyebrow{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:750}
h1{font-size:clamp(30px,5vw,48px);line-height:1.15;margin:14px 0;max-width:850px}h2{line-height:1.25;margin-top:1.6em}
.lead{font-size:19px;max-width:800px;color:var(--muted)}a{color:var(--accent);text-underline-offset:3px}
nav{display:flex;flex-wrap:wrap;gap:10px 24px;margin:24px 0}nav a{font-weight:650}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:24px 0}
.card{background:white;border:1px solid var(--border);border-radius:10px;padding:18px}
.card strong{font-size:32px;display:block}.card span{color:var(--muted)}
section{background:white;border:1px solid var(--border);border-radius:12px;margin:0 0 24px;padding:24px clamp(16px,3vw,32px);scroll-margin-top:20px}
section>h2:first-child{margin-top:0}.expected{border-left:4px solid var(--accent);padding-left:18px}
pre{overflow:auto;max-height:620px;background:#122b38;color:#eff5f7;border-radius:8px;padding:18px;font:13px/1.6 ui-monospace,monospace;tab-size:2}
:not(pre)>code{background:#edf2f4;padding:2px 4px;border-radius:3px;font-size:.9em}
table{border-collapse:collapse;display:block;overflow:auto}th,td{padding:8px 12px;border:1px solid var(--border);text-align:left;vertical-align:top}
.source{border-top:1px solid var(--border);padding:13px 0}.source summary{cursor:pointer;font-weight:650;overflow-wrap:anywhere}
small{font-weight:400;color:var(--muted);display:inline-block;margin-left:12px}
input{width:100%;font:inherit;padding:12px;border:1px solid #9bafb7;border-radius:6px;margin:8px 0 18px}
footer{color:var(--muted);font-size:14px;padding-bottom:48px}li{margin-bottom:8px}
@media(max-width:620px){.cards{grid-template-columns:1fr}.card strong{font-size:26px}section{padding:18px}main{padding-top:0}}
</style></head><body>
<div class="notice" role="note">Synthetic sample data · No SAP system · Verified on open-source tooling</div>
<header><div class="eyebrow">Energy &amp; Utilities / ABAP source demonstration</div>
<h1>Meter readings, estimates and a traceable worklist.</h1>
<p class="lead">A small AI-assisted implementation with explicit business rules, decimal billing calculations and reviewable tests. Run on the open-source abaplint/transpiler stack: 77 of 77 unit methods executed, 0 lint issues; not run on a real SAP system.</p>
<nav aria-label="Demo sections"><a href="#verification">Verification record</a><a href="#source">Browse ABAP</a><a href="#scope">Delivery scope</a><a href="README.md">Technical contract</a></nav>
<div class="cards"><div class="card"><strong>77</strong><span>ABAP Unit methods authored</span></div>
<div class="card"><strong>0</strong><span>SAP systems used (open-source runtime only)</span></div>
<div class="card"><strong>77 / 77</strong><span>ABAP Unit methods executed, 0 lint issues</span></div></div>
<p class="expected"><b>Expected example, calculated by hand:</b> 120 kWh → 36.00 EUR net + 6.84 tax = <b>42.84 EUR gross</b>. This is an expectation, not an executed result.</p></header>
<main><section id="verification">__RECORD__</section>
<section id="source"><h2>ABAP source and test cases</h2><p>The browser displays source only. It does not execute ABAP or simulate SAP.</p>
<label for="filter">Filter filenames or source text</label><input id="filter" type="search" placeholder="Try rollover, leap_year or worklist">
<p id="matches" aria-live="polite"></p>__SOURCE__</section>
<section id="scope">__SALES__</section></main>
<footer>Local static documentation. No analytics, remote assets or source uploads. No SAP kernel was used.</footer>
<script>
const filter=document.querySelector('#filter');const entries=[...document.querySelectorAll('.source')];
function refresh(){const query=filter.value.trim().toLowerCase();let shown=0;entries.forEach(entry=>{const match=entry.textContent.toLowerCase().includes(query);entry.hidden=!match;if(match)shown++;});document.querySelector('#matches').textContent=shown+' of '+entries.length+' source files shown';}
filter.addEventListener("input",refresh);refresh();
</script></body></html>
'''
(ROOT / 'index.html').write_text(page.replace('__RECORD__', record).replace('__SOURCE__', '\n'.join(blocks)).replace('__SALES__', sales))
print('Rendered local index.html with', len(blocks), 'ABAP source/test files')
