"""Release-scoped two-snapshot comparison. No deployment or deletion is executed."""
from collections import Counter
from datetime import datetime,timezone
import re
import uuid

from . import __version__
from .snapshot import load_snapshot,parse_manifest,xml,local
from .impact import build_graph,query_graph


def graph_files(snapshot):
    files={}
    for c in snapshot.components.values():
        for path,item in c['files'].items():
            # Metadata-format companions are represented in the graph's source naming convention.
            suffixes={'.flow':'.flow-meta.xml','.permissionset':'.permissionset-meta.xml','.profile':'.profile-meta.xml'}
            target=path
            for old,new in suffixes.items():
                if path.endswith(old): target=path[:-len(old)]+new; break
            files[target]=item
    return files


def component_nodes(graph,component):
    paths=set(component['files'])
    full=component['full_name'].lower();kind=component['type']
    aliases={'CustomObject':'object:'+full,'CustomField':'field:'+full,'ApexClass':'apex:'+full,'ApexTrigger':'apex:'+full,'Flow':'flow:'+full}
    return [n['id'] for n in graph['nodes'] if n['id']==aliases.get(kind) or (n['path'] in paths and n['kind'] in {'apex_class','flow','trigger','permission_metadata','lwc'})]


def regression_notes(before,after):
    notes=[]
    if before and after and before['type'] in {'ApexClass','ApexTrigger'}:
        def methods(c):
            code='\n'.join(text for path,(text,digest) in c['files'].items() if path.endswith(('.cls','.trigger')))
            from .lexer import mask
            return set(re.findall(r'\b(?:public|global)\s+(?:static\s+)?[\w<>.,\[\] ]+?\s+(\w+)\s*\(',mask(code)))
        removed=sorted(methods(before)-methods(after))
        if removed: notes.append('Public/global method names removed or renamed: '+', '.join(removed)+'. Check callers; overload compatibility is not proven.')
    if before and after and before['type'] in {'PermissionSet','Profile'}:
        def entries(c):
            result=set()
            for path,(text,digest) in c['files'].items():
                try: root=xml(text)
                except ValueError: continue
                for e in root:
                    if local(e.tag) in {'fieldPermissions','objectPermissions','classAccesses','userPermissions'}:
                        result.add(tuple((local(x.tag),(x.text or '').strip()) for x in e))
            return result
        if entries(before)-entries(after):
            notes.append('Permission entries changed or omitted. Review possible access reduction; omission is not assumed to revoke a grant during deployment.')
    return notes


def compare_snapshots(candidate_path,destination_path,scope_path,delete_pre=None,delete_post=None):
    candidate=load_snapshot(candidate_path); baseline=load_snapshot(destination_path)
    if candidate.provenance.get('role','source')!='source' or baseline.provenance.get('role','destination')!='destination': raise ValueError('Snapshot source/destination role declarations do not match their comparison positions')
    scope=parse_manifest(scope_path,candidate.namespace) if scope_path else {}
    deletions={}; conflicts={}
    for phase,path in [('pre',delete_pre),('post',delete_post)]:
        if not path: continue
        for key,item in parse_manifest(path,baseline.namespace).items():
            if key in deletions: conflicts[key]='Deletion is declared more than once or in both phases'
            deletions[key]={**item,'phase':phase}
    if not scope and not deletions: raise ValueError('Supply explicit release scope or an explicit deletion manifest')
    if len(scope)+len(deletions)>4000: raise ValueError('Release component limit exceeded')
    for key in scope.keys()&deletions.keys(): conflicts[key]='Component is both a release update and an explicit deletion'
    # Parent-object deletion cannot be mixed with child changes in this release.
    for key,item in deletions.items():
        if item['type']=='CustomObject':
            for other,child in {**scope,**deletions}.items():
                if child['type']=='CustomField' and child['full_name'].startswith(item['full_name']+'.'):
                    conflicts[other]='Child-field intent overlaps a parent-object deletion'
                    conflicts[key]='Parent-object deletion overlaps explicit child-field intent'
    before_graph=build_graph(graph_files(baseline),[])
    rows=[]; merged=dict(baseline.components)
    for key in sorted(scope.keys()|deletions.keys()):
        meta=scope.get(key) or deletions[key]
        old=baseline.components.get(key); new=candidate.components.get(key)
        oldstate=baseline.state(key); newstate=candidate.state(key)
        kind='unknown'; reason=''; notes=[]
        if key in conflicts:
            kind='conflict'; reason=conflicts[key]
        elif candidate.namespace!=baseline.namespace:
            reason='Snapshot namespaces differ; no cross-namespace identity matching is inferred'
        elif key in deletions:
            if oldstate=='present':
                kind='destructive';reason='Explicit '+deletions[key]['phase']+' deletion intent; destination component is present'
                merged.pop(key,None)
                if meta['type']=='CustomObject':
                    for child_key,child in list(merged.items()):
                        if child['type']=='CustomField' and child['full_name'].startswith(meta['full_name']+'.'): merged.pop(child_key)
                    notes.append('Object deletion may also remove child metadata and business data; this tool does not execute or validate a deletion.')
                notes.append('Review incoming references in the before graph; deletion approval and live validation are still required.')
            elif oldstate=='absent': kind='unchanged';reason='Explicit deletion target is already absent in declared destination coverage'
            else: reason='Deletion target presence cannot be established from destination coverage'
        elif newstate!='present':
            reason='Candidate definition is missing, incomplete or unreadable; missing source is not deletion intent'
        elif oldstate=='unknown':
            reason='Destination presence/absence is not established; cannot label this component new'
        elif oldstate=='absent':
            kind='new';reason='Candidate definition is present; destination coverage declares this identity absent';merged[key]=new
        elif old['hash']==new['hash']:
            kind='unchanged';reason='Supported canonical content matches the destination snapshot'
        else:
            kind='modified';reason='Same metadata identity, different supported canonical content';merged[key]=new
            notes.extend(regression_notes(old,new))
        rows.append({'identity':key,**meta,'classification':kind,'reason':reason,'review_notes':notes,
            'deletion_phase':deletions.get(key,{}).get('phase'),'explicit_deletion_intent':key in deletions,
            'candidate_state':newstate,'destination_state':oldstate,'before_hash':old['hash'] if old else None,
            'candidate_hash':new['hash'] if new else None,
            'candidate_files':sorted(new['files']) if new else [],'destination_files':sorted(old['files']) if old else [],
            'before_nodes':component_nodes(before_graph,old) if old else []})
    # Build a review projection: unchanged destination context plus only classified intended changes.
    projected=type(baseline)(baseline.root,components=merged)
    after_graph=build_graph(graph_files(projected),[])
    deleted_ids={node for row in rows if row['classification']=='destructive' for node in row['before_nodes']}
    for n in after_graph['nodes']:
        if n['id'] in deleted_ids and n['kind'] in {'object','field'}: n['explicitly_deleted_in_projection']=True
    for e in after_graph['edges']:
        if e['target'] in deleted_ids:
            e['confidence']='unresolved'
            e['note']+=' Target definition has explicit deletion intent; remaining source references require review.'
    for row in rows:
        component=merged.get(row['identity'])
        row['after_nodes']=component_nodes(after_graph,component) if component else []
        if row['classification']=='destructive':
            slices=[query_graph(before_graph,n,'upstream',2) for n in row['before_nodes'][:5]]
            row['upstream_reference_count']=len({e['id'] for s in slices for e in s['edges']})
            if row['upstream_reference_count']: row['review_notes'].append('Upstream source references exist in the destination baseline; review them before deletion.')
    def signature(e):
        clean=lambda x:re.sub(r'@\d+$','',x)
        return (clean(e['source']),clean(e['target']),e['kind'],e['confidence'],e.get('mode'),e.get('boundary'),e.get('transaction_model'))
    old_edges={signature(e):e for e in before_graph['edges'] if e['kind']!='contains'}
    new_edges={signature(e):e for e in after_graph['edges'] if e['kind']!='contains'}
    untouched=[{'identity':k,'type':c['type'],'full_name':c['full_name']} for k,c in baseline.components.items() if k not in scope and k not in deletions]
    counts=Counter(row['classification'] for row in rows)
    return {'schema_version':'sfg.comparison.v1','id':uuid.uuid4().hex,'tool_version':__version__,
        'created_at':datetime.now(timezone.utc).isoformat(),'kind':'comparison','rows':rows,'effective_user_access_status':'not_assessed',
        'summary':{k:counts[k] for k in ('new','modified','destructive','unchanged','unknown','conflict')},
        'review_status':'incomplete' if counts['unknown'] or counts['conflict'] or candidate.issues or baseline.issues else 'ready_for_human_review',
        'candidate_snapshot':candidate.receipt(),'destination_snapshot':baseline.receipt(),
        'untouched_destination_components':untouched,'before_impact':before_graph,'after_impact':after_graph,
        'relationship_changes':{'added':[new_edges[k] for k in new_edges.keys()-old_edges.keys()],
                                'removed':[old_edges[k] for k in old_edges.keys()-new_edges.keys()]},
        'limitations':['No deployment, validation deployment, deletion, anonymous Apex or record changes are performed.',
            'Absence relies on declared snapshot coverage; neither a missing file nor an incomplete retrieval proves deletion or absence.',
            'The after graph is a source review projection, not a simulation of Salesforce deployment merge semantics or runtime execution.',
            'Baseline-only components outside explicit release/deletion intent are retained as context.',
            'Renames are not inferred. Internal method removals and permission changes remain component modifications with review notes.',
            'Refresh snapshots to check live destination drift before a later deployment. This comparison does not lock an org.']}
