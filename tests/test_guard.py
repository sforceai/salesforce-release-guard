import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from salesforce_guard.analyzer import parse_output, run_analyzer
from salesforce_guard.lexer import mask, safe_excerpt
from salesforce_guard.policy import TOOLS, decision
from salesforce_guard.report import render_html, save_report
from salesforce_guard.scan import scan_project

ROOT = Path(__file__).resolve().parents[1]


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def apex(self, content, version=66, name='Review.cls'):
        path = self.root / name
        path.write_text(content, encoding='utf-8')
        if version is not None:
            Path(str(path) + '-meta.xml').write_text(f'<ApexClass><apiVersion>{version}</apiVersion></ApexClass>')
        return path

    def rules(self):
        return [f['rule'] for f in scan_project(self.root)['findings']]

    def test_legacy_query_is_review_not_confirmed_defect(self):
        self.apex('public with sharing class Review { List<Account> a = [SELECT Id FROM Account]; }')
        report = scan_project(self.root)
        self.assertIn('APEX002', self.rules())
        self.assertEqual(report['summary']['confirmed_vulnerabilities'], 0)
        self.assertTrue(all(f['status'] == 'requires_review' for f in report['findings']))

    def test_api67_implicit_query_not_legacy_flag(self):
        self.apex('public class Review { List<Account> a = [SELECT Id FROM Account]; }', 67)
        self.assertNotIn('APEX002', self.rules())

    def test_explicit_system_operation_is_signal_in_api67(self):
        self.apex('public with sharing class Review { List<Account> a = [SELECT Id FROM Account WITH SYSTEM_MODE]; }', 67)
        self.assertIn('APEX001', self.rules())

    def test_user_mode_not_legacy_flag(self):
        self.apex('public class Review { List<Account> a = [SELECT Id FROM Account WITH USER_MODE]; update as user accounts; }', 66)
        self.assertNotIn('APEX002', self.rules())

    def test_trigger_default_is_separate(self):
        self.apex('trigger Review on Account (before insert) { List<Account> a = [SELECT Id FROM Account]; }', 67, 'Review.trigger')
        report = scan_project(self.root)
        self.assertIn('APEX002', self.rules())
        self.assertEqual(report['contexts'][0]['default_mode'], 'trigger_system_context')

    def test_without_sharing_not_itself_fls_bypass(self):
        self.apex('public without sharing class Review { List<Account> a = [SELECT Id FROM Account WITH USER_MODE]; }', 67)
        self.assertEqual(self.rules(), ['APEX003'])

    def test_comments_and_literals_do_not_trigger_operation_rules(self):
        self.apex("// WITH SYSTEM_MODE\n/* without sharing */\npublic class Review { String note = 'WITH SYSTEM_MODE without sharing System.debug('; }", 67)
        self.assertEqual(self.rules(), [])

    def test_dynamic_query_concat(self):
        self.apex("public class Review { void go(String input) { Database.query('SELECT Id FROM Account WHERE Name = ' + input); } }", 67)
        self.assertIn('APEX004', self.rules())

    def test_plus_inside_query_literal_is_not_concat(self):
        self.apex("public class Review { void go() { Database.query('SELECT Id FROM Account WHERE Name = \\'a+b\\''); } }", 67)
        self.assertNotIn('APEX004', self.rules())

    def test_secret_redaction(self):
        secret = 'example-secret-do-not-leak'
        self.apex(f"public class Review {{ String clientSecret = '{secret}'; }}", 67)
        report = scan_project(self.root)
        self.assertIn('APEX008', self.rules())
        self.assertNotIn(secret, json.dumps(report))
        self.assertNotIn(secret, render_html(report))

    def test_digest_and_empty_catch(self):
        self.apex("public class Review { void go() { Crypto.generateDigest('MD5', payload); try {} catch (Exception e) { /* ignored */ } } }", 67)
        self.assertIn('APEX005', self.rules())
        self.assertIn('APEX006', self.rules())

    def test_nonempty_catch_not_flagged(self):
        self.apex('public class Review { void go() { try {} catch (Exception e) { throw e; } } }', 67)
        self.assertNotIn('APEX006', self.rules())

    def test_test_classes_inventoried_not_flagged(self):
        self.apex('@IsTest public without sharing class Review {}')
        report = scan_project(self.root)
        self.assertEqual(report['summary']['files'], 2)
        self.assertEqual(report['findings'], [])
        self.assertFalse(report['contexts'][0]['reviewed'])

    def test_unknown_api_is_incomplete(self):
        self.apex('public class Review {}', None)
        report = scan_project(self.root)
        self.assertEqual(report['scan_status'], 'incomplete')
        self.assertEqual(report['issues'][0]['reason'], 'unknown_api_version')

    def test_invalid_api_is_incomplete(self):
        self.apex('public class Review {}', 'not-a-version')
        self.assertEqual(scan_project(self.root)['scan_status'], 'incomplete')

    def test_broad_permissions_and_field_edits(self):
        (self.root / 'Access.permissionset-meta.xml').write_text('<PermissionSet><userPermissions><name>ModifyAllData</name><enabled>true</enabled></userPermissions><objectPermissions><object>Account</object><modifyAllRecords>true</modifyAllRecords></objectPermissions><fieldPermissions><field>Account.Name</field><editable>true</editable></fieldPermissions></PermissionSet>')
        self.assertEqual(set(self.rules()), {'META001', 'META002', 'META003'})

    def test_disabled_grants_not_findings(self):
        (self.root / 'Access.permissionset-meta.xml').write_text('<PermissionSet><userPermissions><name>ModifyAllData</name><enabled>false</enabled></userPermissions></PermissionSet>')
        self.assertEqual(self.rules(), [])

    def test_flow_context(self):
        (self.root / 'Review.flow-meta.xml').write_text('<Flow><runInMode>SystemModeWithoutSharing</runInMode></Flow>')
        self.assertIn('FLOW001', self.rules())

    def test_visualforce_comment_ignored(self):
        (self.root / 'Review.page').write_text('<!-- escape="false" --><apex:page><apex:outputText escape="true" /></apex:page>')
        self.assertEqual(self.rules(), [])

    def test_xml_entities_rejected(self):
        (self.root / 'Review.flow-meta.xml').write_text('<!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]><Flow>&x;</Flow>')
        report = scan_project(self.root)
        self.assertEqual(report['scan_status'], 'incomplete')
        self.assertEqual(report['findings'], [])

    def test_empty_project_incomplete(self):
        self.assertEqual(scan_project(self.root)['scan_status'], 'incomplete')

    def test_unsupported_files_not_read(self):
        (self.root / '.env').write_text('PRIVATE_VALUE=do-not-read')
        self.apex('public class Review {}', 67)
        self.assertNotIn('do-not-read', json.dumps(scan_project(self.root)))

    def test_generated_directories_excluded(self):
        (self.root / 'node_modules').mkdir()
        (self.root / 'node_modules' / 'bad.cls').write_text('without sharing')
        self.apex('public class Review {}', 67)
        self.assertEqual(scan_project(self.root)['summary']['files'], 2)

    def test_oversized_file_recorded(self):
        self.apex('public class Review {}', 67)
        with patch('salesforce_guard.scan.MAX_FILE', 8):
            report = scan_project(self.root)
        self.assertEqual(report['scan_status'], 'incomplete')
        self.assertTrue(any(i['reason'] == 'file_size_limit' for i in report['issues']))

    def test_snapshot_changes_with_metadata(self):
        self.apex('public class Review {}', 66)
        old = scan_project(self.root)['snapshot_sha256']
        self.apex('public class Review {}', 67)
        self.assertNotEqual(scan_project(self.root)['snapshot_sha256'], old)

    def test_report_escapes_markup(self):
        self.apex('public class Review {}', 67)
        report = scan_project(self.root)
        report['project_name'] = '<script>alert(1)</script>'
        rendered = render_html(report)
        self.assertNotIn('<script>alert(1)</script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertNotIn('src="https://', rendered)

    def test_owasp_all_ten_with_honest_gaps(self):
        self.apex('public class Review {}', 67)
        categories = scan_project(self.root)['owasp']
        self.assertEqual(len(categories), 10)
        self.assertTrue(any(c['coverage'] == 'not_assessed' for c in categories))

    def test_report_saved_separately(self):
        self.apex('public class Review {}', 67)
        report = scan_project(self.root)
        destination = save_report(report, self.root / 'output')
        self.assertEqual(json.loads((destination / 'report.json').read_text())['id'], report['id'])
        self.assertTrue((destination / 'report.html').exists())

    def test_symlink_not_followed(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'Secret.cls'
            target.write_text('public without sharing class Secret {}')
            try:
                (self.root / 'Linked.cls').symlink_to(target)
            except OSError:
                self.skipTest('OS does not permit symlink creation')
            report = scan_project(self.root)
            self.assertEqual(report['findings'], [])
            self.assertEqual(report['scan_status'], 'incomplete')

    def test_reparse_directory_excluded_without_traversal(self):
        child = self.root / 'junction'
        child.mkdir()
        (child / 'Hidden.cls').write_text('public without sharing class Hidden {}')
        with patch('salesforce_guard.scan.linked', side_effect=lambda p: p.name == 'junction'):
            report = scan_project(self.root)
        self.assertEqual(report['summary']['files'], 0)
        self.assertTrue(any(i['reason'] == 'linked_directory_skipped' for i in report['issues']))

    def test_linked_source_root_rejected(self):
        with patch('salesforce_guard.scan.linked', return_value=True):
            with self.assertRaises(ValueError): scan_project(self.root)


class PolicyTests(unittest.TestCase):
    def test_owned_tools_allowed(self):
        for tool in TOOLS:
            self.assertIsNone(decision(tool))

    def test_foreign_tools_denied_regardless_of_name_or_arguments(self):
        for tool in ('terminal', 'read_file', 'write_file', 'execute_code', 'mcp__salesforce__query', 'mcp__salesforce__execute_apex', 'mcp__salesforce__deploy', 'browser', 'send_message', 'sfg_scan_evil', 'SFG_SCAN', '', None, [], {}):
            self.assertEqual(decision(tool)['action'], 'block', repr(tool))

    def test_discovery_allowed(self):
        for tool in ('tool_search', 'skills_list', 'skill_view'):
            self.assertIsNone(decision(tool))

    def test_native_registration_and_handler_contract(self):
        spec = importlib.util.spec_from_file_location('sfg_plugin_test', ROOT / '__init__.py', submodule_search_locations=[str(ROOT)])
        module = importlib.util.module_from_spec(spec)
        import sys
        sys.modules[spec.name] = module
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(module)
        class Context:
            def __init__(self): self.tools, self.hooks = {}, {}
            def register_tool(self, **kw): self.tools[kw['name']] = kw
            def register_hook(self, name, callback): self.hooks[name] = callback
        ctx = Context()
        module.register(ctx)
        self.assertEqual(set(ctx.tools), TOOLS)
        self.assertEqual(ctx.hooks['pre_tool_call'](tool_name='terminal', args={'command': 'anything'})['action'], 'block')
        self.assertEqual(json.loads(ctx.tools['sfg_policy']['handler']({}))['mode'], 'restricted_review_profile')
        self.assertIn('error', json.loads(ctx.tools['sfg_scan']['handler']({'project_path': '.'})))
        self.assertIn('error', json.loads(ctx.tools['sfg_report']['handler']({'report_id': '../../secret'})))


class AnalyzerTests(unittest.TestCase):
    def test_parse_current_schema_preserves_engine_findings(self):
        data = {'versions': {'code-analyzer': '5.test'}, 'violations': [{'rule': 'ApexCRUDViolation', 'engine': 'pmd', 'severity': 2, 'message': 'Review required', 'locations': []}]}
        parsed = parse_output(data)
        self.assertEqual(parsed['raw_count'], 1)
        self.assertEqual(parsed['confirmed_vulnerabilities'], 0)

    def test_bad_schema_not_empty_success(self):
        for data in ({}, [], {'versions': {}, 'violations': [{}]}, {'versions': {}, 'violations': [{'rule': 'x', 'severity': 99}]}):
            with self.assertRaises(ValueError): parse_output(data)

    def test_uninstalled_jit_plugin_does_not_run_scan(self):
        calls = []
        def execute(args, cwd, env, stdout, stderr, timeout):
            calls.append(args)
            stdout.write(json.dumps([{'name': '@salesforce/plugin-code-analyzer', 'type': 'jit', 'version': '5.15.0'}]).encode())
            return 0
        with tempfile.TemporaryDirectory() as out, patch('salesforce_guard.analyzer._execute', side_effect=execute):
            receipt = run_analyzer(ROOT / 'examples/risky-project', out, ['native-sf.exe'])
            self.assertEqual(receipt['status'], 'unavailable')
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][-2:], ['plugins', '--json'])

    def test_engine_error_does_not_become_success(self):
        def execute(args, cwd, env, stdout, stderr, timeout):
            if args[-2:] == ['plugins', '--json']:
                stdout.write(json.dumps([{'name': '@salesforce/plugin-code-analyzer', 'type': 'link', 'root': 'installed', 'version': '5.15.0'}]).encode())
            else:
                Path(args[-1]).write_text(json.dumps({'versions': {'pmd': 'test'}, 'violations': []}))
                stderr.write(b'InternalExecutionError: incomplete analysis')
            return 0
        with tempfile.TemporaryDirectory() as out, patch('salesforce_guard.analyzer._execute', side_effect=execute):
            receipt = run_analyzer(ROOT / 'examples/risky-project', out, ['native-sf.exe'])
            self.assertEqual(receipt['status'], 'incomplete')

    def test_missing_executable_recorded(self):
        with tempfile.TemporaryDirectory() as out:
            receipt = run_analyzer(ROOT / 'examples/risky-project', out, ['nonexistent-salesforce-guard-cli'])
            self.assertEqual(receipt['status'], 'failed')
            self.assertTrue((Path(out) / 'receipt.json').exists())

    def test_timeout_not_success(self):
        import subprocess
        with tempfile.TemporaryDirectory() as out, patch('salesforce_guard.analyzer._execute', side_effect=subprocess.TimeoutExpired('sf', 1)):
            receipt = run_analyzer(ROOT / 'examples/risky-project', out, ['native-sf.exe'], 1)
            self.assertEqual(receipt['status'], 'timeout')


if __name__ == '__main__':
    unittest.main()
