"""Local, bounded access evidence and reports. No authentication or org commands."""
from datetime import datetime,timezone
import hashlib
import html
import json
import math
from pathlib import Path
from .review_scope import review_scope, CSS as SCOPE_CSS
import re
import uuid

from .scan import linked
from .visuals import masthead,REPORT_CSS

API_NAME=re.compile(r'[A-Za-z][A-Za-z0-9_]{0,79}')
USER_ID=re.compile(r'005[A-Za-z0-9]{12}(?:[A-Za-z0-9]{3})?')
STATES={'allowed','denied','unknown'}
LIMITATIONS=[
    'Point-in-time, scoped configuration observations for the selected user, who may differ from the connected operator.',
    'Record-level sharing, restriction rules, session/IP/login policy, licensing and actual execution are not assessed.',
    'Object/FLS uses Salesforce computed access responses, not a manual sum of permission grants. Missing or unreadable evidence is unknown.',
    'Apex rows describe configured entry grants only, not effective Apex execution authorization or internal call reachability.',
    'System-mode code can bypass user CRUD/FLS. An allowed row is not proof that code enforces authorization.',
    'Permissions may change during or after collection. No transaction lock or independent signature is provided; evidence files can be edited.',
    'Org IDs, user IDs and schema names are private. Keep evidence and reports out of public repositories and demos.'
]


def scope_from_dict(data):
    if not isinstance(data,dict) or set(data)-{'objects','fields','classes'}: raise ValueError('Unsupported access scope')
    result={k:[] for k in ('objects','fields','classes')}
    for kind in result:
        values=data.get(kind,[])
        if not isinstance(values,list) or len(values)>50: raise ValueError('Access scope limit is 50 per kind')
        for value in values:
            parts=value.split('.') if isinstance(value,str) else []
            if len(parts)!=(2 if kind=='fields' else 1) or not all(API_NAME.fullmatch(p) for p in parts): raise ValueError('Use explicit API names, not queries or wildcards')
            if value in result[kind]: raise ValueError('Duplicate access scope member')
            result[kind].append(value)
    result['objects']=sorted(set(result['objects'])|{v.split('.')[0] for v in result['fields']})
    if len(result['objects'])>50 or sum(map(len,result.values()))>100 or not any(result.values()): raise ValueError('Access scope must contain 1 to 100 entries')
    return result


def _load_json(path,limit=2*1024*1024):
    path=Path(path)
    if any(linked(p) for p in (path,*path.parents) if p.exists()) or path.stat().st_size>limit: raise ValueError('Evidence is linked or oversized')
    with path.open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError('Evidence exceeds its byte limit')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate JSON keys are unsupported')
            result[key]=value
        return result
    def constant(value):raise ValueError('Non-finite JSON numbers are unsupported')
    try:data=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=pairs,parse_constant=constant)
    except (UnicodeError,RecursionError):raise ValueError('Evidence encoding or nesting is unsupported') from None
    stack=[(data,0)];count=0
    while stack:
        node,depth=stack.pop();count+=1
        if depth>64 or count>50000:raise ValueError('Evidence nesting/element limit exceeded')
        if isinstance(node,float) and not math.isfinite(node):raise ValueError('Non-finite JSON numbers are unsupported')
        if isinstance(node,(dict,list)) and len(node)+count>50000:raise ValueError('Evidence element limit exceeded')
        if isinstance(node,dict):stack.extend((v,depth+1) for v in node.values())
        elif isinstance(node,list):stack.extend((v,depth+1) for v in node)
    return data,raw


def load_json(path,limit=2*1024*1024):
    return _load_json(path,limit)[0]


def observation(value,reason):
    return {'status':'allowed' if value is True else 'denied' if value is False else 'unknown','reason':reason}


def combine(*checks):
    if any(c['status']=='denied' for c in checks): return observation(False,'At least one required object/field permission is denied')
    if any(c['status']=='unknown' for c in checks): return observation(None,'Required object/field evidence is incomplete')
    return observation(True,'Both object and field permissions are allowed in the scoped evidence')


def load_evidence(path,now=None):
    data,raw=_load_json(path);now=now or datetime.now(timezone.utc)
    if not isinstance(data,dict) or data.get('schema')!='sfg.access.v1': raise ValueError('Unsupported access evidence schema')
    if not USER_ID.fullmatch(str(data.get('user_id',''))) or not re.fullmatch(r'00D[A-Za-z0-9]{12}(?:[A-Za-z0-9]{3})?',str(data.get('org_id',''))): raise ValueError('Invalid access evidence identity')
    scope=scope_from_dict(data.get('scope'))
    if not isinstance(data.get('role'),str) or data.get('role') not in {'source','destination'} or type(data.get('user_active')) not in {bool,type(None)}: raise ValueError('Invalid access evidence context')
    try:
        stamp=datetime.fromisoformat(data['captured_at'])
        age=(now-stamp).total_seconds()
    except (KeyError,TypeError,ValueError): raise ValueError('Invalid evidence timestamp') from None
    if age< -300 or age>86400: raise ValueError('Access evidence is stale or future-dated; recapture it')
    rows=data.get('rows');expected={({ 'objects':'object','fields':'field','classes':'class'}[k],v) for k,vs in scope.items() for v in vs};seen=set()
    if not isinstance(rows,list) or len(rows)!=len(expected): raise ValueError('Access evidence scope is incomplete')
    clean=[]
    for row in rows:
        if not isinstance(row,dict): raise ValueError('Invalid access row')
        if not isinstance(row.get('kind'),str) or not isinstance(row.get('resource'),str):raise ValueError('Invalid access resource')
        key=(row.get('kind'),row.get('resource'))
        if key not in expected or key in seen: raise ValueError('Access evidence contains duplicate or out-of-scope rows')
        seen.add(key);checks=row.get('checks');required={'read','create','update','delete'} if key[0]=='object' else {'read','create','update'} if key[0]=='field' else {'configured_entry_grant'}
        if not isinstance(checks,dict) or set(checks)!=required: raise ValueError('Access checks do not match resource kind')
        out={}
        for name,c in checks.items():
            if not isinstance(c,dict) or not isinstance(c.get('status'),str) or c.get('status') not in STATES or not isinstance(c.get('reason'),str) or len(c['reason'])>1000: raise ValueError('Invalid access observation')
            out[name]={'status':c['status'],'reason':c['reason']}
        clean.append({'kind':key[0],'resource':key[1],'checks':out})
    # Always re-apply the object gate even to externally supplied evidence.
    objects={r['resource']:r for r in clean if r['kind']=='object'}
    for row in clean:
        if row['kind']=='field':
            obj=objects[row['resource'].split('.')[0]]
            row['checks']={k:combine(v,obj['checks'][k]) for k,v in row['checks'].items()}
        if data['user_active'] is not True:
            row['checks']={k:observation(False if data['user_active'] is False else None,'Selected user is inactive or activity could not be verified') for k in row['checks']}
    counts={s:sum(c['status']==s for r in clean for c in r['checks'].values()) for s in sorted(STATES)}
    return {'schema':'sfg.access.report.v1','id':uuid.uuid4().hex,'org_id':data['org_id'],'user_id':data['user_id'],'role':data['role'],
        'captured_at':data['captured_at'],'scope':scope,'rows':clean,'summary':counts,'status':'partial' if counts['unknown'] else 'scoped_observed',
        'record_access':'not_assessed','effective_execution_access':'not_assessed','limitations':LIMITATIONS,
        'evidence_sha256':hashlib.sha256(raw).hexdigest()}


def render_access(report):
    esc=lambda x:html.escape(str(x),quote=True)
    rows=''.join('<tr><td data-label="Kind">'+esc(r['kind'])+'</td><td data-label="Resource">'+esc(r['resource'])+'</td><td data-label="Check">'+esc(k.replace('_',' '))+'</td><td data-label="Observation" class="'+esc(c['status'])+'">'+esc(c['status'])+'</td><td data-label="Evidence">'+esc(c['reason'])+'</td></tr>' for r in report['rows'] for k,c in r['checks'].items())
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>Salesforce Guard · Access evidence</title><style>body{background:#0b1120;color:#edf4ff;font:16px/1.6 system-ui;margin:0}main{max-width:1100px;margin:auto;padding:28px 18px}h1{font-size:36px}section{background:#131d30;border:1px solid #35445a;border-radius:12px;padding:18px;margin:18px 0}.wrap{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:12px;border-bottom:1px solid #35445a;overflow-wrap:anywhere}.allowed{color:#6ee7c1}.denied{color:#ffb1ba}.unknown{color:#f9d88b}code{overflow-wrap:anywhere}@media(max-width:650px){thead{display:none}table,tbody,tr,td{display:block}tr{border:1px solid #35445a;border-radius:8px;margin:12px 0;padding:12px}td{padding:5px 0;border:0}td::before{content:attr(data-label) ": ";color:#a4b3c8;font-weight:600}}' + REPORT_CSS + SCOPE_CSS + '</style><main>' + masthead('User access · Hermes plugin') + '<p class="eyebrow">The user behind the change</p><h1>Can they read it?<br><em>Can they change it?</em></h1>' + review_scope(report) + '<section class="panel"><strong>'+esc('Evidence incomplete' if report['status']=='partial' else 'Scoped configuration observations')+'</strong><p>'+esc(str(report['summary']['allowed'])+' allowed · '+str(report['summary']['denied'])+' denied · '+str(report['summary']['unknown'])+' unknown')+'</p><p>Object and field configuration is observed. Record access and effective execution authorization are not assessed. Apex results are configured entry grants only.</p><p>Selected user: <code>'+esc(report['user_id'])+'</code> · '+esc(report['role'])+' · Collected '+esc(report['captured_at'])+'</p></section><section class="wrap panel"><table><thead><tr><th>Kind</th><th>Resource</th><th>Check</th><th>Observation</th><th>Evidence / limit</th></tr></thead><tbody>'+rows+'</tbody></table></section><section class="panel"><h2>Scope and limitations</h2><ul>'+''.join('<li>'+esc(x)+'</li>' for x in report['limitations'])+'</ul><p>Evidence SHA-256: <code>'+esc(report['evidence_sha256'])+'</code></p></section></main></html>'


def save_access(report,output):
    parent=Path(output).absolute()
    if any(linked(p) for p in (parent,*parent.parents) if p.exists()):raise ValueError('Access report output must not traverse links')
    dest=parent/report['id'];dest.mkdir(parents=True,exist_ok=False)
    (dest/'access.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (dest/'access.html').write_text(render_access(report),encoding='utf-8')
    return dest


def attach_access(report,path,side=None):
    access=load_evidence(path)
    if side is not None:
        if side not in {'before','after'}:raise ValueError('Invalid comparison access side')
        snapshot=report['destination_snapshot' if side=='before' else 'candidate_snapshot']
        provenance=snapshot.get('provenance',{});role='destination' if side=='before' else 'source'
        if provenance.get('role')!=role or access['role']!=role or not provenance.get('org_id') or provenance['org_id'][:15]!=access['org_id'][:15]:
            raise ValueError('Access evidence does not match the comparison snapshot org and role')
        report.setdefault('user_access',{})[side]=access
    else:report['user_access']={'selected':access}
    report['effective_user_access_status']='scoped_configuration_only'
    report['effective_execution_access']='not_assessed'
    return report


def access_section(report):
    evidence=report.get('user_access',{})
    if not evidence:return ''
    esc=lambda x:html.escape(str(x),quote=True)
    content='<h2>Selected-user access evidence</h2><section class="panel"><p>Scoped configuration observations only. Record-level access and effective execution remain unassessed. System-mode code may bypass user CRUD/FLS.</p>'
    content+='<p>'+('Evidence org and role matched the captured snapshot provenance.' if report.get('kind')=='comparison' else 'Local source-to-org identity is not independently verified; this is selected-user context only.')+'</p>'
    for side,access in evidence.items():
        content+='<h3>'+esc(side)+' · '+esc(access['role'])+'</h3><p>Selected user: '+esc(access['user_id'])+' · '+esc(access['captured_at'])+'</p><div class="table-wrap"><table><thead><tr><th>Resource</th><th>Check</th><th>Observation</th></tr></thead><tbody>'
        content+=''.join('<tr><td>'+esc(r['resource'])+'</td><td>'+esc(k.replace('_',' '))+'</td><td>'+esc(c['status'])+'</td></tr>' for r in access['rows'] for k,c in r['checks'].items())+'</tbody></table></div>'
    return content+'</section>'
