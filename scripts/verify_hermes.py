"""Operator verification using the installed Hermes runtime, no model or live org.

This harness uses Doctor's own isolation context. Private helpers are test-only;
the shipped plugin itself uses exclusively supported registration/storage APIs.
"""
import argparse
import hashlib
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plugin', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--timeout',type=int,default=120,help='Outer host-check timeout in seconds (5 to 600).')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args = parser.parse_args()
    if (Path(args.plugin)/'.runtime').exists() or (Path(args.plugin)/'output').exists():
        parser.error('Use the source-only dist/salesforce-guard directory after scripts/package.py. Doctor copies its input; the development workspace contains private runtime caches and live output.')
    if not 5<=args.timeout<=600:parser.error('Timeout must be 5 to 600 seconds')
    if not args.worker:
        root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
        from salesforce_guard.analyzer import _execute
        try:
            code=_execute([sys.executable,'-u',str(Path(__file__).resolve()),'--plugin',str(Path(args.plugin).resolve()),'--output',str(Path(args.output).resolve()),'--worker'],root,os.environ.copy(),sys.stdout,sys.stderr,args.timeout)
        except subprocess.TimeoutExpired:
            code=2
        if code:
            failed={'status':'failed_or_timed_out','completion':'not_established','exit_code':code}
            out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(failed,indent=2),encoding='utf-8')
            print(json.dumps(failed),flush=True)
        return code
    build=Path(args.plugin)/'BUILD.json'
    if build.is_file():
        inventory=json.loads(build.read_text(encoding='utf-8'))['source_sha256']
        for relative,expected in inventory.items():
            source=Path(args.plugin)/relative
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=expected:
                raise ValueError('Installed bundle is missing or changed: '+relative)
        print('stage: installed bundle hashes verified',flush=True)
    print('stage: import Hermes verification modules',flush=True)
    from hermes_cli.plugin_dev import doctor_plugin, _doctor_runtime
    from hermes_cli.plugin_validate import validate_plugin_dir
    print('stage: Doctor',flush=True)
    report = doctor_plugin(args.plugin)
    print('stage: catalog validation',flush=True)
    receipt = {'doctor': asdict(report), 'validation': asdict(validate_plugin_dir(Path(args.plugin))), 'runtime_calls': []}
    print('stage: registered tool runtime',flush=True)
    with _doctor_runtime(Path(args.plugin).resolve()) as runtime:
        for name in ('sfg_demo', 'sfg_impact','sfg_access', 'terminal', 'mcp__salesforce__execute_apex', 'mcp__salesforce__deploy', 'send_message'):
            directives = runtime.manager.invoke_hook('pre_tool_call', tool_name=name, args={}, task_id='sfg-verification')
            blocked = any(isinstance(d, dict) and d.get('action') == 'block' for d in directives)
            expected = name not in {'sfg_demo','sfg_impact','sfg_access'}
            assert blocked == expected, (name, directives)
            receipt['runtime_calls'].append({'tool': name, 'blocked': blocked, 'actual_tool_executed': False})
        # Run the actual registered tool handler, not a parallel imitation of it.
        receipt['schema_discovery_boundary'] = []
        for names, expected in ((['sfg_compare_demo','sfg_changes','sfg_impact','sfg_access'],False),
                                (['sfg_access','terminal'],True),(['mcp__salesforce__query'],True)):
            directives = runtime.manager.invoke_hook('pre_tool_call',tool_name='tool_describe',args={'names':names},task_id='sfg-verification')
            blocked = any(isinstance(d,dict) and d.get('action')=='block' for d in directives)
            assert blocked == expected, (names,directives)
            receipt['schema_discovery_boundary'].append({'names':names,'blocked':blocked})
        from tools.registry import registry
        entry = registry.get_entry('sfg_demo')
        if entry is None:
            entries = [e for e in registry._snapshot_entries() if e.name == 'sfg_demo']
            entry = entries[0] if entries else None
        assert entry is not None, 'Registered demo tool not found'
        result = json.loads(entry.handler({}))
        assert 'error' not in result, result
        assert result['summary']['findings'] > 0, result
        receipt['registered_demo_tool'] = {'report_id': result['report_id'], 'summary': result['summary'], 'scan_status': result['scan_status']}
        impact=registry.get_entry('sfg_impact')
        assert impact is not None
        listing=json.loads(impact.handler({'report_id':result['report_id']}))
        assert listing.get('nodes'),listing
        selected=next(n['id'] for n in listing['nodes'] if n['kind']=='apex_method')
        impact_result=json.loads(impact.handler({'report_id':result['report_id'],'focus':selected,'depth':2}))
        assert impact_result.get('edges'),impact_result
        receipt['registered_impact_tool']={'focus':selected,'nodes':len(impact_result['nodes']),'connections':len(impact_result['edges']),'notice':impact_result['notice']}
        comparison=registry.get_entry('sfg_compare_demo')
        assert comparison is not None
        change_result=json.loads(comparison.handler({}))
        assert change_result.get('summary')=={'new':1,'modified':2,'destructive':1,'unchanged':1,'unknown':0,'conflict':0},change_result
        changes=registry.get_entry('sfg_changes')
        rows=json.loads(changes.handler({'report_id':change_result['report_id']}))
        assert len(rows.get('rows',[]))==5,rows
        before=json.loads(impact.handler({'report_id':change_result['report_id'],'comparison_side':'before','focus':'apex:oldexpenseutility'}))
        assert before.get('edges'),before
        receipt['registered_comparison_tools']={'summary':change_result['summary'],'change_rows':len(rows['rows']),'deletion_before_connections':len(before['edges'])}
        access=registry.get_entry('sfg_access');assert access is not None
        access_result=json.loads(access.handler({}))
        assert access_result.get('summary')=={'allowed':3,'denied':8,'unknown':0},access_result
        receipt['registered_access_tool']={'summary':access_result['summary'],'status':access_result['status'],'rows':len(access_result['rows'])}
        # Prove folder approval in the actual registered handler, not only a helper.
        import tempfile
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
        from salesforce_guard.input_approvals import update_approval
        policy_result=json.loads(registry.get_entry('sfg_policy').handler({}))
        policy_file=policy_result['input_boundary']['policy_file']
        with tempfile.TemporaryDirectory(prefix='sfg-approved-input-') as scratch:
            source=Path(scratch).resolve();(source/'Example.cls').write_text('public with sharing class Example {}',encoding='utf-8')
            denied=json.loads(registry.get_entry('sfg_scan').handler({'project_path':str(source)}))
            assert 'not approved' in denied.get('error',''),denied
            update_approval(policy_file,source,approve=True,model_sharing=True)
            allowed=json.loads(registry.get_entry('sfg_scan').handler({'project_path':str(source)}))
            assert 'error' not in allowed,allowed
            update_approval(policy_file,source,approve=False)
            revoked=json.loads(registry.get_entry('sfg_scan').handler({'project_path':str(source)}))
            assert 'not approved' in revoked.get('error',''),revoked
        receipt['native_input_approval']={'unapproved_denied':True,'operator_approved_read':True,'revoked_denied':True,'agent_approval_tool':False}
        # Exercise the host's pre-dispatch gate as well as the raw hook callback.
        from model_tools import handle_function_call
        sentinel = Path(args.output).resolve().parent / 'FORBIDDEN_TOOL_MUST_NOT_RUN.txt'
        assert not sentinel.exists(), 'Use a fresh verification output directory'
        from hermes_cli import plugins
        with patch.object(plugins, '_delivery_manager', return_value=runtime.manager):
            result = handle_function_call('terminal', {'command': 'echo guard-probe', 'workdir': str(Path(args.output).resolve().parent)}, task_id='sfg-verification')
        assert 'Salesforce Guard' in str(result) and 'blocked' in str(result).lower(), result
        receipt['host_dispatch_probe'] = {'tool': 'terminal', 'requested_command': 'echo guard-probe',
            'blocked_before_execution': True, 'result': result}
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(receipt, indent=2, default=str), encoding='utf-8')
    print(json.dumps(receipt, indent=2, default=str))
    failures = [f for f in receipt['doctor']['findings'] if f['level'] == 'error']
    failures += [check for check in receipt['validation']['checks'] if not check[1]]
    return 1 if failures else 0


if __name__ == '__main__': raise SystemExit(main())
