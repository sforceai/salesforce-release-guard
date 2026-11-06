import argparse
import json
from pathlib import Path
import sys

from .analyzer import run_analyzer
from .policy import decision, status
from .report import save_report
from .scan import scan_project
from .impact import query_graph
from .compare import compare_snapshots
from .comparison_view import save_comparison


def main(argv=None):
    parser = argparse.ArgumentParser(description='Salesforce Guard: local review and explicit operator-only org capture.')
    commands = parser.add_subparsers(dest='command', required=True)
    scan = commands.add_parser('scan', help='Scan supplied Salesforce source and generate HTML/JSON.')
    scan.add_argument('project')
    scan.add_argument('--output', default='output')
    scan.add_argument('--fail-on', choices=['high', 'medium', 'low'])
    scan.add_argument('--with-code-analyzer', action='store_true', help='Explicitly run an installed CLI; never available to agent tools.')
    scan.add_argument('--sf-bin', help='Path to an installed native sf executable (not a shell wrapper).')
    scan.add_argument('--node', help='Windows: installed Node executable.')
    scan.add_argument('--sf-js', help='Windows: installed Salesforce CLI bin/run.js.')
    scan.add_argument('--timeout', type=int, default=180)
    scan.add_argument('--access-evidence',help='Explicit local selected-user configuration evidence; not runtime proof.')
    demo = commands.add_parser('demo', help='Scan fictional examples and demonstrate policy decisions.')
    demo.add_argument('--output', default='output')
    policy = commands.add_parser('policy', help='Inspect or evaluate the review-only tool gate.')
    policy.add_argument('--tool')
    impact=commands.add_parser('impact',help='Explore dependencies in an existing report JSON.')
    impact.add_argument('report')
    impact.add_argument('--focus')
    impact.add_argument('--direction',choices=['upstream','downstream','both'],default='both')
    impact.add_argument('--depth',type=int,default=2)
    compare=commands.add_parser('compare',help='Compare two snapshots with explicit release/deletion intent; never deploy.')
    compare.add_argument('candidate'); compare.add_argument('destination')
    compare.add_argument('--scope'); compare.add_argument('--delete-pre'); compare.add_argument('--delete-post')
    compare.add_argument('--output',default='output')
    compare.add_argument('--before-access');compare.add_argument('--after-access')
    compare_demo=commands.add_parser('compare-demo',help='Run the fictional two-snapshot release example.')
    compare_demo.add_argument('--output',default='output')
    org=commands.add_parser('org',help='Operator-only browser OAuth and scoped metadata capture through installed Salesforce CLI.')
    org.add_argument('--state-dir',default='.sfg-connections');org.add_argument('--sf-bin');org.add_argument('--node');org.add_argument('--sf-js')
    org_actions=org.add_subparsers(dest='org_action',required=True)
    login=org_actions.add_parser('login');login.add_argument('role',choices=['source','destination']);login.add_argument('--instance-url',required=True);login.add_argument('--expected-org-id',required=True);login.add_argument('--client-id')
    org_status=org_actions.add_parser('status');org_status.add_argument('--verify',action='store_true')
    disconnect=org_actions.add_parser('disconnect');disconnect.add_argument('role',choices=['source','destination']);disconnect.add_argument('--revoke',action='store_true')
    capture=org_actions.add_parser('capture');capture.add_argument('role',choices=['source','destination']);capture.add_argument('--manifest',required=True);capture.add_argument('--output',default='output/snapshots')
    access=org_actions.add_parser('access',help='Collect scoped configuration access for an explicitly selected user; no writes.')
    access.add_argument('role',choices=['source','destination']);access.add_argument('--user-id',required=True);access.add_argument('--scope',required=True);access.add_argument('--output',default='output/access')
    access_report=commands.add_parser('access-report',help='Render local scoped access evidence without org access.')
    access_report.add_argument('evidence');access_report.add_argument('--output',default='output')
    access_demo=commands.add_parser('access-demo',help='Generate a fictional selected-user access report; no credentials or org calls.')
    access_demo.add_argument('--output',default='output')
    inputs=commands.add_parser('inputs',help='Operator-only native input-folder approvals; never an agent tool.')
    inputs.add_argument('action',choices=['approve','revoke','status'])
    inputs.add_argument('--policy-file',required=True,help='Absolute input-approvals.json location from native sfg_policy.')
    inputs.add_argument('--root',help='Absolute project folder to approve or revoke.')
    inputs.add_argument('--allow-model-sharing',action='store_true',help='Acknowledge that requested excerpts/evidence go to the selected Hermes model.')
    args = parser.parse_args(argv)
    try:
        if args.command=='inputs':
            from .input_boundary import approval_status, POLICY_NAME
            if Path(args.policy_file).name!=POLICY_NAME or not Path(args.policy_file).is_absolute():
                raise ValueError('Use the absolute input-approvals.json location from sfg_policy.')
            if args.action=='status':result=approval_status(Path(args.policy_file).parent)
            else:
                from .input_approvals import update_approval
                result=update_approval(args.policy_file,args.root,approve=args.action=='approve',model_sharing=args.allow_model_sharing)
            print(json.dumps(result,indent=2));return 0
        if args.command=='org':
            from .orgs import OrgBridge,CliTransport,cli_command
            bridge=OrgBridge(args.state_dir,CliTransport(cli_command(args.node,args.sf_js,args.sf_bin)))
            if args.org_action=='login': result=bridge.login(args.role,args.instance_url,args.expected_org_id,args.client_id)
            elif args.org_action=='status': result=bridge.status(args.verify)
            elif args.org_action=='disconnect': result=bridge.disconnect(args.role,args.revoke)
            elif args.org_action=='capture': result=bridge.capture(args.role,args.manifest,args.output)
            else:
                from .access import load_json
                from .access_capture import collect_access
                result=collect_access(bridge,args.role,args.user_id,load_json(args.scope),args.output)
            print(json.dumps(result,indent=2));return 0
        if args.command in {'access-report','access-demo'}:
            from .access import load_evidence,save_access
            if args.command=='access-demo':
                from .access_demo import demo_evidence
                import uuid
                folder=Path(args.output)/uuid.uuid4().hex;folder.mkdir(parents=True,exist_ok=False)
                evidence=folder/'fictional-access-evidence.json';evidence.write_text(json.dumps(demo_evidence()),encoding='utf-8')
            else:evidence=args.evidence
            report=load_evidence(evidence);dest=save_access(report,args.output)
            print(json.dumps({'report':str((dest/'access.html').resolve()),'json':str((dest/'access.json').resolve()),'summary':report['summary'],'status':report['status']},indent=2));return 0
        if args.command in {'compare','compare-demo'}:
            if args.command=='compare-demo':
                base=Path(__file__).resolve().parents[1]/'examples'/'release-demo'
                report=compare_snapshots(base/'candidate',base/'destination',base/'package.xml',delete_post=base/'destructiveChangesPost.xml')
            else: report=compare_snapshots(args.candidate,args.destination,args.scope,args.delete_pre,args.delete_post)
            if args.command=='compare' and (args.before_access or args.after_access):
                from .access import attach_access
                if args.before_access:attach_access(report,args.before_access,'before')
                if args.after_access:attach_access(report,args.after_access,'after')
            destination=save_comparison(report,args.output)
            print(json.dumps({'report':str((destination/'comparison.html').resolve()),'json':str((destination/'comparison.json').resolve()),'summary':report['summary'],'review_status':report['review_status']},indent=2))
            return 2 if report['review_status']=='incomplete' else 0
        if args.command=='impact':
            path=Path(args.report)
            if path.stat().st_size>16*1024*1024: raise ValueError('Report exceeds impact-tool size limit')
            graph=json.loads(path.read_text(encoding='utf-8')).get('impact')
            if not graph: raise ValueError('Rescan with version 0.2.0 to generate impact data')
            result=query_graph(graph,args.focus,args.direction,args.depth) if args.focus else {'nodes':graph['nodes'],'notice':graph['notice']}
            print(json.dumps(result,indent=2)); return 0
        if args.command == 'policy':
            result = status()
            if args.tool:
                result['evaluation'] = decision(args.tool) or {'action': 'allow'}
            print(json.dumps(result, indent=2))
            return 0
        root = Path(__file__).resolve().parents[1] / 'examples' / 'risky-project' if args.command == 'demo' else Path(args.project)
        report = scan_project(root)
        if args.command=='scan' and args.access_evidence:
            from .access import attach_access
            attach_access(report,args.access_evidence)
        if args.command == 'scan' and args.with_code_analyzer:
            if bool(args.node) != bool(args.sf_js):
                parser.error('--node and --sf-js must be supplied together')
            if not 1 <= args.timeout <= 600:
                parser.error('--timeout must be between 1 and 600 seconds')
            command = [str(Path(args.node).resolve()), str(Path(args.sf_js).resolve())] if args.node else [args.sf_bin] if args.sf_bin else None
            external = run_analyzer(root, Path(args.output) / 'external' / report['id'], command, args.timeout)
            expected = {f['path']: f['sha256'] for f in report['inventory']}
            if external.get('source_hashes') and external['source_hashes'] != expected:
                external.update(status='source_changed', reason='Source changed between local and external scans; do not combine as one snapshot.')
            report['external_sast'] = external
        destination = save_report(report, args.output)
        print(json.dumps({'report': str((destination / 'report.html').resolve()),
                          'json': str((destination / 'report.json').resolve()), 'status': report['scan_status'],
                          'summary': report['summary'], 'external_sast': report['external_sast']['status']}, indent=2))
        if args.command == 'demo':
            print('\nPolicy demonstration (evaluation only; no proposed action is executed):')
            for tool in ('sfg_scan', 'terminal', 'mcp__salesforce__execute_apex', 'mcp__salesforce__deploy', 'send_message'):
                print(f"  {tool}: {(decision(tool) or {'action': 'allow'})['action']}")
        if report['scan_status'] == 'incomplete':
            return 2
        if args.command == 'scan':
            if args.with_code_analyzer and report['external_sast']['status'] != 'process_completed_requires_review':
                return 2
            if args.fail_on:
                levels = {'high': 0, 'medium': 1, 'low': 2}
                if any(levels[f['severity']] <= levels[args.fail_on] for f in report['findings']):
                    return 1
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({'error': str(exc), 'status': 'failed'}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
