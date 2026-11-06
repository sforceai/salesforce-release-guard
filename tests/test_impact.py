import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from salesforce_guard.impact import build_graph, query_graph
from salesforce_guard.scan import scan_project
from salesforce_guard.report import render_html


def source(classes=None,flows=None,extra=None):
    files={}
    for name,code in (classes or {}).items():
        files[name+'.cls']=(code,'hash-'+name)
        files[name+'.cls-meta.xml']=('<ApexClass><apiVersion>67.0</apiVersion></ApexClass>','metadata-'+name)
    for name,xml in (flows or {}).items(): files[name+'.flow-meta.xml']=(xml,'flow-'+name)
    files.update(extra or {})
    return files


class ImpactTests(unittest.TestCase):
    def graph(self,**kw): return build_graph(source(**kw),[])
    def edges(self,g,kind): return [e for e in g['edges'] if e['kind']==kind]

    def test_resolved_static_call_has_evidence(self):
        g=self.graph(classes={'Entry':'public class Entry { public void go() { Service.run(); } }','Service':'public class Service { public static void run() {} }'})
        e=self.edges(g,'calls')[0]
        self.assertEqual(e['confidence'],'explicit_reference')
        self.assertTrue(e['target'].startswith('method:service.run/0'))
        self.assertEqual(e['evidence']['path'],'Entry.cls')

    def test_comments_and_string_literals_do_not_create_calls(self):
        g=self.graph(classes={'Entry':"public class Entry { public void go() { /* Ghost.run(); */ String s='Ghost.run()'; } }"})
        self.assertFalse(self.edges(g,'calls'))

    def test_local_and_typed_variable_calls(self):
        g=self.graph(classes={'Entry':'public class Entry { public void go() { Worker w = new Worker(); w.run(); helper(); } private void helper() {} }','Worker':'public class Worker { public void run() {} }'})
        targets={e['target'].split('@')[0] for e in self.edges(g,'calls')}
        self.assertIn('method:worker.run/0',targets)
        self.assertIn('method:entry.helper/0',targets)

    def test_overloaded_same_arity_stays_unresolved(self):
        g=self.graph(classes={'Entry':'public class Entry { void go() { Worker.run(value); } }','Worker':'public class Worker { void run(String value) {} void run(Integer value) {} }'})
        self.assertEqual(self.edges(g,'calls')[0]['confidence'],'unresolved')

    def test_missing_external_class_not_invented(self):
        g=self.graph(classes={'Entry':'public class Entry { void go() { Missing.run(); } }'})
        e=self.edges(g,'calls')[0]
        self.assertEqual(e['confidence'],'unresolved')
        self.assertTrue(e['target'].startswith('unresolved:'))

    def test_dynamic_dispatch_has_explicit_gap(self):
        g=self.graph(classes={'Entry':"public class Entry { void go() { Type.forName('NotEmbedded'); } }"})
        self.assertTrue(self.edges(g,'dynamic_call'))
        self.assertNotIn('NotEmbedded',json.dumps(g))

    def test_async_new_target(self):
        g=self.graph(classes={'Entry':'public class Entry { void go() { System.enqueueJob(new Worker()); } }','Worker':'public class Worker implements Queueable { public void execute(QueueableContext c) {} }'})
        e=self.edges(g,'enqueues')[0]
        self.assertEqual(e['boundary'],'asynchronous')
        self.assertTrue(e['target'].startswith('method:worker.execute/1'))

    def test_async_variable_target(self):
        g=self.graph(classes={'Entry':'public class Entry { void go() { Worker job = new Worker(); System.enqueueJob(job); } }','Worker':'public class Worker { public void execute(QueueableContext c) {} }'})
        self.assertEqual(self.edges(g,'enqueues')[0]['confidence'],'explicit_reference')

    def test_unknown_async_variable_is_unresolved(self):
        g=self.graph(classes={'Entry':'public class Entry { void go() { System.enqueueJob(job); } }'})
        self.assertEqual(self.edges(g,'enqueues')[0]['confidence'],'unresolved')

    def test_dml_preserves_parameter_type_and_user_mode(self):
        g=self.graph(classes={'Entry':'public class Entry { void go(List<Expense__c> records) { update as user records; } }'})
        e=self.edges(g,'writes')[0]
        self.assertEqual(e['target'],'object:expense__c')
        self.assertEqual(e['mode'],'explicit_user')

    def test_standard_user_type_not_confused_with_mode_keyword(self):
        g=self.graph(classes={'Entry':'public class Entry { void go(User account) { update as system account; } }'})
        e=self.edges(g,'writes')[0]
        self.assertEqual(e['target'],'object:user')
        self.assertEqual(e['mode'],'explicit_system')

    def test_database_dml_and_legacy_context(self):
        files=source(classes={'Entry':'public class Entry { void go(List<Expense__c> records) { Database.update(records, false, AccessLevel.SYSTEM_MODE); } }'})
        g=build_graph(files,[])
        e=self.edges(g,'writes')[0]
        self.assertEqual(e['target'],'object:expense__c')
        self.assertEqual(e['mode'],'explicit_system')

    def test_query_field_dependencies_are_separate_from_record_access(self):
        g=self.graph(classes={'Entry':'public without sharing class Entry { void go() { List<Account> a=[SELECT Id, Name FROM Account WITH USER_MODE]; } }'})
        self.assertEqual(self.edges(g,'reads')[0]['mode'],'explicit_user')
        self.assertEqual(len(self.edges(g,'reads_field')),2)
        self.assertEqual(next(n for n in g['nodes'] if n['id']=='apex:entry')['sharing'],'without sharing')

    def test_flow_scheduled_invocable_and_fault_routes(self):
        xml='<Flow><status>Active</status><start><object>Expense__c</object><recordTriggerType>Update</recordTriggerType><scheduledPaths><name>Later</name><connector><targetReference>Call</targetReference></connector></scheduledPaths></start><actionCalls><name>Call</name><actionType>apex</actionType><actionName>Worker</actionName><flowTransactionModel>CurrentTransaction</flowTransactionModel><faultConnector><targetReference>Audit</targetReference></faultConnector></actionCalls><recordCreates><name>Audit</name><object>Audit__c</object></recordCreates></Flow>'
        g=self.graph(classes={'Worker':'public class Worker { @InvocableMethod public static void run(List<Id> ids) {} }'},flows={'Review':xml})
        self.assertEqual(self.edges(g,'schedules')[0]['boundary'],'scheduled_transaction')
        self.assertEqual(self.edges(g,'invokes_apex')[0]['transaction_model'],'CurrentTransaction')
        self.assertEqual(len(self.edges(g,'fault')),1)

    def test_record_activation_is_conditional_not_direct_call(self):
        g=self.graph(classes={'Entry':'public class Entry { void go(List<Expense__c> items) { update items; } }'},flows={'Review':'<Flow><status>Active</status><start><object>Expense__c</object><recordTriggerType>Update</recordTriggerType></start></Flow>'})
        e=self.edges(g,'may_activate')[0]
        self.assertEqual(e['confidence'],'conditional')
        self.assertIn('not evaluated',e['note'])

    def test_draft_flow_not_assumed_active(self):
        g=self.graph(classes={'Entry':'public class Entry { void go(List<Expense__c> items) { update items; } }'},flows={'Review':'<Flow><status>Draft</status><start><object>Expense__c</object><recordTriggerType>Update</recordTriggerType></start></Flow>'})
        self.assertEqual(self.edges(g,'may_activate'),[])

    def test_subflow_forward_reference_resolves(self):
        g=self.graph(flows={'First':'<Flow><subflows><name>RunSecond</name><flowName>Second</flowName></subflows></Flow>','Second':'<Flow><start/></Flow>'})
        self.assertEqual(next(n for n in g['nodes'] if n['id']=='flow:second')['kind'],'flow')
        self.assertEqual(self.edges(g,'calls_subflow')[0]['confidence'],'explicit_reference')

    def test_whole_flow_mode_finding_not_assigned_to_each_element(self):
        files=source(flows={'Review':'<Flow><start/><runInMode>SystemMode</runInMode></Flow>'})
        finding={'id':'mode-finding','path':'Review.flow-meta.xml','line':1}
        g=build_graph(files,[finding])
        self.assertEqual(next(n for n in g['nodes'] if n['kind']=='flow')['finding_ids'],['mode-finding'])
        self.assertTrue(all(not n['finding_ids'] for n in g['nodes'] if n['kind']=='flow_element'))

    def test_invalid_api_does_not_invent_database_default(self):
        files=source(classes={'Entry':'public class Entry { void go(List<Account> records) { update records; } }'})
        files['Entry.cls-meta.xml']=('<ApexClass><apiVersion>NaN</apiVersion></ApexClass>','hash')
        self.assertEqual(self.edges(build_graph(files,[]),'writes')[0]['mode'],'unknown')

    def test_permission_grant_does_not_become_call(self):
        g=self.graph(classes={'Entry':'public class Entry {}'},extra={'Access.permissionset-meta.xml':('<PermissionSet><classAccesses><apexClass>Entry</apexClass><enabled>true</enabled></classAccesses></PermissionSet>','hash')})
        e=self.edges(g,'grants_class_access')[0]
        self.assertIn('effective user access are unknown',e['note'])
        self.assertEqual(self.edges(g,'calls'),[])

    def test_method_query_includes_declared_access_context_separately(self):
        g=self.graph(classes={'Entry':'public class Entry { void go() {} }'},extra={'Access.permissionset-meta.xml':('<PermissionSet><classAccesses><apexClass>Entry</apexClass><enabled>true</enabled></classAccesses></PermissionSet>','hash')})
        focus=next(n['id'] for n in g['nodes'] if n['kind']=='apex_method')
        result=query_graph(g,focus)
        self.assertEqual(len(result['declared_access_context']),1)
        self.assertEqual(result['edges'],[])

    def test_lwc_import_is_reference_not_proven_invocation(self):
        g=self.graph(classes={'Entry':'public class Entry { public void go() {} }'},extra={'force-app/main/default/lwc/demo/demo.js':("import action from '@salesforce/apex/Entry.go';",'hash')})
        self.assertEqual(len(self.edges(g,'imports_apex')),1)
        self.assertIn('not proven',self.edges(g,'imports_apex')[0]['note'])

    def test_cycle_query_terminates_and_upstream_differs(self):
        g=self.graph(classes={'A':'public class A { void go() { B.go(); } }','B':'public class B { void go() { A.go(); } }'})
        focus=next(n['id'] for n in g['nodes'] if n['kind']=='apex_method')
        result=query_graph(g,focus,'both',4)
        self.assertEqual(len(result['nodes']),2)
        self.assertFalse(result['truncated'])

    def test_method_focus_does_not_pull_unrelated_sibling_calls(self):
        g=self.graph(classes={'A':'public class A { void one() { B.go(); } void two() { C.go(); } }','B':'public class B { void go() {} }','C':'public class C { void go() {} }'})
        focus=next(n['id'] for n in g['nodes'] if n['id'].startswith('method:a.one/'))
        result=query_graph(g,focus,'downstream',2)
        self.assertFalse(any(n['id'].startswith('method:c.') for n in result['nodes']))

    def test_class_focus_includes_members(self):
        g=self.graph(classes={'A':'public class A { void one() {} void two() {} }'})
        self.assertEqual(len(query_graph(g,'apex:a')['nodes']),3)

    def test_missing_node_and_bad_depth_rejected(self):
        g=self.graph(classes={'A':'public class A {}'})
        for focus,direction,depth in [('missing','both',2),('apex:a','sideways',2),('apex:a','both',99)]:
            with self.assertRaises(ValueError): query_graph(g,focus,direction,depth)

    def test_oversized_graph_has_visible_gap(self):
        with patch('salesforce_guard.impact.MAX_NODES',2):
            g=self.graph(classes={'A':'public class A { void one() {} void two() {} }'})
        self.assertLessEqual(len(g['nodes']),2)
        self.assertTrue(any('limit' in gap['reason'] for gap in g['gaps']))

    def test_full_node_budget_does_not_crash_on_flow(self):
        with patch('salesforce_guard.impact.MAX_NODES',2):
            g=self.graph(classes={'A':'public class A { void go() {} }'},flows={'Review':'<Flow><start/></Flow>'})
        self.assertEqual(len(g['nodes']),2)
        self.assertTrue(any('Flow dependencies omitted' in gap['reason'] for gap in g['gaps']))

    def test_script_payload_escaped(self):
        report=scan_project(Path(__file__).resolve().parents[1]/'examples/risky-project')
        report['impact']['nodes'][0]['label']='</script><script>alert(42)</script>'
        rendered=render_html(report)
        self.assertNotIn('</script><script>alert(42)</script>',rendered)
        self.assertIn('\\u003c/script',rendered)

    def test_fictional_demo_has_full_reference_chain(self):
        report=scan_project(Path(__file__).resolve().parents[1]/'examples/risky-project')
        g=report['impact']
        kinds={e['kind'] for e in g['edges']}
        self.assertTrue({'imports_apex','calls','writes','may_activate','schedules','invokes_apex','enqueues','fault'}<=kinds)
        self.assertFalse(any(n['id']=='object:update' for n in g['nodes']))
        self.assertFalse(any(e['kind']=='writes' and e['target']=='object:user' for e in g['edges']))


if __name__=='__main__': unittest.main()
