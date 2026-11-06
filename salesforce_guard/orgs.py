"""Operator-only Salesforce CLI bridge. Never imported by native plugin tools.

Salesforce CLI owns OAuth, browser consent, credential storage and refresh. This
module never reads a credential store or exposes generic org commands to a model.
"""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit
import uuid
from contextlib import contextmanager
import time
import xml.etree.ElementTree as ET

from .snapshot import parse_manifest,load_snapshot,NS,SUPPORTED
from .scan import linked

ROLES={'source','destination'}
ORG_ID=re.compile(r'00D[A-Za-z0-9]{12}(?:[A-Za-z0-9]{3})?')
READABLE_ABSENCE={'ApexClass','ApexTrigger','Flow','PermissionSet','Profile','ApexPage','ApexComponent','LightningComponentBundle'}
QUERY='SELECT Id, IsSandbox FROM Organization LIMIT 1'


def org_id(value):
    if not isinstance(value,str) or not ORG_ID.fullmatch(value): raise ValueError('Supply the expected 15- or 18-character Salesforce org ID')
    return value[:15]


def salesforce_login_url(value):
    p=urlsplit(value)
    host=p.hostname or ''
    valid=host in {'login.salesforce.com','test.salesforce.com'} or bool(re.fullmatch(r'[a-z0-9-]+(?:\.sandbox)?\.my\.salesforce\.com',host))
    if p.scheme!='https' or not valid or p.username or p.password or p.port is not None or p.path not in {'','/'} or p.query or p.fragment:
        raise ValueError('Use an HTTPS Salesforce login or My Domain URL without a path, credentials, port or query')
    return 'https://'+host


def cli_command(node=None,entry=None,executable=None):
    if node or entry:
        if not(node and entry): raise ValueError('Supply both Node and Salesforce CLI entry paths')
        if not Path(node).is_file() or not Path(entry).is_file(): raise ValueError('Installed CLI paths not found')
        return [str(Path(node).resolve()),str(Path(entry).resolve())]
    if executable:
        if Path(executable).suffix.lower() in {'.cmd','.bat','.ps1'} or not Path(executable).is_file(): raise ValueError('Supply an existing native CLI executable, not a shell wrapper')
        return [str(Path(executable).resolve())]
    native=shutil.which('sf')
    if native and Path(native).suffix.lower() not in {'.cmd','.bat','.ps1'}: return [str(Path(native).resolve())]
    if os.name=='nt':
        shim=shutil.which('sf.cmd')
        node=shutil.which('node')
        if shim and node:
            entry=Path(shim).parent/'node_modules'/'@salesforce'/'cli'/'bin'/'run.js'
            if entry.is_file(): return [node,str(entry)]
    raise ValueError('Install Salesforce CLI or supply native executable / Node and CLI entry paths; shell wrappers are not executed')


class CliTransport:
    def __init__(self,command): self.command=command

    def run(self,args,cwd,timeout=120,json_output=True):
        # Fixed callers supply all commands; no command text, tokens or shell interpolation.
        allowed={('org','login','web'),('data','query'),('org','list','metadata'),('project','retrieve','start'),('org','logout')}
        if not any(tuple(args[:len(prefix)])==prefix for prefix in allowed): raise ValueError('CLI operation is outside the review bridge allowlist')
        if args[:2]==['data','query']:
            if len(args)!=7 or args[:4]!=['data','query','--query',QUERY] or args[4]!='--target-org' or args[6]!='--json' or not re.fullmatch(r'sfg-(?:source|destination)-[a-f0-9]{12}',args[5]):
                raise ValueError('Only the fixed org-identity query is permitted')
        return self._invoke(args,cwd,timeout,json_output)

    def _invoke(self,args,cwd,timeout=120,json_output=True):
        """Internal execution for validated fixed operator commands, never model input."""
        allowed_env={'PATH','PATHEXT','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','HOME','APPDATA','LOCALAPPDATA','SF_DATA_DIR','SF_CACHE_DIR','SF_CONFIG_DIR'}
        env={k:v for k,v in os.environ.items() if k.upper() in allowed_env}
        env.update(SF_DISABLE_TELEMETRY='true',SF_AUTOUPDATE_DISABLE='true',SF_SKIP_NEW_VERSION_CHECK='true',DEBUG='salesforce-guard',SF_LOG_STDERR='true',SF_LOG_LEVEL='error')
        try:
            # Disk spooling bounds memory; raw CLI output is discarded, never put in a report or exception.
            with tempfile.TemporaryFile() as out,tempfile.TemporaryFile() as err:
                from .analyzer import _execute
                code=_execute([*self.command,*args],cwd,env,out,err,timeout)
                if code: raise ValueError('Salesforce CLI operation failed; check CLI setup, permissions and sign-in outside the reviewing agent')
                if not json_output: return None
                out.seek(0,2)
                if out.tell()>16*1024*1024: raise ValueError('CLI response exceeded the review limit')
                out.seek(0); data=json.loads(out.read().decode('utf-8-sig'))
                if not isinstance(data,dict) or data.get('status')!=0: raise ValueError('Salesforce CLI did not confirm success')
                return data.get('result')
        except subprocess.TimeoutExpired: raise ValueError('Salesforce CLI operation timed out; no successful connection or capture is claimed') from None
        except (OSError,json.JSONDecodeError,UnicodeError): raise ValueError('Salesforce CLI could not complete a readable response') from None


class OrgBridge:
    def __init__(self,state_dir,transport):
        self.root=Path(state_dir).absolute()
        if any(linked(p) for p in (self.root,*self.root.parents) if p.exists()): raise ValueError('Connection directory must not traverse links')
        self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/'connections.json'; self.transport=transport

    def _load(self):
        if not self.path.exists(): return {}
        if linked(self.path) or self.path.stat().st_size>65536: raise ValueError('Invalid connection registry')
        data=json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(data,dict): raise ValueError('Invalid connection registry')
        for role,c in data.items():
            if role not in ROLES or not isinstance(c,dict): raise ValueError('Invalid role binding')
            if set(c)!={'org_id','is_sandbox','alias','login_url','connected_at'} or type(c.get('is_sandbox')) is not bool or not isinstance(c.get('connected_at'),str) or len(c['connected_at'])>100: raise ValueError('Invalid connection registry fields')
            org_id(c.get('org_id')); salesforce_login_url(c.get('login_url',''))
            if not isinstance(c.get('alias'),str) or not re.fullmatch(r'sfg-'+role+r'-[a-f0-9]{12}',c['alias']): raise ValueError('Invalid generated org alias')
        return data

    def _save(self,data):
        temporary=self.root/('connections-'+uuid.uuid4().hex+'.tmp')
        with temporary.open('x',encoding='utf-8') as stream: json.dump(data,stream,indent=2)
        try: temporary.chmod(0o600)
        except OSError: pass
        temporary.replace(self.path)

    @contextmanager
    def _registry_lock(self):
        lock=self.root/'registry.lock';handle=None
        for attempt in range(40):
            try: handle=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);break
            except FileExistsError: time.sleep(0.05)
        if handle is None: raise ValueError('Connection registry is busy; retry after the other operator action finishes')
        try: yield
        finally: os.close(handle);lock.unlink()

    def _verify_alias(self,alias,expected):
        response=self.transport.run(['data','query','--query',QUERY,'--target-org',alias,'--json'],self.root)
        records=response.get('records',[]) if isinstance(response,dict) else []
        if not isinstance(records,list) or len(records)!=1 or not isinstance(records[0],dict) or org_id(records[0].get('Id'))!=org_id(expected): raise ValueError('Org identity mismatch; role binding/capture refused')
        if type(records[0].get('IsSandbox')) is not bool: raise ValueError('Org environment could not be verified')
        return {'org_id':records[0]['Id'],'is_sandbox':records[0]['IsSandbox']}

    def login(self,role,url,expected_org_id,client_id=None):
        if role not in ROLES: raise ValueError('Role must be source or destination')
        url=salesforce_login_url(url); expected=org_id(expected_org_id)
        alias='sfg-'+role+'-'+uuid.uuid4().hex[:12]
        args=['org','login','web','--instance-url',url,'--alias',alias]
        if client_id:
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{9,299}',client_id): raise ValueError('Invalid public OAuth client ID')
            args+=['--client-id',client_id]
        with self._registry_lock():
            data=self._load()
            if any(r!=role and org_id(other['org_id'])==expected for r,other in data.items()): raise ValueError('Source and destination must be separate org identities')
            self.transport.run(args,self.root,timeout=300,json_output=False)
            verified=self._verify_alias(alias,expected)
            record={**verified,'alias':alias,'login_url':url,'connected_at':datetime.now(timezone.utc).isoformat()}
            data[role]=record; self._save(data)
        return {'role':role,**record,'credential_owner':'Salesforce CLI','effective_user_access_assessed':False,'notice':'No tokens are stored in the connection registry. Org identity is verified, not effective user permissions. This binding is not a read-only OAuth scope.'}

    def status(self,verify=False):
        data=self._load(); result={}
        for role,c in data.items():
            if verify: self._verify_alias(c['alias'],c['org_id'])
            result[role]={**c,'identity_checked_now':verify,'effective_user_access_assessed':False}
        return result

    def disconnect(self,role,revoke=False):
        with self._registry_lock():
            data=self._load()
            if role not in data: raise ValueError('Role is not connected')
            c=data[role]
            if revoke:
                self._verify_alias(c['alias'],c['org_id'])
                self.transport.run(['org','logout','--target-org',c['alias'],'--no-prompt'],self.root,json_output=False)
            del data[role]; self._save(data)
        return {'role':role,'disconnected':True,'cli_logout_requested':revoke,
                'notice':'Without --revoke, Salesforce CLI authorisation remains. CLI logout may affect other uses of the same authorised user.'}

    def capture(self,role,manifest,output):
        data=self._load()
        if role not in data: raise ValueError('Connect this role before capturing metadata')
        c=data[role]; self._verify_alias(c['alias'],c['org_id'])
        requested=parse_manifest(manifest)
        if len(requested)>200: raise ValueError('Capture limit is 200 explicitly named components; supply a narrower manifest')
        present={}; absent=[]; coverage_notes=[]
        for kind in sorted({item['type'] for item in requested.values()}):
            listing=self.transport.run(['org','list','metadata','--metadata-type',kind,'--api-version','67.0','--target-org',c['alias'],'--json'],self.root)
            if listing is None: raise ValueError('Metadata inventory was not confirmed; no absence can be declared')
            if not isinstance(listing,list) or any(not isinstance(x,dict) or not isinstance(x.get('fullName'),str) for x in listing): raise ValueError('Unsupported metadata inventory response')
            if len(listing)>=1000: raise ValueError('Metadata listing may be truncated; absence cannot be established')
            names={x['fullName'] for x in listing}
            for key,item in requested.items():
                if item['type']!=kind: continue
                if item['full_name'] in names: present[key]=item
                elif kind in READABLE_ABSENCE: absent.append({'type':kind,'full_name':item['full_name']})
                else: coverage_notes.append('No absence claim for unsupported child/standard metadata listing: '+kind)
        parent=Path(output).absolute()
        if any(linked(p) for p in (parent,*parent.parents) if p.exists()): raise ValueError('Output directory must not traverse links')
        parent.mkdir(parents=True,exist_ok=True)
        destination=parent/(role+'-'+uuid.uuid4().hex)
        with tempfile.TemporaryDirectory(prefix='sfg-org-capture-') as work:
            work=Path(work)
            (work/'sfdx-project.json').write_text(json.dumps({'packageDirectories':[{'path':'force-app','default':True}],'namespace':'','sourceApiVersion':'67.0'}))
            (work/'force-app').mkdir()
            stage=work/'snapshot';stage.mkdir()
            if present:
                package=ET.Element('Package',xmlns=NS)
                for kind in sorted({i['type'] for i in present.values()}):
                    group=ET.SubElement(package,'types')
                    for i in sorted(present.values(),key=lambda x:x['full_name']):
                        if i['type']==kind: ET.SubElement(group,'members').text=i['full_name']
                    ET.SubElement(group,'name').text=kind
                ET.SubElement(package,'version').text='67.0'
                package_path=work/'package.xml';ET.ElementTree(package).write(package_path,encoding='utf-8',xml_declaration=True)
                response=self.transport.run(['project','retrieve','start','--manifest',str(package_path),'--target-org',c['alias'],'--api-version','67.0','--output-dir',str(stage),'--wait','5','--json'],work,timeout=360)
                if not isinstance(response,dict) or response.get('done') is not True or response.get('success') is not True: raise ValueError('Metadata retrieval did not confirm completed success')
            self._verify_alias(c['alias'],c['org_id'])
            current=self._load().get(role)
            if not current or current['alias']!=c['alias'] or org_id(current['org_id'])!=org_id(c['org_id']): raise ValueError('Role connection changed during capture; snapshot refused')
            snap=load_snapshot(stage)
            if snap.issues or any(v['issues'] for v in snap.components.values()): raise ValueError('Retrieved snapshot is incomplete or has unsupported source definitions')
            if any(key not in snap.components for key in present): raise ValueError('Retrieved components do not match the requested inventory')
            ledger={'schema':'sfg.snapshot.v1','namespace':'','complete_types':[],'absent_components':absent,
                'files_sha256':{p:h for p,(t,h) in snap.files.items()},
                'provenance':{'kind':'salesforce_cli_scoped_capture','org_id':c['org_id'],'role':role,'captured_at':datetime.now(timezone.utc).isoformat()}}
            (stage/'sfg-snapshot.json').write_text(json.dumps(ledger,indent=2))
            shutil.copytree(stage,destination)
        return {'role':role,'org_id':c['org_id'],'snapshot_path':str(destination),'components':len(snap.components),'declared_absent':len(absent),
                'coverage_notes':coverage_notes,'notice':'Scoped metadata capture, not a complete org export. No deployment or business-record mutation was performed.'}
