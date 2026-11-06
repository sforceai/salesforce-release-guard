import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from salesforce_guard.orgs import OrgBridge,CliTransport,salesforce_login_url,org_id,cli_command,QUERY
from salesforce_guard.snapshot import load_snapshot
from test_comparison import manifest

SOURCE='00D000000000001';TARGET='00D000000000002'


class FakeCli:
    def __init__(self): self.calls=[];self.aliases={};self.wrong=False;self.pending=False;self.limit=False
    def run(self,args,cwd,timeout=120,json_output=True):
        self.calls.append(args)
        if args[:3]==['org','login','web']:
            alias=args[args.index('--alias')+1]
            url=args[args.index('--instance-url')+1]
            self.aliases[alias]=SOURCE if 'source' in url else TARGET
            return None
        alias=args[args.index('--target-org')+1]
        if args[:2]==['data','query']:
            return {'records':[{'Id':TARGET if self.wrong else self.aliases[alias],'IsSandbox':True,'ignored_private_field':'not-persisted'}]}
        if args[:3]==['org','list','metadata']:
            return [{'fullName':'Service'}]*1000 if self.limit else [{'fullName':'Service'}]
        if args[:3]==['project','retrieve','start']:
            out=Path(args[args.index('--output-dir')+1])/'classes';out.mkdir()
            (out/'Service.cls').write_text('public class Service { public static void go() {} }')
            (out/'Service.cls-meta.xml').write_text('<ApexClass><apiVersion>67.0</apiVersion></ApexClass>')
            return {'done':not self.pending,'success':not self.pending}
        if args[:2]==['org','logout']: return None
        raise AssertionError(args)


class OrgTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.cli=FakeCli();self.bridge=OrgBridge(self.root/'connections',self.cli)

    def connect(self,role='source'):
        return self.bridge.login(role,'https://'+role+'-example.my.salesforce.com',SOURCE if role=='source' else TARGET)

    def test_login_url_allowlist(self):
        for url in ['https://login.salesforce.com','https://test.salesforce.com','https://fictional.my.salesforce.com','https://fictional--dev.sandbox.my.salesforce.com']:
            self.assertEqual(salesforce_login_url(url),url)

    def test_host_spoofing_and_token_urls_rejected(self):
        for url in ['http://login.salesforce.com','https://login.salesforce.com.evil.invalid','https://user:password@login.salesforce.com','https://localhost','https://login.salesforce.com?token=secret','https://login.salesforce.com:443','https://example.my.salesforce.com/services/oauth2/token']:
            with self.assertRaises(ValueError): salesforce_login_url(url)

    def test_org_id_validation(self):
        self.assertEqual(org_id(SOURCE+'ABC'),SOURCE)
        for value in ['not-an-org','005000000000001',None]:
            with self.assertRaises(ValueError):org_id(value)

    def test_two_roles_have_distinct_aliases_and_expected_ids(self):
        a=self.connect();b=self.connect('destination')
        self.assertNotEqual(a['alias'],b['alias']);self.assertNotEqual(a['org_id'],b['org_id'])
        state=json.loads(self.bridge.path.read_text())
        self.assertEqual(set(state),{'source','destination'})
        self.assertNotIn('ignored_private_field',self.bridge.path.read_text())

    def test_no_default_org_or_auth_display_used(self):
        self.connect()
        flat=' '.join(' '.join(a) for a in self.cli.calls)
        self.assertNotIn('--set-default',flat);self.assertNotIn('org display',flat)
        self.assertNotIn('show-access-token',flat)

    def test_wrong_org_never_committed(self):
        self.cli.wrong=True
        with self.assertRaises(ValueError): self.connect()
        self.assertFalse(self.bridge.path.exists())

    def test_same_org_cannot_fill_both_roles(self):
        self.connect()
        with self.assertRaises(ValueError): self.bridge.login('destination','https://source-example.my.salesforce.com',SOURCE)

    def test_status_verifies_identity_on_request(self):
        self.connect();self.assertTrue(self.bridge.status(True)['source']['identity_checked_now'])
        self.cli.wrong=True
        with self.assertRaises(ValueError): self.bridge.status(True)

    def test_local_disconnect_does_not_revoke_other_cli_use(self):
        self.connect();self.bridge.disconnect('source')
        self.assertEqual(self.bridge.status(),{})
        self.assertFalse(any(a[:2]==['org','logout'] for a in self.cli.calls))

    def test_explicit_revoke_targets_only_bound_alias(self):
        c=self.connect();self.bridge.disconnect('source',True)
        self.assertIn(['org','logout','--target-org',c['alias'],'--no-prompt'],self.cli.calls)

    def test_capture_has_pinned_identity_and_hashes(self):
        self.connect();scope=manifest(self.root/'package.xml',[('ApexClass','Service'),('ApexClass','NewPolicy')])
        result=self.bridge.capture('source',scope,self.root/'snapshots')
        snap=load_snapshot(result['snapshot_path'])
        self.assertEqual(snap.state('|ApexClass|Service'),'present')
        self.assertEqual(snap.state('|ApexClass|NewPolicy'),'absent')
        self.assertEqual(snap.provenance['org_id'],SOURCE)
        self.assertFalse(snap.issues)
        self.assertEqual(sum(a[:2]==['data','query'] for a in self.cli.calls),3)

    def test_retargeted_alias_blocks_capture(self):
        self.connect();self.cli.wrong=True
        scope=manifest(self.root/'package.xml',[('ApexClass','Service')])
        with self.assertRaises(ValueError):self.bridge.capture('source',scope,self.root/'snapshots')
        self.assertFalse(any(a[:3]==['project','retrieve','start'] for a in self.cli.calls))

    def test_pending_retrieve_not_promoted(self):
        self.connect();self.cli.pending=True
        scope=manifest(self.root/'package.xml',[('ApexClass','Service')])
        with self.assertRaises(ValueError):self.bridge.capture('source',scope,self.root/'snapshots')
        self.assertEqual(list((self.root/'snapshots').glob('source-*')),[])

    def test_large_listing_does_not_prove_absence(self):
        self.connect();self.cli.limit=True
        scope=manifest(self.root/'package.xml',[('ApexClass','Missing')])
        with self.assertRaises(ValueError):self.bridge.capture('source',scope,self.root/'snapshots')

    def test_null_inventory_does_not_prove_absence(self):
        self.connect();original=self.cli.run
        def run(args,*a,**kw):return None if args[:3]==['org','list','metadata'] else original(args,*a,**kw)
        scope=manifest(self.root/'package.xml',[('ApexClass','Missing')])
        with patch.object(self.cli,'run',side_effect=run):
            with self.assertRaisesRegex(ValueError,'inventory was not confirmed'):self.bridge.capture('source',scope,self.root/'snapshots')

    def test_invalid_state_cannot_inject_target_arguments(self):
        self.connect();state=json.loads(self.bridge.path.read_text());state['source']['alias']='--target-org bad'
        self.bridge.path.write_text(json.dumps(state))
        with self.assertRaises(ValueError):self.bridge.status()

    def test_unexpected_registry_secret_field_is_not_echoed(self):
        self.connect();data=json.loads(self.bridge.path.read_text());data['source']['access_token']='secret-sentinel'
        self.bridge.path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'registry fields'):self.bridge.status()

    def test_cli_transport_rejects_write_operations(self):
        transport=CliTransport(['native-sf.exe'])
        for args in [['project','deploy','start'],['apex','run'],['data','delete','record']]:
            with self.assertRaises(ValueError):transport.run(args,self.root)

    def test_explicit_cli_wrapper_is_not_silently_replaced(self):
        wrapper=self.root/'sf.cmd';wrapper.write_text('echo not executed')
        with self.assertRaises(ValueError):cli_command(executable=str(wrapper))

    def test_raw_cli_failure_never_leaks_credentials(self):
        def execute(args,cwd,env,out,err,timeout):
            out.write(b'Bearer secret-sentinel');err.write(b'refresh_token secret-sentinel');return 1
        with patch('salesforce_guard.analyzer._execute',side_effect=execute):
            try:CliTransport(['native-sf.exe']).run(['data','query','--query',QUERY,'--target-org','sfg-source-000000000000','--json'],self.root)
            except ValueError as exc:self.assertNotIn('secret-sentinel',str(exc))
            else:self.fail('CLI failure was accepted')

    def test_environment_tokens_and_node_options_not_inherited(self):
        captured={}
        def execute(args,cwd,env,out,err,timeout):
            captured.update(env);out.write(b'{"status":0,"result":{}}');return 0
        with patch.dict('os.environ',{'SF_ACCESS_TOKEN':'secret','NODE_OPTIONS':'--require untrusted.js'}),patch('salesforce_guard.analyzer._execute',side_effect=execute):
            CliTransport(['native-sf.exe']).run(['data','query','--query',QUERY,'--target-org','sfg-source-000000000000','--json'],self.root)
        self.assertNotIn('SF_ACCESS_TOKEN',captured);self.assertNotIn('NODE_OPTIONS',captured)

    def test_cli_timeout_is_not_auth_success(self):
        with patch('salesforce_guard.analyzer._execute',side_effect=subprocess.TimeoutExpired('sf',1)):
            with self.assertRaisesRegex(ValueError,'timed out'):CliTransport(['native-sf.exe']).run(['org','login','web'],self.root,json_output=False)

    def test_business_record_query_is_rejected_before_execution(self):
        with patch('salesforce_guard.analyzer._execute') as execute:
            with self.assertRaisesRegex(ValueError,'fixed org-identity'):
                CliTransport(['native-sf.exe']).run(['data','query','--query','SELECT Id FROM Account','--target-org','sfg-source-000000000000','--json'],self.root)
            execute.assert_not_called()

    def test_identity_check_does_not_claim_effective_access(self):
        self.assertFalse(self.connect()['effective_user_access_assessed'])
        self.assertFalse(self.bridge.status(True)['source']['effective_user_access_assessed'])

    def test_option_like_public_client_id_rejected(self):
        with self.assertRaises(ValueError):
            self.bridge.login('source','https://source-example.my.salesforce.com',SOURCE,'--flags-dir')
        self.assertEqual(self.cli.calls,[])

    def test_deep_metadata_xml_rejected(self):
        from salesforce_guard.snapshot import canonical
        with self.assertRaisesRegex(ValueError,'nesting/element limit'):
            canonical('<a>'*1000+'</a>'*1000,True)

    def test_connection_mutations_hold_registry_lock_during_cli_calls(self):
        original=self.cli.run
        def checked(args,*a,**kw):
            self.assertTrue((self.bridge.root/'registry.lock').exists())
            return original(args,*a,**kw)
        with patch.object(self.cli,'run',side_effect=checked):
            self.connect()
            self.bridge.disconnect('source',True)
        self.assertFalse((self.bridge.root/'registry.lock').exists())


if __name__=='__main__':unittest.main()
