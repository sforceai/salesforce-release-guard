"""Bounded source dependency graph, not a compiler, execution trace or access proof.

Every relationship carries source evidence and a relation-specific confidence.
Only supplied source is used. Dynamic dispatch is reported as unresolved.
"""
from collections import defaultdict, deque
import hashlib
import re
import xml.etree.ElementTree as ET

from .lexer import mask, line_at, safe_excerpt

MAX_NODES = 2500
MAX_EDGES = 6000
MAX_QUERY_NODES = 120
PLATFORM = {'system', 'database', 'schema', 'featuremanagement', 'math', 'date', 'datetime', 'crypto',
            'json', 'messaging', 'userinfo', 'string', 'integer', 'decimal', 'test', 'limits', 'url', 'blob'}


def build_graph(files, findings):
    nodes, edges, gaps = {}, {}, []
    classes, methods, flows, writes = {}, defaultdict(list), [], []

    def gap(path, line, reason, component=None):
        if len(gaps) < 500:
            entry = {'path': path, 'line': line, 'reason': reason, 'component': component}
            if entry not in gaps: gaps.append(entry)

    def node(identity, label, kind, path='', line=1, **data):
        if identity in nodes and nodes[identity]['kind']=='external_flow' and kind=='flow':
            nodes[identity].update(label=label,kind=kind,path=path,line=line,**data)
        if identity not in nodes:
            if len(nodes) >= MAX_NODES:
                gap(path, line, 'Graph node limit reached; relationships omitted.')
                return None
            nodes[identity] = {'id': identity, 'label': label, 'kind': kind, 'path': path, 'line': line, **data}
        return identity

    def edge(source, target, kind, path, text, pos=0, confidence='explicit_reference', note='', **data):
        if not source or not target or source not in nodes or target not in nodes: return
        if len(edges) >= MAX_EDGES:
            gap(path, line_at(text, pos), 'Graph relationship limit reached; relationships omitted.')
            return
        line = line_at(text, pos)
        identity = hashlib.sha256(f'{source}|{target}|{kind}|{path}|{line}|{note}'.encode()).hexdigest()[:16]
        edges[identity] = {'id': identity, 'source': source, 'target': target, 'kind': kind,
            'confidence': confidence, 'note': note, 'evidence': {'path': path, 'line': line,
                'excerpt': safe_excerpt(text, line) if path.endswith(('.cls', '.trigger')) else 'Source metadata/import reference'}, **data}

    def external(label, path, line, reason):
        identity = 'unresolved:' + hashlib.sha256(f'{path}:{label}'.encode()).hexdigest()[:16]
        node(identity, label, 'unresolved', path, line)
        gap(path, line, reason, identity)
        return identity

    def object_node(name):
        return node('object:' + name.lower(), name, 'object', definition_available=False)

    def parse_xml(path, text):
        if re.search(r'<!\s*(DOCTYPE|ENTITY)\b', text, re.I):
            gap(path, 1, 'DTD/entity metadata is not parsed.')
            return None
        try: return ET.fromstring(text)
        except ET.ParseError:
            gap(path, 1, 'Metadata could not be parsed for impact analysis.')
            return None

    def child(e, tag):
        return next((c for c in e if c.tag.rsplit('}', 1)[-1] == tag), None)

    def value(e, tag):
        c = child(e, tag)
        return (c.text or '').strip() if c is not None else ''

    def meta_pos(text, name):
        return max(0, text.find(name))

    # Pair braces in comment/string-masked source, then locate method declarations at class depth.
    for path, (text, digest) in sorted(files.items()):
        if not path.endswith(('.cls', '.trigger')): continue
        if len(nodes)>=MAX_NODES:
            gap(path,1,'Graph node limit reached; source dependencies omitted.'); continue
        code = mask(text)
        if re.search(r'@isTest\b', code, re.I): continue
        pairs, stack = {}, []
        for i, c in enumerate(code):
            if c == '{': stack.append(i)
            elif c == '}' and stack: pairs[stack.pop()] = i
        if stack or code.count('}') != len(pairs): gap(path, 1, 'Unbalanced source braces; graph is partial.')
        is_trigger = path.endswith('.trigger')
        match = re.search(r'\b(?:trigger|class|interface)\s+(\w+)', code, re.I)
        if not match:
            gap(path, 1, 'No supported Apex declaration found.'); continue
        name = match.group(1)
        key = name.lower()
        if key in classes:
            gap(path, line_at(text, match.start()), 'Duplicate class name; calls to this type remain unresolved.')
            classes[key]['ambiguous'] = True
            continue
        identity = 'apex:' + key
        api = None
        metadata = files.get(path + '-meta.xml')
        if metadata:
            tree = parse_xml(path + '-meta.xml', metadata[0])
            if tree is not None:
                for e in tree.iter():
                    if e.tag.rsplit('}', 1)[-1] == 'apiVersion': api = (e.text or '').strip()
        sharing = re.search(r'\b(without\s+sharing|with\s+sharing|inherited\s+sharing)\b', code[:match.end()], re.I)
        info = {'name': name, 'id': identity, 'path': path, 'text': text, 'code': code,
                'api_version': api, 'sharing': sharing.group().lower() if sharing else 'not_declared', 'trigger': is_trigger}
        classes[key] = info
        node(identity, name, 'trigger' if is_trigger else 'apex_class', path, line_at(text, match.start()),
             api_version=api, sharing=info['sharing'])
        opening = code.find('{', match.end())
        closing = pairs.get(opening, len(code))
        depth = 0
        depths = []
        for c in code:
            depths.append(depth)
            if c == '{': depth += 1
            elif c == '}': depth -= 1
        if is_trigger:
            info['members'] = [{'id': identity, 'name': name, 'arity': 0, 'start': opening + 1,
                'end': closing, 'params': '', 'entry_points': ['trigger']}]
            continue
        members = []
        for m in re.finditer(r'\b(\w+)\s*\(([^{};()]*)\)\s*\{', code):
            if len(nodes)>=MAX_NODES:
                gap(path,1,'Graph node limit reached; method declarations omitted.'); break
            if not (opening < m.start() < closing) or depths[m.start()] != depths[opening] + 1: continue
            if m.group(1).lower() in {'if', 'for', 'while', 'switch', 'catch'}: continue
            end = pairs.get(m.end() - 1)
            if end is None: continue
            parameters = m.group(2)
            arity = _arity(parameters)
            mid = f'method:{key}.{m.group(1).lower()}/{arity}@{line_at(text,m.start())}'
            prefix = code[max(opening, max(code.rfind('}', opening, m.start()), code.rfind(';', opening, m.start()))):m.start()]
            entries = [a for a in ('AuraEnabled', 'InvocableMethod', 'RestResource', 'HttpGet', 'HttpPost', 'HttpPatch', 'HttpDelete', 'future') if re.search(r'@' + a + r'\b', prefix, re.I)]
            node(mid, name + '.' + m.group(1) + f'/{arity}', 'apex_method', path, line_at(text, m.start()),
                 api_version=api, sharing=info['sharing'], entry_points=entries,owner=identity)
            member = {'id': mid, 'name': m.group(1), 'arity': arity, 'start': m.end(), 'end': end,
                      'params': parameters, 'entry_points': entries}
            members.append(member)
            methods[(key, m.group(1).lower())].append(member)
            edge(identity, mid, 'contains', path, text, m.start(), note='Source containment, not an execution step.')
        info['members'] = members
        if re.search(r'\bclass\s+\w+', code[opening + 1:closing], re.I):
            gap(path, line_at(text, opening), 'Nested Apex types are not resolved; their methods are outside this graph.')
        if not members: gap(path, line_at(text, opening), 'No supported method bodies; property/initializer paths are not analysed.')

    def resolve_method(type_name, method_name, arity=None):
        info = classes.get(type_name.lower())
        if not info or info.get('ambiguous'): return None
        candidates = methods.get((type_name.lower(), method_name.lower()), [])
        if arity is not None: candidates = [m for m in candidates if m['arity'] == arity]
        return candidates[0]['id'] if len(candidates) == 1 else None

    for info in classes.values():
        path, text, code = info['path'], info['text'], info['code']
        for member in info.get('members', []):
            if len(edges)>=MAX_EDGES:
                gap(path,1,'Graph relationship limit reached; remaining method dependencies omitted.'); break
            source, start = member['id'], member['start']
            body = code[start:member['end']]
            types = _types(member['params'] + ';' + body)
            parentheses={}; pending=[]
            for index,char in enumerate(body):
                if char=='(': pending.append(index)
                elif char==')' and pending: parentheses[pending.pop()]=index
            for m in re.finditer(r'\b(?:System\s*\.\s*|Database\s*\.\s*)?(enqueueJob|executeBatch|schedule|scheduleBatch)\s*\(', body, re.I):
                end=parentheses.get(m.end()-1)
                arguments=body[m.end():end] if end is not None else ''
                new_type=re.search(r'\bnew\s+(\w+)\s*\(',arguments)
                owner=new_type.group(1) if new_type else types.get(arguments.strip(),'Unresolved asynchronous job')
                target = resolve_method(owner, 'execute')
                if not target:
                    target = external(owner + '.execute', path, line_at(text, start+m.start()), 'Async target execute method is absent or ambiguous.')
                edge(source, target, 'enqueues' if m.group(1).lower() == 'enqueuejob' else 'schedules', path, text, start+m.start(),
                     confidence='explicit_reference' if not target.startswith('unresolved:') else 'unresolved', boundary='asynchronous', note='New execution boundary; principal and authorisation require verification.')
            for m in re.finditer(r'\b(?:(\w+)\s*\.\s*)?(\w+)\s*\(', body):
                if len(edges)>=MAX_EDGES:
                    gap(path,1,'Graph relationship limit reached; calls omitted.'); break
                receiver, name = m.group(1), m.group(2)
                if name.lower() in {'if','for','while','catch','switch','return','new','enqueuejob','executebatch','schedule','schedulebatch'}: continue
                if body[max(0,m.start()-5):m.start()].strip().endswith('new'): continue
                if receiver and receiver.lower() in PLATFORM: continue
                if receiver == 'Type' and name.lower() == 'forname':
                    target = external('Dynamic Apex target', path, line_at(text,start+m.start()), 'Type.forName dispatch is not statically resolved.')
                    edge(source,target,'dynamic_call',path,text,start+m.start(),confidence='unresolved'); continue
                owner = info['name'] if not receiver or receiver.lower() in {'this','super'} else types.get(receiver, receiver)
                if receiver and receiver.lower() == 'super':
                    target = None
                else:
                    end = parentheses.get(m.end()-1)
                    target = resolve_method(owner,name,_arity(body[m.end():end])) if end is not None else None
                if target:
                    boundary='asynchronous' if 'future' in nodes.get(target,{}).get('entry_points',[]) else 'not_established'
                    edge(source,target,'calls',path,text,start+m.start(),boundary=boundary,note='Static call reference; path feasibility and control checks are not proven.')
                elif receiver or (owner.lower(),name.lower()) in methods:
                    target = external(owner+'.'+name,path,line_at(text,start+m.start()),'Receiver type, overload, inheritance or external implementation not resolved.')
                    edge(source,target,'calls',path,text,start+m.start(),confidence='unresolved')
            for m in re.finditer(r'\[\s*SELECT\b[^\]]*\]',body,re.I):
                query=m.group()
                refs=list(re.finditer(r'\bFROM\s+(\w+)',query,re.I))
                for ref in refs:
                    obj=object_node(ref.group(1))
                    edge(source,obj,'reads',path,text,start+m.start(),mode=_mode(query,info),note='Object reference in static SOQL; record/field access is not proven.')
                if len(refs)==1:
                    selection=re.search(r'\bSELECT\s+(.*?)\s+FROM\b',query,re.I|re.S)
                    if selection:
                        for field in selection.group(1).split(','):
                            field=field.strip()
                            if re.fullmatch(r'\w+',field):
                                fid=node('field:'+refs[0].group(1).lower()+'.'+field.lower(),refs[0].group(1)+'.'+field,'field')
                                edge(source,fid,'reads_field',path,text,start+m.start(),mode=_mode(query,info))
                else: gap(path,line_at(text,start+m.start()),'Nested relationship query: field ownership is not resolved.',source)
            for m in re.finditer(r'\b(insert|update|upsert|delete|undelete)\s+(?:(?:as\s+(?:user|system))\s+)?(?:new\s+)?(\w+)\b|\bDatabase\s*\.\s*(insert|update|upsert|delete|undelete)\s*\(\s*(\w+)',body,re.I):
                operation, variable = (m.group(1),m.group(2)) if m.group(1) else (m.group(3),m.group(4))
                obj_name=types.get(variable,variable if variable.endswith('__c') else None)
                end=body.find(';',m.end())
                statement=body[m.start():end if end>=0 else m.end()]
                if obj_name:
                    target=object_node(obj_name)
                    edge(source,target,'writes',path,text,start+m.start(),operation=operation.lower(),mode=_mode(statement,info),note='DML target inferred from a local declared type; runtime effects require verification.')
                    writes.append((source,obj_name,operation.lower(),path,text,start+m.start()))
                else:
                    target=external('DML target: '+variable,path,line_at(text,start+m.start()),'DML target type is not resolved.')
                    edge(source,target,'writes',path,text,start+m.start(),confidence='unresolved',operation=operation.lower())
            if re.search(r'\bDatabase\s*\.\s*(?:query|queryWithBinds)\s*\(',body,re.I):
                gap(path,line_at(text,start),'Dynamic SOQL object/field dependencies are not resolved.',source)

    # Flow elements are first-class nodes: connector and fault paths stay distinct.
    for path,(text,digest) in sorted(files.items()):
        if not path.endswith('.flow-meta.xml'): continue
        if len(nodes)>=MAX_NODES:
            gap(path,1,'Graph node limit reached; Flow dependencies omitted.'); continue
        tree=parse_xml(path,text)
        if tree is None: continue
        name=path.rsplit('/',1)[-1].removesuffix('.flow-meta.xml')
        fid=node('flow:'+name.lower(),name,'flow',path,declared_mode=value(tree,'runInMode') or 'not_declared',declared_status=value(tree,'status') or 'unknown')
        elements={}
        for e in tree:
            tag=e.tag.rsplit('}',1)[-1]
            ename='start' if tag=='start' else value(e,'name')
            if not ename: continue
            if tag in {'variables','formulas','constants','choices','dynamicChoiceSets','textTemplates'}: continue
            eid=node(fid+'#'+ename,ename,'flow_element',path,line_at(text,meta_pos(text,ename)),element_type=tag)
            if not eid:
                gap(path,1,'Graph node limit reached; remaining Flow elements omitted.'); break
            elements[ename]=(eid,e,tag)
            edge(fid,eid,'contains',path,text,meta_pos(text,ename),note='Flow containment, not an execution step.')
        start_entry=elements.get('start')
        if start_entry:
            edge(fid,start_entry[0],'starts',path,text,meta_pos(text,'<start>'))
            flows.append((fid,value(start_entry[1],'object'),value(start_entry[1],'recordTriggerType'),value(tree,'status'),path))
        lookup_objects={value(e,'name'):value(e,'object') for e in tree if e.tag.rsplit('}',1)[-1]=='recordLookups'}
        for ename,(eid,e,tag) in elements.items():
            pos=meta_pos(text,ename)
            for connector in e.iter():
                ctag=connector.tag.rsplit('}',1)[-1]
                if ctag not in {'connector','faultConnector','defaultConnector'}: continue
                target_name=value(connector,'targetReference')
                if not target_name: continue
                target=elements.get(target_name,(None,))[0]
                if not target: target=external(target_name,path,line_at(text,pos),'Flow connector target missing from supplied metadata.')
                scheduled=any(connector is nested for scheduled in e if scheduled.tag.rsplit('}',1)[-1]=='scheduledPaths' for nested in scheduled.iter())
                edge(eid,target,'fault' if ctag=='faultConnector' else 'schedules' if scheduled else 'branches' if tag=='decisions' else 'next',path,text,pos,
                     confidence='conditional' if tag=='decisions' or scheduled else 'explicit_reference',
                     boundary='scheduled_transaction' if scheduled else 'same_flow',note='Connector exists; runtime conditions and active org version are not verified.')
            if tag=='actionCalls' and value(e,'actionType').lower()=='apex':
                owner=value(e,'actionName')
                invocables=[m for m in classes.get(owner.lower(),{}).get('members',[]) if 'InvocableMethod' in m.get('entry_points',[])]
                target=invocables[0]['id'] if len(invocables)==1 else None
                if not target: target=external(owner,path,line_at(text,pos),'Invocable target absent or ambiguous.')
                edge(eid,target,'invokes_apex',path,text,pos,confidence='explicit_reference' if not target.startswith('unresolved:') else 'unresolved',
                     transaction_model=value(e,'flowTransactionModel') or 'not_declared')
            if tag=='subflows':
                target_name=value(e,'flowName')
                if not target_name:
                    gap(path,line_at(text,pos),'Subflow has no target name.',eid); continue
                target='flow:'+target_name.lower()
                if target not in nodes: node(target,target_name,'external_flow',path,line_at(text,pos))
                edge(eid,target,'calls_subflow',path,text,pos,confidence='explicit_reference' if nodes[target]['kind']=='flow' else 'unresolved')
            if tag in {'recordCreates','recordUpdates','recordDeletes','recordLookups'}:
                obj=value(e,'object') or lookup_objects.get(value(e,'inputReference'))
                operation={'recordCreates':'insert','recordUpdates':'update','recordDeletes':'delete','recordLookups':'read'}[tag]
                if obj:
                    edge(eid,object_node(obj),'reads' if operation=='read' else 'writes',path,text,pos,operation=operation,note='Metadata target; access mode and downstream criteria require review.')
                    if operation!='read': writes.append((eid,obj,operation,path,text,pos))
                else:
                    gap(path,line_at(text,pos),'Flow record variable target object is not resolved.',eid)

    # Resolve subflow targets after all Flow declarations have been indexed.
    for n in nodes.values():
        if n['kind']=='external_flow': gap(n['path'],n['line'],'Subflow source is not supplied.',n['id'])
    for e in edges.values():
        if e['kind']=='calls_subflow' and nodes[e['target']]['kind']=='flow':
            e['confidence']='explicit_reference'
    for source,obj,operation,path,text,pos in writes:
        events={'insert':{'Create','CreateAndUpdate'},'update':{'Update','CreateAndUpdate'},'upsert':{'Create','Update','CreateAndUpdate'},'delete':{'Delete'}}.get(operation,set())
        for fid,flow_obj,event,status,flow_path in flows:
            if obj.lower()==flow_obj.lower() and event in events and status=='Active':
                edge(source,fid,'may_activate',path,text,pos,confidence='conditional',note='Object/event match only. Entry filters, prior values, deployed activation and transaction order are not evaluated.',target_evidence={'path':flow_path,'element':'start'})

    for path,(text,digest) in sorted(files.items()):
        if path.endswith(('.permissionset-meta.xml','.profile-meta.xml')):
            tree=parse_xml(path,text)
            if tree is None: continue
            name=path.rsplit('/',1)[-1].split('.')[0]
            pid=node('permission:'+path,name,'permission_metadata',path)
            for e in tree:
                tag=e.tag.rsplit('}',1)[-1]
                if tag=='classAccesses' and value(e,'enabled')=='true':
                    owner=value(e,'apexClass'); target=classes.get(owner.lower(),{}).get('id')
                    if not target: target=external(owner,path,1,'Granted Apex class source not supplied.')
                    edge(pid,target,'grants_class_access',path,text,meta_pos(text,owner),note='Metadata grant only; assignments and effective user access are unknown.')
                if tag=='fieldPermissions' and (value(e,'readable')=='true' or value(e,'editable')=='true'):
                    field=value(e,'field'); target=node('field:'+field.lower(),field,'field')
                    edge(pid,target,'grants_field_access',path,text,meta_pos(text,field),readable=value(e,'readable')=='true',editable=value(e,'editable')=='true',note='Grant only; profile/group/muting/assignment effects are not evaluated.')
        elif '/lwc/' in path.replace('\\','/') and path.endswith('.js'):
            name=path.rsplit('/',2)[-2]; lid=node('lwc:'+name,name,'lwc',path)
            for m in re.finditer(r'^\s*import\s+[^;\n]+?\s+from\s+[\'\"]@salesforce/apex/(\w+)\.(\w+)[\'\"]',mask(text,strings=False),re.M):
                target=resolve_method(m.group(1),m.group(2))
                if not target: target=external(m.group(1)+'.'+m.group(2),path,line_at(text,m.start()),'Imported Apex target absent or overloaded.')
                edge(lid,target,'imports_apex',path,text,m.start(),confidence='explicit_reference' if not target.startswith('unresolved:') else 'unresolved',note='Import reference only; invocation and end-user authorisation are not proven.')

    ranges={m['id']:(line_at(info['text'],m['start']),line_at(info['text'],m['end'])) for info in classes.values() for m in info.get('members',[])}
    by_path=defaultdict(list)
    for f in findings: by_path[f['path']].append(f)
    for n in nodes.values():
        n['finding_ids']=[] if n['kind'] in {'flow_element','unresolved','external_flow','lwc'} else [f['id'] for f in by_path[n['path']] if n['kind']!='apex_method' or ranges[n['id']][0]<=f['line']<=ranges[n['id']][1]]
    return {'schema':'sfg.impact.v1','nodes':list(nodes.values()),'edges':list(edges.values()),'gaps':gaps,
        'limits':{'nodes':MAX_NODES,'edges':MAX_EDGES,'query_nodes':MAX_QUERY_NODES},
        'notice':'Static dependency references, not verified execution paths or proof of authorisation. Missing source and dynamic targets remain unresolved.'}


def _arity(parameters):
    if not parameters.strip(): return 0
    depth=0; count=1
    for c in parameters:
        if c in '(<[': depth+=1
        elif c in ')>]': depth-=1
        elif c==',' and depth==0: count+=1
    return count


def _closing_paren(text,start):
    depth=0
    for i in range(start,len(text)):
        if text[i]=='(': depth+=1
        elif text[i]==')':
            depth-=1
            if depth==0: return i
    return None


def _types(text):
    result={}
    for m in re.finditer(r'(?:^|[;{}(,])\s*(?:(?:public|private|protected|static|final)\s+)*(?:(?:List|Set)\s*<\s*(\w+)\s*>|(\w+))\s+(\w+)\s*(?=[,;)=])',text):
        type_name,var=m.group(1) or m.group(2),m.group(3)
        if type_name.lower() not in {'return','new','as','throw','insert','update','upsert','delete','undelete'}: result[var]=type_name
    return result


def _mode(statement,info):
    if re.search(r'\bWITH\s+USER_MODE\b|\bAccessLevel\s*\.\s*USER_MODE\b|\bas\s+user\b',statement,re.I): return 'explicit_user'
    if re.search(r'\bWITH\s+SYSTEM_MODE\b|\bAccessLevel\s*\.\s*SYSTEM_MODE\b|\bas\s+system\b',statement,re.I): return 'explicit_system'
    if not re.fullmatch(r'\d{1,3}(?:\.\d)?',info.get('api_version') or ''): return 'unknown'
    try: api=float(info['api_version'])
    except (ValueError,TypeError): return 'unknown'
    return 'trigger_system_context' if info['trigger'] else 'user_default_api67_plus' if api>=67 else 'legacy_system_default'


def query_graph(graph,focus,direction='both',depth=2):
    if direction not in {'upstream','downstream','both'}: raise ValueError('Direction must be upstream, downstream or both')
    if type(depth) is not int or not 1<=depth<=4: raise ValueError('Depth must be from 1 to 4')
    nodes={n['id']:n for n in graph['nodes']}
    if focus not in nodes: raise ValueError('Select an existing graph node ID')
    seeds={focus}
    # Component selections include their members; method selections remain method-specific.
    if nodes[focus]['kind'] in {'apex_class','flow'}:
        seeds.update(e['target'] for e in graph['edges'] if e['source']==focus and e['kind']=='contains')
    truncated=len(seeds)>MAX_QUERY_NODES
    if truncated: seeds={focus}|set(sorted(seeds-{focus})[:MAX_QUERY_NODES-1])
    selected=set(seeds); edge_ids=set()
    for walk in (['upstream','downstream'] if direction=='both' else [direction]):
        queue=deque((s,0) for s in sorted(seeds)); visited=set(seeds)
        while queue:
            current,distance=queue.popleft()
            if distance>=depth: continue
            for e in graph['edges']:
                if e['kind']=='contains': continue
                match=e['target']==current if walk=='upstream' else e['source']==current
                if not match: continue
                other=e['source'] if walk=='upstream' else e['target']
                if other not in selected and len(selected)>=MAX_QUERY_NODES:
                    truncated=True; continue
                selected.add(other);edge_ids.add(e['id'])
                if other not in visited:
                    visited.add(other);queue.append((other,distance+1))
    chosen=[e for e in graph['edges'] if e['id'] in edge_ids]
    kinds={e['kind'] for e in chosen}
    tests=['Verify allowed and denied callers for the selected entry point; dependency references do not establish authorisation.']
    if kinds & {'writes','may_activate'}: tests.append('Test expected record changes, denied side effects, entry criteria, bulk inputs and recursion.')
    if kinds & {'enqueues','schedules'}: tests.append('Test revalidation after the async boundary, stale/replayed work, principal changes and duplicate execution.')
    if 'fault' in kinds: tests.append('Test the fault route, rollback behaviour, recovery eligibility and diagnostic output.')
    if kinds & {'reads','reads_field','grants_field_access'}: tests.append('Test least-privileged CRUD/FLS and record visibility; verify intended privileged exceptions separately.')
    owners={nodes[n].get('owner',n) for n in selected if nodes[n]['kind'] in {'apex_class','apex_method'}}
    access=[e for e in graph['edges'] if e['kind']=='grants_class_access' and e['target'] in owners]
    return {'focus':focus,'direction':direction,'depth':depth,'nodes':[n for n in graph['nodes'] if n['id'] in selected],
        'declared_access_context':access,
        'edges':chosen,'truncated':truncated,'suggested_tests':tests,'total_graph_gaps':len(graph['gaps']),'gaps':[g for g in graph['gaps'] if g.get('path')=='.' or g.get('component') in selected or g.get('path') in {nodes[n]['path'] for n in selected}],
        'notice':graph['notice']}
