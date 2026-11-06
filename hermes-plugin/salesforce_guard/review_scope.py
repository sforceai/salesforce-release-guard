"""A concise, escaped coverage summary; no live checks or approval decisions."""
import html

CSS = '''.review-scope{margin:24px 0}.review-scope h2{margin:0 0 12px}.scope-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px 24px;margin:18px 0}.scope-grid div{min-width:0}.scope-grid dt{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:var(--muted,#536959)}.scope-grid dd{margin:4px 0;overflow-wrap:anywhere}.review-scope .scope-next{border-left:3px solid #668047;padding-left:12px}@media(max-width:650px){.scope-grid{grid-template-columns:1fr}}'''


def review_scope(report):
    entries = []
    comparison = report.get('kind') == 'comparison'
    access_only = report.get('schema') == 'sfg.access.report.v1'
    if comparison:
        for key, label in (('candidate_snapshot', 'Proposed source'), ('destination_snapshot', 'Existing destination')):
            snap = report.get(key, {})
            stamp = snap.get('provenance', {}).get('captured_at') or 'capture time not supplied'
            entries.append((label, f"{snap.get('components', 0)} supplied components; {stamp}"))
        entries.append(('Release scope', f"{len(report.get('rows', []))} reviewed components; {len(report.get('untouched_destination_components', []))} retained destination components as context"))
    elif not access_only:
        entries.append(('Source reviewed', f"{report.get('summary', {}).get('files', 0)} inventoried files; {len(report.get('issues', []))} recorded scan gaps"))
    access = {'selected user': report} if access_only else report.get('user_access', {})
    if not access:
        entries.append(('Selected-user access', 'Not assessed — no selected-user access evidence is attached.'))
    else:
        for side, evidence in access.items():
            counts = evidence.get('summary', {})
            entries.append((f'Access evidence — {side}', f"User {evidence.get('user_id', 'not supplied')}; role {evidence.get('role', 'not supplied')}; captured {evidence.get('captured_at', 'not supplied')}; {counts.get('unknown', 0)} unknown checks"))
    if not access_only:
        entries.append(('Dependency coverage', 'Supplied source only. Zero references found does not prove that the whole org has no callers. Missing source and dynamic relationships can hide dependencies.'))
    entries.append(('Not assessed', 'Record-level sharing, effective execution authorization and current live-org drift. Static references do not prove runtime execution.'))
    entries.append(('Evidence timing', 'Point-in-time, user-supplied evidence. Capture timestamps are not independently attested and may be absent. Refresh inputs before a later release decision.'))
    if comparison and report.get('review_status') == 'incomplete':
        next_step = 'Resolve unknown/conflicting inputs and capture gaps before making a release decision.'
    elif comparison and report.get('summary', {}).get('destructive'):
        next_step = 'Inspect the destination-before callers of each removal. Collect missing source/access context and refresh the destination before approving a deployment.'
    else:
        next_step = 'Inspect the evidence and gaps. Collect selected-user context where needed; an allowed row or empty finding list is not deployment approval.'
    esc = lambda value: html.escape(str(value), quote=True)
    rows = ''.join(f'<div><dt>{esc(label)}</dt><dd>{esc(value)}</dd></div>' for label, value in entries)
    return '<section class="panel review-scope" aria-label="What was checked"><h2>What was actually checked?</h2><p><strong>Human review only. This report does not approve a deployment.</strong></p><dl class="scope-grid">' + rows + '</dl><p class="scope-next"><strong>Next step:</strong> ' + esc(next_step) + '</p><p class="muted">When used through Hermes, requested source excerpts and evidence are shared with your selected AI provider.</p></section>'
