"""Standalone HTML report. All source-derived data is escaped, with no remote assets."""
import html
import json
from pathlib import Path
from .review_scope import review_scope, CSS as SCOPE_CSS
from .rules import OWASP
from .access import access_section
from .visuals import masthead,REPORT_CSS
from .impact_view import section as impact_section, CSS as IMPACT_CSS, JS as IMPACT_JS


def render_html(report):
    esc = lambda value: html.escape(str(value), quote=True)
    counts = report['summary']
    cards = []
    for f in report['findings']:
        impact_button=f'<button type="button" class="inspect-impact" data-finding="{esc(f["id"])}">Inspect impact</button>' if any(f['id'] in n.get('finding_ids',[]) for n in report.get('impact',{}).get('nodes',[])) else '<p class="muted">Dependency mapping is not available for this finding.</p>'
        cards.append(f'''<article class="finding" data-severity="{esc(f['severity'])}" data-category="{esc(f['owasp'])}">
<div class="labels"><span class="pill {esc(f['severity'])}">{esc(f['severity'])}</span><span class="pill">{esc(f['owasp'])}</span><span class="muted">{esc(f['rule'])} · Requires review</span></div>
<h3>{esc(f['title'])}</h3><p class="location">{esc(f['path'])}:{esc(f['line'])}</p>
<pre>{esc(f['evidence'])}</pre><p>{esc(f['detail'])}</p>
<details><summary>Review guidance &amp; context</summary><p>{esc(f['remedy'])}</p><p class="muted">API version: {esc(f.get('api_version') or 'not established')} · {esc(f.get('execution_context') or 'metadata observation')}</p><p class="muted">{esc(f['id'])} · static signal, not a confirmed vulnerability</p></details>{impact_button}</article>''')
    rows = ''.join(f"<tr><td>{esc(c['id'])}</td><td>{esc(c['name'])}</td><td><span class='coverage'>{esc(c['coverage'].replace('_', ' '))}</span></td><td>{c['findings']}</td><td>{esc(c['scope'])}</td></tr>" for c in report['owasp'])
    issues = ''.join(f"<li>{esc(i['path'])}: {esc(i['reason'])}</li>" for i in report['issues']) or '<li>No traversal or parsing errors recorded.</li>'
    sources = ''.join(f"<li><a href='{esc(s['url'])}' rel='noreferrer'>{esc(s['title'])}</a></li>" for s in report['sources'])
    limits = ''.join(f"<li>{esc(s)}</li>" for s in report['limitations'])
    ext = report.get('external_sast', {})
    external_findings = ext.get('findings', [])
    external_rows = ''.join(f"<tr><td>{esc(f.get('rule','unknown'))}</td><td>{esc(f.get('engine',''))}</td><td>{esc(f.get('severity',''))}</td><td>{esc(f.get('message',''))}</td><td class='location'>{esc('; '.join(str(l.get('file','')) + ':' + str(l.get('startLine','')) for l in (f.get('locations') or []) if isinstance(l, dict)))}</td></tr>" for f in external_findings)
    external_table = f"<p>{len(external_findings)} external scanner observations, reported separately from local signals; overlap is possible. All require review. Severity uses Salesforce's scale: 1 critical, 2 high, 3 moderate, 4 low, 5 info.</p><div class='table-wrap'><table><thead><tr><th>Rule</th><th>Engine</th><th>Severity</th><th>Message</th><th>Location</th></tr></thead><tbody>{external_rows}</tbody></table></div>" if external_rows else ''
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Salesforce Guard · Security Review</title><style>
:root{color-scheme:dark;--bg:#0b1120;--panel:#131d30;--border:#28354b;--muted:#a4b3c8;--ink:#edf4ff;--mint:#6ee7c1}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}main{max-width:1180px;margin:auto;padding:42px 24px 64px}.brand{font-size:13px;letter-spacing:.16em;color:var(--mint);font-weight:750}h1{font-size:clamp(32px,5vw,54px);line-height:1.1;margin:14px 0}h2{font-size:23px;margin-top:38px}h3{margin:12px 0 4px;font-size:19px}.intro{color:var(--muted);max-width:780px}.banner{border:1px solid #6e5730;background:#2b2418;padding:14px 18px;border-radius:12px;margin:24px 0}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.metric,.finding,.panel{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:20px}.metric b{display:block;font-size:32px}.metric span,.muted,.location{color:var(--muted)}.toolbar{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}input,select{background:var(--panel);border:1px solid #4c607c;color:var(--ink);padding:12px;border-radius:8px;font:inherit}input{flex:1;min-width:200px}.finding{margin:12px 0}.labels{display:flex;gap:9px;align-items:center;flex-wrap:wrap}.pill{font-size:12px;padding:3px 9px;border:1px solid var(--border);border-radius:20px}.high{background:#49202c;color:#ffb1ba;border-color:#713145}.medium{background:#40351e;color:#f9d88b;border-color:#66552e}.low{background:#173a49;color:#a5d9ee}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#0a1221;border-radius:8px;padding:14px;color:#c7d7eb;font:13px/1.6 ui-monospace,Consolas,monospace}.location{font:13px/1.5 ui-monospace,Consolas,monospace;overflow-wrap:anywhere}summary{cursor:pointer;color:var(--mint)}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:13px 10px;border-bottom:1px solid var(--border);vertical-align:top}th{color:var(--muted);font-weight:600}.table-wrap{overflow:auto}.coverage{white-space:nowrap}a{color:var(--mint)}footer{margin-top:34px;color:var(--muted);font-size:12px}.hash{word-break:break-all}#empty{display:none;color:var(--muted)}[hidden]{display:none!important}@media(max-width:650px){.metrics{grid-template-columns:repeat(2,1fr)}main{padding:28px 16px}th,td{padding:10px 7px}}@media print{body{background:white;color:black}.toolbar{display:none}.finding,.metric,.panel{background:white;color:black;break-inside:avoid}.muted,.location{color:#333}details{display:block}pre{background:#eee;color:black}}
''' + IMPACT_CSS + REPORT_CSS + SCOPE_CSS + '''</style></head><body><main>''' + masthead('Security review · Hermes plugin') + '''<p class="eyebrow">Source. Signals. Something to check.</p>
<h1>Find the risk.<br><em>Show your working.</em></h1>''' + f'''
<p class="intro">Local security review for <strong>{esc(report['project_name'])}</strong>. Evidence first, explicit uncertainty, and no live Salesforce changes.</p>
<div class="banner"><strong>Human review required.</strong> Status: {esc(report['scan_status'].replace('_',' '))}. This is a bounded heuristic scan, not a security certification or a complete OWASP assessment.<br><strong>User access: {esc(report.get('effective_user_access_status','not_assessed').replace('_',' '))}.</strong> Record access and effective execution are not assessed. Declared grants and code modes do not establish runtime authorization.</div>
{review_scope(report)}<section class="metrics" aria-label="Review summary"><div class="metric"><b>{counts['files']}</b><span>Files inventoried</span></div><div class="metric"><b>{counts['findings']}</b><span>Signals to review</span></div><div class="metric"><b>0</b><span>Vulnerabilities confirmed</span></div><div class="metric"><b>{len(report['issues'])}</b><span>Scan gaps recorded</span></div></section>
{'<p><a href="#impact-heading">Explore upstream &amp; downstream impact →</a></p>' if report.get('impact') else ''}
<h2>Security findings</h2><p class="muted" id="visible" aria-live="polite">{counts['findings']} findings</p>
<div class="toolbar"><input id="search" type="search" aria-label="Search findings" placeholder="Search a rule, component or finding…"><select id="severity" aria-label="Filter by severity"><option value="">All severities</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select><select id="category" aria-label="Filter by OWASP category"><option value="">All OWASP categories</option>''' + ''.join(f'<option value="{k}:2025">{k} · {esc(v[0])}</option>' for k,v in OWASP.items()) + f'''</select></div>
<section id="findings">{''.join(cards)}</section><p id="empty">No findings match this filter. This does not establish security.</p>
{impact_section(report['impact']) if report.get('impact') else ''}
{access_section(report)}
<h2>OWASP Top 10:2025 coverage</h2><div class="panel table-wrap"><table><thead><tr><th>Category</th><th>Risk</th><th>Coverage</th><th>Signals</th><th>Scope &amp; limitations</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>External SAST</h2><section class="panel"><strong>Salesforce Code Analyzer: {esc(ext.get('status','not_run'))}</strong><p>{esc(ext.get('reason',''))}</p>{external_table}</section>
<h2>Evidence &amp; limitations</h2><section class="panel"><p class="hash"><strong>Source snapshot:</strong> {esc(report['snapshot_sha256'])}</p><p><strong>Engine:</strong> {esc(report['engine'])} · v{esc(report['tool_version'])}</p><ul>{limits}</ul><h3>Scan gaps</h3><ul>{issues}</ul><details><summary>Source references</summary><ul>{sources}</ul></details></section>
<footer>Report {esc(report['id'])} · {esc(report['created_at'])} · Original source literals are redacted from Apex excerpts. Scan results can still contain sensitive schema names. Keep client reports private.</footer>
</main><script>
const search=document.getElementById('search'),severity=document.getElementById('severity'),category=document.getElementById('category');
function filter(){{let count=0;document.querySelectorAll('.finding').forEach(card=>{{const show=(!severity.value||card.dataset.severity===severity.value)&&(!category.value||card.dataset.category===category.value)&&card.textContent.toLowerCase().includes(search.value.toLowerCase());card.hidden=!show;if(show)count++;}});document.getElementById('visible').textContent=count+' findings shown';document.getElementById('empty').style.display=count?'none':'block';}}
search.addEventListener('input',filter);severity.addEventListener('change',filter);category.addEventListener('change',filter);
</script>''' + ('<script>'+IMPACT_JS+'</script>' if report.get('impact') else '') + '</body></html>'


def save_report(report, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    destination = output / report['id']
    destination.mkdir(exist_ok=False)
    (destination / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (destination / 'report.html').write_text(render_html(report), encoding='utf-8')
    return destination
