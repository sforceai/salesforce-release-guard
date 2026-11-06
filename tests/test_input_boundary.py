import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from salesforce_guard.input_boundary import authorize_inputs, approval_status, POLICY_NAME
from salesforce_guard.input_approvals import update_approval
from salesforce_guard.review_scope import review_scope

ROOT = Path(__file__).resolve().parents[1]


class InputBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve();self.data = self.root/'profile'
        self.project = self.root/'project';self.project.mkdir()
        self.sibling = self.root/'project-other';self.sibling.mkdir()
        self.policy = self.data/POLICY_NAME

    def approve(self):
        return update_approval(self.policy,self.project,approve=True,model_sharing=True)

    def test_explicit_consent_approval_and_revocation(self):
        with self.assertRaises(ValueError):authorize_inputs(self.data,[self.project])
        with self.assertRaisesRegex(ValueError,'model-sharing'):
            update_approval(self.policy,self.project,approve=True)
        self.assertFalse(self.policy.exists())
        self.approve()
        authorize_inputs(self.data,[self.project])
        with self.assertRaises(ValueError):authorize_inputs(self.data,[self.sibling])
        update_approval(self.policy,self.project,approve=False)
        with self.assertRaises(ValueError):authorize_inputs(self.data,[self.project])
        self.assertEqual(approval_status(self.data)['state'],'demo_only')

    def test_every_input_must_be_approved_and_traversal_does_not_expand_scope(self):
        self.approve()
        with self.assertRaises(ValueError):authorize_inputs(self.data,[self.project,self.sibling])
        with self.assertRaises(ValueError):authorize_inputs(self.data,[self.project/'..'/'project-other'])
        with self.assertRaises(ValueError):authorize_inputs(self.data,['relative'])
        with self.assertRaises(ValueError):update_approval(self.policy,Path(self.root.anchor),approve=True,model_sharing=True)

    def test_malformed_forged_and_oversized_policies_fail_closed(self):
        self.data.mkdir()
        for content in ('{','{}','{"schema":"sfg.input-approvals.v1","model_sharing_approved":"true","roots":[]}',
                        '{"schema":"sfg.input-approvals.v1","model_sharing_approved":true,"roots":[],"roots":[]}',
                        ' '*65537):
            self.policy.write_text(content)
            with self.assertRaises(ValueError):authorize_inputs(self.data,[self.project])
            self.assertEqual(approval_status(self.data)['state'],'invalid_policy')

    def test_link_escape_is_refused(self):
        self.approve();link=self.project/'escape'
        try:link.symlink_to(self.sibling,target_is_directory=True)
        except OSError:self.skipTest('Creating a real symlink is unavailable on this host')
        with self.assertRaisesRegex(ValueError,'links|reparse'):authorize_inputs(self.data,[link])

    def test_busy_update_cannot_overwrite_a_revocation(self):
        self.approve();before=self.policy.read_bytes()
        lock=self.data/'.input-approvals.lock';lock.write_text('busy')
        with self.assertRaisesRegex(ValueError,'busy'):update_approval(self.policy,self.project,approve=False)
        self.assertEqual(before,self.policy.read_bytes())
        lock.unlink();update_approval(self.policy,self.project,approve=False)
        self.assertEqual(approval_status(self.data)['approved_root_count'],0)

    def load_native(self):
        name='sfg_input_boundary_test'
        spec=importlib.util.spec_from_file_location(name,ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
        module=importlib.util.module_from_spec(spec);sys.modules[name]=module
        self.addCleanup(sys.modules.pop,name,None);spec.loader.exec_module(module)
        module._data=lambda:self.data
        return module

    def test_native_handlers_refuse_inputs_before_analysis_and_cannot_self_approve(self):
        native=self.load_native()
        with patch.object(native,'scan_project') as scan:
            result=json.loads(native._scan({'project_path':str(self.project),'approved_roots':[str(self.project)]}))
            self.assertIn('not approved',result['error']);scan.assert_not_called()
        self.approve()
        foreign=self.sibling/'scope.xml';foreign.write_text('<Package/>')
        with patch.object(native,'scan_project') as scan:
            self.assertIn('error',json.loads(native._scan({'project_path':str(self.project),'access_evidence_path':str(foreign)})))
            scan.assert_not_called()
        with patch.object(native,'compare_snapshots') as compare:
            for key in ('scope_path','delete_pre','delete_post','before_access','after_access'):
                result=json.loads(native._compare({'candidate_path':str(self.project),'destination_path':str(self.project),key:str(foreign)}))
                self.assertIn('error',result)
            compare.assert_not_called()
        self.assertIn('error',json.loads(native._access({'evidence_path':str(foreign)})))
        before=self.policy.read_bytes();native._policy({'roots':[str(self.sibling)]})
        self.assertEqual(before,self.policy.read_bytes())

    def test_builtin_demos_need_no_operator_approval(self):
        native=self.load_native()
        self.assertNotIn('error',json.loads(native._demo({})))
        self.assertEqual(json.loads(native._compare_demo({}))['summary']['destructive'],1)
        self.assertEqual(json.loads(native._access({}))['summary'],{'allowed':3,'denied':8,'unknown':0})
        self.assertFalse(self.policy.exists())

    def test_approved_custom_source_can_be_reviewed(self):
        native=self.load_native();self.approve()
        (self.project/'Example.cls').write_text('public with sharing class Example {}')
        self.assertNotIn('error',json.loads(native._scan({'project_path':str(self.project)})))

    def test_scope_summary_keeps_unknown_coverage_and_user_evidence_visible(self):
        report={'kind':'comparison','review_status':'incomplete','summary':{'unknown':1},
                'candidate_snapshot':{'components':1},'destination_snapshot':{'components':2},
                'rows':[{}],'user_access':{'before':{'user_id':'<img src=x>','role':'destination','captured_at':'yesterday','summary':{'unknown':2}}}}
        text=review_scope(report)
        self.assertIn('Zero references found does not prove',text)
        self.assertIn('2 unknown checks',text);self.assertIn('&lt;img src=x&gt;',text)
        self.assertNotIn('<img',text);self.assertIn('Resolve unknown/conflicting',text)
        self.assertIn('Not assessed',review_scope({'summary':{}}))


if __name__=='__main__':unittest.main()
