"""Bounded local heuristics with explicit provenance and incomplete-scan reporting."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
import xml.etree.ElementTree as ET

from . import __version__
from .lexer import mask, line_at, safe_excerpt
from .rules import RULES, OWASP, SOURCES

MAX_FILES = 4000
MAX_FILE = 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MAX_ENTRIES = 20000
MAX_FINDINGS = 2000
SKIP_DIRS = {'.git', '.sf', '.sfdx', '.hermes', 'node_modules', '.venv', 'venv', '__pycache__', '.runtime', 'output', 'dist'}
BROAD = {'ModifyAllData', 'ViewAllData', 'AuthorApex', 'CustomizeApplication', 'ManageUsers', 'AssignPermissionSets'}


def _xml(text):
    if re.search(r'<!\s*(DOCTYPE|ENTITY)\b', text, re.I):
        raise ValueError('DTD/entity declarations are unsupported')
    return ET.fromstring(text)


def local_name(tag):
    return tag.rsplit('}', 1)[-1]


def children(element):
    return {local_name(c.tag): (c.text or '').strip() for c in element}


def relevant(name):
    return name.endswith(('.cls', '.trigger', '.page', '.component', '.cls-meta.xml', '.trigger-meta.xml',
                          '.permissionset-meta.xml', '.profile-meta.xml', '.flow-meta.xml'))


def linked(path):
    # Python 3.10/3.11 lack Path.is_junction; Windows reparse attributes cover junctions too.
    return path.is_symlink() or bool(getattr(path.lstat(), 'st_file_attributes', 0) & 0x400)


def inventory(root):
    original = Path(root).absolute()
    if any(linked(p) for p in (original, *original.parents)):
        raise ValueError('Source roots must not traverse symlinks or directory junctions')
    root = original.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Project must be a directory')
    files, issues, total, entries = {}, [], 0, 0
    def walk_error(error):
        issues.append({'path': str(Path(error.filename).name), 'reason': 'directory_unreadable'})
    for folder, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        dirs[:] = sorted(d for d in dirs if d.lower() not in SKIP_DIRS)
        for d in list(dirs):
            child = Path(folder) / d
            if linked(child):
                dirs.remove(d)
                issues.append({'path': child.relative_to(root).as_posix(), 'reason': 'linked_directory_skipped'})
        entries += len(dirs) + len(names)
        if entries > MAX_ENTRIES:
            issues.append({'path': '.', 'reason': 'directory_entry_limit'})
            break
        for name in sorted(names):
            if not relevant(name) and not ('lwc' in Path(folder).relative_to(root).parts and name.endswith('.js')):
                continue
            path = Path(folder) / name
            rel = path.relative_to(root).as_posix()
            if len(files) >= MAX_FILES:
                issues.append({'path': '.', 'reason': 'file_limit'})
                return root, files, issues
            try:
                if linked(path) or not path.resolve().is_relative_to(root):
                    raise ValueError('linked_file_skipped')
                if path.stat().st_size > MAX_FILE:
                    raise ValueError('file_size_limit')
                with path.open('rb') as stream:
                    content = stream.read(MAX_FILE + 1)
                if len(content) > MAX_FILE:
                    raise ValueError('file_size_limit')
                total += len(content)
                if total > MAX_TOTAL:
                    issues.append({'path': rel, 'reason': 'total_size_limit'})
                    return root, files, issues
                text = content.decode('utf-8-sig')
                files[rel] = (text, hashlib.sha256(content).hexdigest())
            except (OSError, UnicodeError, ValueError) as exc:
                issues.append({'path': rel, 'reason': str(exc) if isinstance(exc, ValueError) else type(exc).__name__})
    return root, files, issues


def scan_project(root):
    root, files, issues = inventory(root)
    findings, contexts = [], []

    def add(rule, path, text, pos=0, detail='', api=None, context=''):
        if len(findings) >= MAX_FINDINGS:
            if not any(i['reason'] == 'finding_limit' for i in issues):
                issues.append({'path': '.', 'reason': 'finding_limit'})
            return
        title, severity, category, remedy = RULES[rule]
        line = line_at(text, pos)
        anchor = f'{rule}|{path}|{line}|{files[path][1]}|{detail}'
        findings.append({'id': hashlib.sha256(anchor.encode()).hexdigest()[:16], 'rule': rule,
            'title': title, 'severity': severity, 'owasp': f'{category}:2025',
            'status': 'requires_review', 'confidence': 'static_signal', 'path': path, 'line': line,
            'evidence': safe_excerpt(text, line) if path.endswith(('.cls', '.trigger')) else detail,
            'detail': detail, 'api_version': api, 'execution_context': context, 'remedy': remedy})

    for path, (text, digest) in sorted(files.items()):
        if path.endswith(('.cls', '.trigger')):
            code, literals = mask(text), mask(text, strings=False)
            if re.search(r'@isTest\b', code, re.I):
                contexts.append({'path': path, 'kind': 'test_class', 'reviewed': False})
                continue
            api = None
            meta = files.get(path + '-meta.xml')
            try:
                if meta:
                    values = [e.text for e in _xml(meta[0]).iter() if local_name(e.tag) == 'apiVersion']
                    api = float(values[0]) if len(values) == 1 and re.fullmatch(r'\d{1,3}(?:\.\d)?', values[0] or '') else None
            except (ValueError, ET.ParseError):
                issues.append({'path': path + '-meta.xml', 'reason': 'invalid_api_metadata'})
            if api is None:
                issues.append({'path': path, 'reason': 'unknown_api_version'})
            trigger = path.endswith('.trigger')
            mode = 'trigger_system_context' if trigger else ('user_default_api67_plus' if api and api >= 67 else 'legacy_system_default' if api else 'unknown')
            contexts.append({'path': path, 'api_version': api, 'default_mode': mode, 'reviewed': True})
            for m in re.finditer(r'\bWITH\s+SYSTEM_MODE\b|\bAccessLevel\s*\.\s*SYSTEM_MODE\b|\b(?:insert|update|upsert|delete|undelete|merge)\s+as\s+system\b', code, re.I):
                add('APEX001', path, text, m.start(), 'Explicit system-mode operation; authorisation path is not proven by this scan.', api, mode)
            for m in re.finditer(r'\bwithout\s+sharing\b', code, re.I):
                add('APEX003', path, text, m.start(), 'Record-sharing bypass declaration. Inspect operation access modes separately.', api, mode)
            # File-level triage only: deliberately do not infer absence of permission checks from keywords.
            for m in re.finditer(r'\[\s*SELECT\b[^\]]*\]|\b(?:insert|update|upsert|delete|undelete|merge)\s+(?!as\b)[A-Za-z_]\w*\s*;', code, re.I):
                if trigger or (api is not None and api <= 66):
                    if not re.search(r'\bWITH\s+(?:USER|SYSTEM)_MODE\b', m.group(), re.I):
                        add('APEX002', path, text, m.start(), 'Implicit operation in legacy/trigger context; caller checks and sanitisation require review.', api, mode)
            for m in re.finditer(r'\bDatabase\s*\.\s*(?:query|getQueryLocator|countQuery)\s*\(([^;]*?)\)\s*;', literals, re.I):
                # Inspect plus operators outside string literals, not harmless plus characters inside a query literal.
                if '+' in mask(m.group(1)):
                    add('APEX004', path, text, m.start(), 'Dynamic query expression contains concatenation; input trust and bind use require review.', api, mode)
            for m in re.finditer(r"\bCrypto\s*\.\s*generateDigest\s*\(\s*'(?:MD5|SHA1|SHA-1)'", literals, re.I):
                add('APEX005', path, text, m.start(), 'Legacy digest identifier; assess security purpose.', api, mode)
            for m in re.finditer(r'\bcatch\s*\([^)]*\)\s*\{\s*\}', code, re.I):
                add('APEX006', path, text, m.start(), 'Handler contains no executable statement.', api, mode)
            for m in re.finditer(r'\bSystem\s*\.\s*debug\s*\(', code, re.I):
                add('APEX007', path, text, m.start(), 'Debug call found; actual data sensitivity is unknown.', api, mode)
            for m in re.finditer(r"\b(?:password|api_?key|client_?secret|access_?token)\s*=\s*'((?:\\.|[^'\\]){12,})'", literals, re.I):
                add('APEX008', path, text, m.start(), 'Credential-shaped literal [redacted]; confirm authenticity.', api, mode)
        elif path.endswith(('.permissionset-meta.xml', '.profile-meta.xml', '.flow-meta.xml')):
            try:
                tree = _xml(text)
            except (ET.ParseError, ValueError) as exc:
                issues.append({'path': path, 'reason': 'xml_parse_error: ' + type(exc).__name__})
                continue
            for e in tree.iter():
                tag, values = local_name(e.tag), children(e)
                if tag == 'userPermissions' and values.get('enabled') == 'true' and values.get('name') in BROAD:
                    add('META001', path, text, max(0, text.find(values['name'])), detail='Enabled user permission: ' + values['name'])
                elif tag == 'objectPermissions':
                    for field in ('modifyAllRecords', 'viewAllRecords', 'viewAllFields'):
                        if values.get(field) == 'true':
                            add('META002', path, text, max(0, text.find(values.get('object', '<objectPermissions>'))), detail=f"{values.get('object', '(unknown object)')}: {field}=true")
                elif tag == 'fieldPermissions' and values.get('editable') == 'true':
                    add('META003', path, text, max(0, text.find(values.get('field', '<fieldPermissions>'))), detail='Editable field: ' + values.get('field', '(unknown field)'))
                elif tag == 'runInMode' and (e.text or '').strip() in ('SystemMode', 'SystemModeWithoutSharing', 'SystemModeWithSharing'):
                    add('FLOW001', path, text, max(0, text.find((e.text or '').strip())), detail='Declared Flow runInMode: ' + (e.text or '').strip())
        elif path.endswith(('.page', '.component')):
            cleaned = re.sub(r'<!--[\s\S]*?-->', lambda m: '\n' * m.group().count('\n'), text)
            for m in re.finditer(r'\bescape\s*=\s*[\"\']false[\"\']', cleaned, re.I):
                add('VF001', path, text, m.start(), 'Visualforce markup declares escape=false.')

    findings.sort(key=lambda f: ({'high': 0, 'medium': 1, 'low': 2}[f['severity']], f['path'], f['line'], f['rule']))
    inv = [{'path': p, 'sha256': h, 'bytes': len(t.encode('utf-8'))} for p, (t, h) in sorted(files.items())]
    snapshot = hashlib.sha256(json.dumps(inv, sort_keys=True).encode()).hexdigest()
    production_scope = any(c.get('reviewed') for c in contexts) or any(p.endswith(('.permissionset-meta.xml', '.profile-meta.xml', '.flow-meta.xml', '.page', '.component')) for p in files)
    if not production_scope:
        issues.append({'path': '.', 'reason': 'no_production_components_analysed'})
    counts = Counter(f['owasp'][:3] for f in findings)
    from .impact import build_graph
    graph=build_graph(files,findings)
    return {'schema_version': 'sfg.report.v2', 'id': uuid.uuid4().hex, 'created_at': datetime.now(timezone.utc).isoformat(),
        'tool_version': __version__, 'project_name': root.name, 'snapshot_sha256': snapshot, 'effective_user_access_status': 'not_assessed',
        'scan_status': 'incomplete' if issues or not files else 'completed_with_limits',
        'engine': 'salesforce-guard-local-heuristics', 'findings': findings, 'inventory': inv,
        'impact':graph,'contexts': contexts, 'issues': issues, 'summary': {'files': len(files), 'findings': len(findings),
            'confirmed_vulnerabilities': 0, 'requires_review': len(findings)},
        'owasp': [{'id': k + ':2025', 'name': v[0], 'coverage': v[1], 'scope': v[2], 'findings': counts[k]} for k, v in OWASP.items()],
        'external_sast': {'status': 'not_run', 'reason': 'Run the optional Code Analyzer adapter explicitly; local triage is not Salesforce Code Analyzer.'},
        'limitations': ['Lexical heuristics, not a full Apex parser or interprocedural analysis.',
            'Local source scanning does not query an org or prove effective authorization. Optional selected-user evidence is separately collected and scoped.',
            'No findings does not establish security. All findings require human qualification.',
            'Test classes are inventoried but excluded from heuristic findings. Symlinks/junctions and generated directories are excluded.',
            'OWASP mapping is partial and contextual, not certification or complete Top 10 coverage.'], 'sources': SOURCES}
