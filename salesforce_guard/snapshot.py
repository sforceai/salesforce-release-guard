"""Bounded metadata snapshots. Absence requires declared coverage, never a guess."""
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .scan import linked, MAX_FILE, MAX_TOTAL, MAX_FILES, MAX_ENTRIES, SKIP_DIRS

NS='http://soap.sforce.com/2006/04/metadata'
SUFFIXES={'.cls':'ApexClass','.trigger':'ApexTrigger','.flow-meta.xml':'Flow',
 '.permissionset-meta.xml':'PermissionSet','.profile-meta.xml':'Profile',
 '.page':'ApexPage','.component':'ApexComponent','.object-meta.xml':'CustomObject',
 '.field-meta.xml':'CustomField','.permissionset':'PermissionSet','.profile':'Profile',
 '.flow':'Flow','.object':'CustomObject'}
SUPPORTED=set(SUFFIXES.values())|{'LightningComponentBundle'}
NAME=re.compile(r'[A-Za-z][A-Za-z0-9_.-]{0,199}')


def xml(text):
    if re.search(r'<!\s*(DOCTYPE|ENTITY)\b',text,re.I): raise ValueError('DTD/entity XML is unsupported')
    try: root=ET.fromstring(text)
    except ET.ParseError: raise ValueError('Invalid metadata XML') from None
    stack=[(root,1)];count=0
    while stack:
        e,depth=stack.pop();count+=1
        if depth>64 or count>50000: raise ValueError('Metadata XML nesting/element limit exceeded')
        stack.extend((child,depth+1) for child in e)
    return root


def local(tag): return tag.rsplit('}',1)[-1]


def identity(kind,name,namespace=''):
    if not isinstance(kind,str) or kind not in SUPPORTED: raise ValueError('Unsupported metadata type')
    if not isinstance(name,str) or not NAME.fullmatch(name) or '..' in name: raise ValueError('Invalid metadata full name')
    if not isinstance(namespace,str) or (namespace and not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,39}',namespace)): raise ValueError('Invalid namespace')
    return namespace+'|'+kind+'|'+name


def parse_manifest(path,namespace=''):
    path=Path(path)
    if linked(path) or path.stat().st_size>MAX_FILE: raise ValueError('Manifest is linked or oversized')
    root=xml(path.read_text(encoding='utf-8-sig'))
    if local(root.tag)!='Package': raise ValueError('Expected a Salesforce Package manifest')
    result={}
    for group in root:
        if local(group.tag)!='types': continue
        kind=next(((e.text or '').strip() for e in group if local(e.tag)=='name'),'')
        for e in group:
            if local(e.tag)!='members': continue
            name=(e.text or '').strip()
            if '*' in name: raise ValueError('Use explicit manifest members; wildcards cannot define reviewed release scope')
            key=identity(kind,name,namespace)
            if key in result: raise ValueError('Duplicate manifest component: '+key)
            result[key]={'type':kind,'full_name':name,'namespace':namespace}
    if not result: raise ValueError('Manifest has no supported explicit components')
    return result


def canonical(text,is_xml):
    text=text.replace('\r\n','\n').replace('\r','\n')
    if not is_xml: return text
    root=xml(text)
    def visit(e):
        # Preserve element order and meaningful text. Only formatting-only whitespace is ignored.
        return [e.tag,sorted(e.attrib.items()),e.text if (e.text or '').strip() else '',
                [[visit(c),c.tail if (c.tail or '').strip() else ''] for c in e]]
    return json.dumps(visit(root),ensure_ascii=True,separators=(',',':'))


@dataclass
class Snapshot:
    root: Path
    components: dict=field(default_factory=dict)
    files: dict=field(default_factory=dict)
    issues: list=field(default_factory=list)
    complete_types: set=field(default_factory=set)
    absent: set=field(default_factory=set)
    namespace: str=''
    provenance: dict=field(default_factory=dict)

    def state(self,key):
        if self.issues: return 'unknown'
        if key in self.components:
            return 'unknown' if self.components[key]['issues'] else 'present'
        ns,kind,name=key.split('|',2)
        if ns!=self.namespace or self.issues: return 'unknown'
        if any(c['issues'] for c in self.components.values() if c['type']==kind): return 'unknown'
        return 'absent' if key in self.absent or kind in self.complete_types else 'unknown'

    def receipt(self):
        inventory=[{'identity':key,'hash':c['hash'],'files':sorted(c['files'])} for key,c in sorted(self.components.items())]
        return {'snapshot_sha256':hashlib.sha256(json.dumps(inventory,sort_keys=True).encode()).hexdigest(),
            'components':len(inventory),'issues':self.issues,'namespace':self.namespace,
            'complete_types':sorted(self.complete_types),'explicit_absence_count':len(self.absent),
            'provenance':self.provenance,'coverage_note':'Completeness is a supplied snapshot/capture declaration, not proof of live org state.'}


def load_snapshot(directory):
    original=Path(directory).absolute()
    if any(linked(p) for p in (original,*original.parents)): raise ValueError('Snapshot roots cannot traverse links or reparse points')
    root=original.resolve(strict=True)
    if not root.is_dir(): raise ValueError('Snapshot must be a directory')
    result=Snapshot(root)
    declared_hashes=None
    ledger=root/'sfg-snapshot.json'
    if ledger.exists():
        if linked(ledger) or ledger.stat().st_size>MAX_FILE: raise ValueError('Snapshot declaration is linked or oversized')
        data=json.loads(ledger.read_text(encoding='utf-8'))
        if not isinstance(data,dict) or data.get('schema')!='sfg.snapshot.v1': raise ValueError('Unsupported snapshot declaration')
        result.namespace=data.get('namespace','')
        identity('ApexClass','Validation',result.namespace)
        complete=data.get('complete_types',[])
        if not isinstance(complete,list) or any(not isinstance(t,str) or t not in SUPPORTED for t in complete): raise ValueError('Invalid complete_types declaration')
        result.complete_types=set(complete)
        declared_hashes=data.get('files_sha256')
        if declared_hashes is not None and (not isinstance(declared_hashes,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not re.fullmatch('[a-f0-9]{64}',v) for k,v in declared_hashes.items())): raise ValueError('Invalid file-hash declaration')
        absent=data.get('absent_components',[])
        if not isinstance(absent,list) or len(absent)>4000 or any(not isinstance(i,dict) or 'type' not in i or 'full_name' not in i for i in absent): raise ValueError('Invalid absent_components declaration')
        for item in absent: result.absent.add(identity(item['type'],item['full_name'],result.namespace))
        p=data.get('provenance',{})
        if not isinstance(p,dict): raise ValueError('Invalid provenance')
        # No arbitrary input fields or credentials are copied into reports.
        result.provenance={k:p[k] for k in ('kind','org_id','role','captured_at') if k in p and isinstance(p[k],str) and len(p[k])<=100}
    from os import walk
    entries=0; size=0; seen=0; companions={}
    for folder,dirs,names in walk(root,followlinks=False,onerror=lambda _:result.issues.append('Unreadable directory')):
        safe=[]
        for name in sorted(dirs):
            child=Path(folder)/name
            if name.lower() in SKIP_DIRS: continue
            if linked(child): result.issues.append('Linked directory skipped'); continue
            safe.append(name)
        dirs[:]=safe
        entries+=len(dirs)+len(names)
        if entries>MAX_ENTRIES: result.issues.append('Directory-entry limit'); break
        for name in sorted(names):
            path=Path(folder)/name; relative=path.relative_to(root).as_posix()
            parts=Path(relative).parts
            kind=next((k for suffix,k in sorted(SUFFIXES.items(),key=lambda pair:-len(pair[0])) if name.endswith(suffix)),None)
            bundle='lwc' in parts and name.endswith(('.js','.html','.css','.svg','.js-meta.xml'))
            companion=name.endswith(('.cls-meta.xml','.trigger-meta.xml','.page-meta.xml','.component-meta.xml'))
            if not kind and not bundle and not companion: continue
            seen+=1
            if seen>MAX_FILES: result.issues.append('File-count limit'); break
            try:
                if linked(path) or not path.resolve().is_relative_to(root): raise ValueError('Linked file skipped')
                with path.open('rb') as stream: content=stream.read(MAX_FILE+1)
                size+=len(content)
                if len(content)>MAX_FILE or size>MAX_TOTAL: raise ValueError('Snapshot size limit')
                text=content.decode('utf-8-sig')
                rawhash=hashlib.sha256(content).hexdigest()
                result.files[relative]=(text,rawhash)
                if companion:
                    companions[relative]=(text,rawhash); continue
                if bundle:
                    bundle_index=parts.index('lwc')
                    if len(parts)<=bundle_index+2: raise ValueError('Invalid LWC bundle layout')
                    kind='LightningComponentBundle'; full_name=parts[bundle_index+1]
                else:
                    suffix=next(s for s,k in sorted(SUFFIXES.items(),key=lambda pair:-len(pair[0])) if k==kind and name.endswith(s))
                    full_name=name[:-len(suffix)]
                    if kind=='CustomField':
                        if 'objects' not in parts: raise ValueError('Field requires decomposed object directory')
                        full_name=parts[parts.index('objects')+1]+'.'+full_name
                key=identity(kind,full_name,result.namespace)
                c=result.components.setdefault(key,{'identity':key,'type':kind,'full_name':full_name,'namespace':result.namespace,'files':{},'issues':[]})
                # Non-bundle metadata must have exactly one definition.
                if c['files'] and not bundle: c['issues'].append('Duplicate component definition')
                c['files'][relative]=(text,rawhash)
                if kind=='CustomObject' and name.endswith('.object'):
                    tree=xml(text)
                    if any(local(e.tag)=='fields' for e in tree): c['issues'].append('Convert monolithic object fields to decomposed source before comparison')
            except (OSError,UnicodeError,ValueError) as exc:
                result.issues.append(relative+': '+type(exc).__name__)
        if seen>MAX_FILES or size>MAX_TOTAL: break
    for c in result.components.values():
        if c['type'] in {'ApexClass','ApexTrigger','ApexPage','ApexComponent'}:
            main=next(iter(c['files']))
            if main+'-meta.xml' in companions: c['files'][main+'-meta.xml']=companions.pop(main+'-meta.xml')
            else: c['issues'].append('Companion metadata missing')
        fingerprints=[]
        for path,(text,digest) in sorted(c['files'].items()):
            try:
                xml_file=path.endswith(('.xml','.flow','.permissionset','.profile','.object'))
                content=canonical(text,xml_file)
                if c['type'] in {'CustomObject','CustomField'} and xml_file:
                    tree=xml(text)
                    full=next(((e.text or '').strip() for e in tree if local(e.tag)=='fullName'),'')
                    if full and full!=c['full_name'].split('.')[-1]: c['issues'].append('XML fullName conflicts with source component identity')
                logical='/'.join(Path(path).parts[Path(path).parts.index('lwc')+2:]) if c['type']=='LightningComponentBundle' else ('metadata' if path.endswith('-meta.xml') and c['type'] in {'ApexClass','ApexTrigger','ApexPage','ApexComponent'} else 'definition')
                fingerprints.append([logical,hashlib.sha256(content.encode()).hexdigest()])
            except (ET.ParseError,ValueError): c['issues'].append('Invalid XML definition')
        c['hash']=hashlib.sha256(json.dumps(sorted(fingerprints)).encode()).hexdigest()
    if companions: result.issues.append('Orphaned companion metadata')
    if set(result.components)&result.absent: result.issues.append('Contradictory presence/absence declaration')
    if declared_hashes is not None and declared_hashes!={p:h for p,(t,h) in result.files.items()}: result.issues.append('Snapshot content no longer matches the captured file inventory')
    return result
