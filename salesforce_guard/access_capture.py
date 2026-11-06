"""Operator-only fixed-shape access queries. No writes or generic query interface."""
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import uuid

from .access import API_NAME,USER_ID,scope_from_dict,observation,load_evidence,save_access
from .scan import linked


def checked(value,pattern):
    if not isinstance(value,str) or not re.fullmatch(pattern,value): raise ValueError('Invalid access query parameter')
    return value


def access_identity_matches(row,durable,user_id):
    """Salesforce normalizes the user suffix to 18 characters in returned DurableId."""
    value=row.get('DurableId');principal=row.get('UserId')
    if not isinstance(value,str) or not isinstance(principal,str):return False
    prefix,separator,suffix=value.rpartition('.')
    return bool(separator and prefix==durable and USER_ID.fullmatch(suffix) and USER_ID.fullmatch(principal) and suffix[:15]==user_id[:15] and principal[:15]==user_id[:15])


def same_name(value,expected):
    return isinstance(value,str) and value.casefold()==expected.casefold()


def query_plan(kind,**p):
    """Return only supported SELECT statements; values cannot become SOQL syntax."""
    specs={
        'user':({'user'},"SELECT Id, IsActive, ProfileId FROM User WHERE Id = '{user}' LIMIT 2",False),
        'entity':({'name'},"SELECT DurableId, QualifiedApiName FROM EntityDefinition WHERE QualifiedApiName = '{name}' LIMIT 2",True),
        'field':({'name','field'},"SELECT DurableId, QualifiedApiName, EntityDefinition.QualifiedApiName FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = '{name}' AND QualifiedApiName = '{field}' LIMIT 2",True),
        'entity_access':({'durable'},"SELECT DurableId, UserId, IsReadable, IsCreatable, IsUpdatable, IsDeletable FROM UserEntityAccess WHERE DurableId = '{durable}'",True),
        'field_access':({'durable'},"SELECT DurableId, UserId, IsAccessible, IsCreatable, IsUpdatable FROM UserFieldAccess WHERE DurableId = '{durable}'",True),
        'class':({'name'},"SELECT Id, Name, NamespacePrefix FROM ApexClass WHERE Name = '{name}' AND NamespacePrefix = null LIMIT 2",False),
        'assignments':({'user'},"SELECT AssigneeId, PermissionSetId, PermissionSetGroupId, PermissionSetGroup.Status, IsActive, ExpirationDate FROM PermissionSetAssignment WHERE AssigneeId = '{user}' LIMIT 201",False),
        'profile':({'profile'},"SELECT Id, ProfileId, IsOwnedByProfile, HasActivationRequired, Type, PermissionsAuthorApex, PermissionsModifyAllData FROM PermissionSet WHERE ProfileId = '{profile}' LIMIT 2",False),
        'sets':({'ids'},"SELECT Id, HasActivationRequired, Type, PermissionsAuthorApex, PermissionsModifyAllData FROM PermissionSet WHERE Id IN ({ids}) LIMIT 201",False),
        'grants':({'class_id','ids'},"SELECT ParentId, SetupEntityId FROM SetupEntityAccess WHERE SetupEntityId = '{class_id}' AND ParentId IN ({ids}) LIMIT 201",False),
    }
    if kind not in specs or set(p)!=specs[kind][0]: raise ValueError('Unsupported access query shape')
    values={}
    for k,v in p.items():
        if k=='ids':
            if not isinstance(v,list) or not 1<=len(v)<=200 or any(not isinstance(x,str) for x in v) or len(set(v))!=len(v): raise ValueError('Access permission-set limit exceeded')
            values[k]=','.join("'"+checked(x,r'0PS[A-Za-z0-9]{12}(?:[A-Za-z0-9]{3})?')+"'" for x in v)
        else:
            pattern=USER_ID.pattern if k=='user' else r'00e[A-Za-z0-9]{12}(?:[A-Za-z0-9]{3})?' if k=='profile' else r'01p[A-Za-z0-9]{12}(?:[A-Za-z0-9]{3})?' if k=='class_id' else r'[A-Za-z0-9_.]{1,200}' if k=='durable' else API_NAME.pattern
            values[k]=checked(v,pattern)
    return specs[kind][1].format(**values),specs[kind][2]


class AccessQueryTransport:
    def __init__(self,transport,alias,cwd):
        checked(alias,r'sfg-(?:source|destination)-[a-f0-9]{12}')
        self.transport=transport;self.alias=alias;self.cwd=cwd

    def query(self,kind,**params):
        soql,tooling=query_plan(kind,**params)
        args=['data','query','--query',soql,'--target-org',self.alias,'--json']
        if tooling: args+=['--use-tooling-api']
        result=self.transport._invoke(args,self.cwd,timeout=60)
        if not isinstance(result,dict) or result.get('done') is not True or not isinstance(result.get('records'),list) or type(result.get('totalSize')) is not int or result.get('totalSize')!=len(result['records']) or len(result['records'])>200:
            raise ValueError('Access query response is incomplete or exceeds its bound')
        if any(not isinstance(r,dict) for r in result['records']): raise ValueError('Invalid access query records')
        return result['records']


def collect_access(bridge,role,user_id,scope,output):
    checked(user_id,USER_ID.pattern);scope=scope_from_dict(scope)
    c=bridge._load().get(role)
    if not c: raise ValueError('Connect the requested org role first')
    bridge._verify_alias(c['alias'],c['org_id'])
    q=AccessQueryTransport(bridge.transport,c['alias'],bridge.root);gaps=[]
    def query(kind,**params):
        try: return q.query(kind,**params)
        except (OSError,ValueError): gaps.append(kind+': query unavailable, malformed or incomplete');return None
    users=query('user',user=user_id)
    if not users or len(users)!=1 or str(users[0].get('Id',''))[:15]!=user_id[:15]: raise ValueError('Selected user identity could not be verified')
    user=users[0];active=user.get('IsActive') if type(user.get('IsActive')) is bool else None
    rows=[]
    def access(kind,name,fields):
        if kind=='object': definitions=query('entity',name=name)
        else:
            obj,field=name.split('.');definitions=query('field',name=obj,field=field)
        checks={k:observation(None,'Resource or computed access could not be verified') for k in fields}
        if definitions and len(definitions)==1:
            definition=definitions[0]
            match=same_name(definition.get('QualifiedApiName'),name) if kind=='object' else same_name(definition.get('QualifiedApiName'),field) and isinstance(definition.get('EntityDefinition'),dict) and same_name(definition['EntityDefinition'].get('QualifiedApiName'),obj)
            if not match:
                gaps.append(kind+' definition does not match requested resource: '+name)
                rows.append({'kind':kind,'resource':name,'checks':checks});return
            durable=definitions[0].get('DurableId')
            if isinstance(durable,str) and re.fullmatch(r'[A-Za-z0-9_.]{1,180}',durable):
                key=durable+'.'+user_id[:15]
                records=query('entity_access' if kind=='object' else 'field_access',durable=key)
                if records and len(records)==1 and access_identity_matches(records[0],durable,user_id):
                    checks={k:observation(records[0].get(v) if type(records[0].get(v)) is bool else None,'Salesforce computed '+kind+' access for this user; runtime and record access excluded') for k,v in fields.items()}
                else:gaps.append(kind+' computed identity/row missing or mismatched: '+name)
            else:gaps.append(kind+' durable identity unsupported: '+name)
        else:gaps.append(kind+' definition missing or ambiguous: '+name)
        rows.append({'kind':kind,'resource':name,'checks':checks})
    for name in scope['objects']:access('object',name,{'read':'IsReadable','create':'IsCreatable','update':'IsUpdatable','delete':'IsDeletable'})
    for name in scope['fields']:access('field',name,{'read':'IsAccessible','create':'IsCreatable','update':'IsUpdatable'})
    if scope['classes']:
        profile=query('profile',profile=user.get('ProfileId'));assignments=query('assignments',user=user_id)
        profile_ok=bool(profile and len(profile)==1 and profile[0].get('IsOwnedByProfile') is True and str(profile[0].get('ProfileId',''))[:15]==str(user.get('ProfileId',''))[:15])
        sets=list(profile) if profile_ok else [];uncertain=not profile_ok or assignments is None
        ids=[];group_ids=set()
        for assignment in assignments or []:
            if str(assignment.get('AssigneeId',''))[:15]!=user_id[:15]:uncertain=True;continue
            if assignment.get('IsActive') is False:continue
            if assignment.get('IsActive') is not True:uncertain=True;continue
            group=assignment.get('PermissionSetGroupId')
            if group and (not isinstance(assignment.get('PermissionSetGroup'),dict) or assignment['PermissionSetGroup'].get('Status')!='Updated'):uncertain=True;continue
            expiry=assignment.get('ExpirationDate')
            if expiry:
                try:
                    if datetime.fromisoformat(expiry.replace('Z','+00:00'))<=datetime.now(timezone.utc):continue
                except (ValueError,TypeError):uncertain=True;continue
            ps=assignment.get('PermissionSetId')
            if isinstance(ps,str) and re.fullmatch(r'0PS[A-Za-z0-9]{12}(?:[A-Za-z0-9]{3})?',ps):
                ids.append(ps)
                if group:group_ids.add(ps)
            else:uncertain=True
        if ids:
            additional=query('sets',ids=sorted(set(ids)))
            returned=[x.get('Id') for x in additional or []]
            if additional is None or any(not isinstance(x,str) for x in returned) or len(set(returned))!=len(returned):uncertain=True;additional=[];returned=[]
            if set(returned)!=set(ids):uncertain=True
            sets+=[x for x in additional or [] if x.get('Id') in ids]
        usable=[]
        for ps in sets:
            if ps.get('Id') in group_ids and ps.get('Type')!='Group':uncertain=True;continue
            if ps.get('HasActivationRequired') is not False:uncertain=True;continue
            if type(ps.get('PermissionsAuthorApex')) is not bool or type(ps.get('PermissionsModifyAllData')) is not bool:uncertain=True
            if ps.get('PermissionsAuthorApex') is True or ps.get('PermissionsModifyAllData') is True:uncertain=True
            if isinstance(ps.get('Id'),str):usable.append(ps['Id'])
        for name in scope['classes']:
            classes=query('class',name=name);check=observation(None,'Class or configured permission evidence is incomplete')
            if classes and len(classes)==1 and same_name(classes[0].get('Name'),name) and classes[0].get('NamespacePrefix') is None and usable:
                grants=query('grants',class_id=classes[0].get('Id'),ids=sorted(set(usable)))
                if grants is not None and all(g.get('ParentId') in usable and str(g.get('SetupEntityId',''))[:15]==str(classes[0].get('Id',''))[:15] for g in grants):
                    check=observation(True if grants else None if uncertain else False,'Configured non-session entry grant observed' if grants else 'Configured grant absent or additional/session permissions unresolved; not an execution test')
            rows.append({'kind':'class','resource':name,'checks':{'configured_entry_grant':check}})
    bridge._verify_alias(c['alias'],c['org_id'])
    if bridge._load().get(role)!=c:raise ValueError('Org role changed during access capture')
    again=query('user',user=user_id)
    if again!=users:raise ValueError('Selected user changed during access capture')
    evidence={'schema':'sfg.access.v1','role':role,'org_id':c['org_id'],'user_id':user_id,'user_active':active,'captured_at':datetime.now(timezone.utc).isoformat(),'scope':scope,'rows':rows,'gaps':gaps}
    parent=Path(output).absolute()
    if any(linked(p) for p in (parent,*parent.parents) if p.exists()):raise ValueError('Access output must not traverse links')
    dest=parent/uuid.uuid4().hex;dest.mkdir(parents=True,exist_ok=False)
    path=dest/'access-evidence.json';path.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    report=load_evidence(path);saved=save_access(report,dest)
    return {'evidence':str(path.resolve()),'report':str((saved/'access.html').resolve()),'json':str((saved/'access.json').resolve()),'summary':report['summary'],'status':report['status'],'gaps':gaps,'record_access':'not_assessed','effective_execution_access':'not_assessed'}
