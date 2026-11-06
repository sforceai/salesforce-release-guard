"""Local comparison report, reusing the evidence-first impact explorer."""
import html
import json
from pathlib import Path
from .access import access_section
from .impact_view import section,CSS,JS
from .visuals import masthead,REPORT_CSS
from .review_scope import review_scope, CSS as SCOPE_CSS


def release_hero(report):
    esc=lambda value:html.escape(str(value),quote=True)
    removals=[(i,r) for i,r in enumerate(report['rows']) if r['classification']=='destructive']
    if removals:
        i,row=max(removals,key=lambda item:item[1].get('upstream_reference_count',0))
        count=row.get('upstream_reference_count',0)
        if type(count) is not int or count<0:count=0
        card=f'<aside class="review-card"><p class="eyebrow">Look here before removal</p><div class="component-name">{esc(row["full_name"])}</div><div class="reference-score"><b>{count}</b><span>upstream source references<br>in the destination snapshot</span></div><p>Within captured source only. Zero does not establish no org-wide callers; references are not a prediction of runtime failure.</p><button class="change-focus" data-row="{i}" type="button">Trace this dependency →</button></aside>'
    else:
        card='<aside class="review-card"><p class="eyebrow">Deletion stays deliberate</p><div class="component-name">No explicit removals</div><p>A missing file is not deletion intent. Review the scoped changes below.</p></aside>'
    return '<div class="hero-grid"><div><p class="eyebrow">The release review desk</p><h1>Before you ship.<br><em>Follow the impact.</em></h1><p class="intro">One change can reach beyond your release. See what changed, who references it, and the evidence worth checking.</p></div>'+card+'</div>'


def render_comparison(report):
    esc=lambda x:html.escape(str(x),quote=True)
    data=json.dumps({'before':report['before_impact'],'after':report['after_impact'],'rows':report['rows']},ensure_ascii=True).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    rows=[]
    for i,row in enumerate(report['rows']):
        notes=''.join('<li>'+esc(n)+'</li>' for n in row['review_notes'])
        rows.append(f'''<tr data-change="{esc(row['classification'])}"><td>{esc(row['type'])}<br><strong>{esc(row['full_name'])}</strong></td><td><span class="badge">{esc(row['classification'])}</span></td><td>{esc(row['reason'])}<ul>{notes}</ul></td><td>{esc(row['deletion_phase'] or '—')}</td><td><button type="button" class="change-focus" data-row="{i}">Inspect impact</button><details><summary>Snapshot evidence</summary><p>Candidate: {esc(row['candidate_state'])}<br>Destination: {esc(row['destination_state'])}<br>Explicit deletion intent: {esc(row['explicit_deletion_intent'])}</p><p class="hash">Before: {esc(row['before_hash'] or 'not established')}<br>Candidate: {esc(row['candidate_hash'] or 'not supplied')}</p></details></td></tr>''')
    metrics=''.join(f'<div class="metric"><b>{v}</b><span>{esc(k)}</span></div>' for k,v in report['summary'].items())
    limits=''.join('<li>'+esc(x)+'</li>' for x in report['limitations'])
    issues=''.join('<li>'+esc(x)+'</li>' for s in ('candidate_snapshot','destination_snapshot') for x in report[s]['issues']) or '<li>No snapshot traversal/parsing issues recorded.</li>'
    receipt=json.dumps({'candidate':report['candidate_snapshot'],'destination':report['destination_snapshot']},indent=2)
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>Salesforce Guard · Snapshot comparison</title><style>
:root{color-scheme:dark;--bg:#0b1120;--panel:#131d30;--border:#28354b;--muted:#a4b3c8;--ink:#edf4ff}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui}main{max-width:1240px;margin:auto;padding:40px 24px}h1{font-size:44px;line-height:1.15}h2{margin-top:36px}h3{font-size:18px}.brand,a,summary{color:#6ee7c1}.brand{letter-spacing:.14em;font-size:12px}.muted,.location{color:var(--muted)}.banner{background:#2b2418;border:1px solid #6e5730;border-radius:10px;padding:16px}.metrics{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin:24px 0}.metric,.panel{padding:18px;background:var(--panel);border:1px solid var(--border);border-radius:12px}.metric b{display:block;font-size:28px}.metric span{color:var(--muted)}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:13px 9px;border-bottom:1px solid var(--border);vertical-align:top}.table-wrap{overflow:auto}button,select{background:#18283e;color:var(--ink);border:1px solid #4c607c;border-radius:7px;padding:10px;font:inherit;cursor:pointer}button:focus-visible,select:focus-visible{outline:2px solid #6ee7c1}summary{cursor:pointer}.toolbar{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}.hash,pre{overflow-wrap:anywhere;white-space:pre-wrap;font:12px/1.7 monospace}pre{background:#0a1221;padding:16px;border-radius:8px}.badge{display:inline-block;border:1px solid #4c607c;border-radius:20px;padding:3px 9px}tr[data-change=destructive] .badge{color:#ffb1ba;border-color:#713145}tr[data-change=unknown] .badge,tr[data-change=conflict] .badge{color:#f9d88b}footer{font-size:12px;color:var(--muted);margin:28px 0}[hidden]{display:none!important}@media(max-width:650px){main{padding:26px 16px}.metrics{grid-template-columns:repeat(3,1fr)}h1{font-size:34px}}
''' + CSS + REPORT_CSS + SCOPE_CSS + '''</style></head><body><main>''' + masthead('Release review · Hermes plugin') + release_hero(report) + review_scope(report) + f'''
<p>Compare a proposed release with an existing destination snapshot. Component identity uses metadata type, full name and declared namespace.</p><div class="banner"><strong>{esc(report['review_status'].replace('_',' '))}.</strong> Missing source is never treated as deletion intent. This is a review, not a deployment.<br><strong>User access: {esc(report.get("effective_user_access_status","not_assessed").replace("_"," "))}.</strong> Record access and effective execution are not assessed. Sign-in does not prove authorization.</div><section class="metrics">{metrics}</section>
<h2>Release changes</h2><label>Filter changes <select id="change-filter"><option value="">All changes</option>{''.join('<option>'+k+'</option>' for k in report['summary'])}</select></label><p class="muted">{len(report['untouched_destination_components'])} destination components outside release scope retained as context. {len(report['relationship_changes']['added'])} added and {len(report['relationship_changes']['removed'])} removed static relationships.</p><div class="panel table-wrap"><table><thead><tr><th>Component</th><th>Classification</th><th>Reason &amp; review notes</th><th>Deletion phase</th><th>Inspect</th></tr></thead><tbody id="change-rows">{''.join(rows)}</tbody></table></div>
<h2>Before / proposed-after impact</h2><p class="muted">Unknown/conflicting changes are not applied to the after projection. It does not simulate deployment merge semantics.</p><div class="toolbar"><label>Graph <select id="comparison-side"><option value="before">Destination before</option><option value="after" selected>Proposed-after source projection</option></select></label><span id="comparison-selection" class="muted">Select a change to focus its impact. Deletion reviews open the before graph.</span></div>
{section(report['after_impact'])}{access_section(report)}<h2>Coverage and evidence</h2><section class="panel"><ul>{issues}</ul><ul>{limits}</ul><details><summary>Snapshot provenance and hashes</summary><pre>{esc(receipt)}</pre></details></section><footer>Report {esc(report['id'])} · {esc(report['created_at'])} · v{esc(report['tool_version'])}. Keep real customer snapshots and reports private.</footer></main><script type="application/json" id="comparison-data">{data}</script><script>''' + JS + r'''
const comparisonData=JSON.parse(document.getElementById('comparison-data').textContent);const side=document.getElementById('comparison-side');let selectedChange=null;
function switchGraph(){const g=comparisonData[side.value];Object.assign(impactGraph,g);impactNodes.clear();g.nodes.forEach(n=>impactNodes.set(n.id,n));impactFocus.replaceChildren();g.nodes.filter(n=>!['unresolved','external_flow'].includes(n.kind)).sort((a,b)=>a.label.localeCompare(b.label)).forEach(n=>{const option=document.createElement('option');option.value=n.id;option.textContent=n.label+' · '+words(n.kind);impactFocus.appendChild(option);});let nodes=selectedChange?(side.value==='before'?selectedChange.before_nodes:selectedChange.after_nodes):[];const target=nodes.find(id=>impactNodes.has(id));impactFocus.value=selectedChange?(target||''):(impactFocus.options[0]?.value||'');showImpact();if(selectedChange&&!target){document.getElementById('comparison-selection').textContent=selectedChange.full_name+' has no supported component definition on this side. Select the other side or review snapshot evidence.';}else if(selectedChange){document.getElementById('comparison-selection').textContent=selectedChange.full_name+' · '+selectedChange.classification+' · '+(side.value==='before'?'destination before':'proposed source projection');}}
side.addEventListener('change',switchGraph);document.querySelectorAll('.change-focus').forEach(button=>button.addEventListener('click',()=>{selectedChange=comparisonData.rows[Number(button.dataset.row)];side.value=selectedChange.classification==='destructive'?'before':'after';switchGraph();document.getElementById('impact-heading').scrollIntoView({behavior:'smooth'});}));document.getElementById('change-filter').addEventListener('change',event=>document.querySelectorAll('#change-rows tr').forEach(row=>row.hidden=!!event.target.value&&row.dataset.change!==event.target.value));
</script></body></html>'''


def save_comparison(report,output):
    destination=Path(output)/report['id']; destination.mkdir(parents=True,exist_ok=False)
    (destination/'comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (destination/'comparison.html').write_text(render_comparison(report),encoding='utf-8')
    return destination
