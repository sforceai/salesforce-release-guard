from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,Mock

from salesforce_guard.access import scope_from_dict,load_evidence,observation,render_access
from salesforce_guard.access_capture import query_plan,AccessQueryTransport,collect_access,access_identity_matches

USER='005000000000001';ORG='00D000000000001';PS='0PS000000000001';PROFILE='00e000000000001';CLASS='01p000000000001'


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def evidence(self):
        return {'schema':'sfg.access.v1','role':'source','org_id':ORG,'user_id':USER,'user_active':True,
            'captured_at':datetime.now(timezone.utc).isoformat(),
            'scope':{'objects':['Example__c'],'fields':['Example__c.Note__c'],'classes':['ExampleService']},
            'rows':[{'kind':'object','resource':'Example__c','checks':{k:observation(False,'computed denied') for k in ('read','create','update','delete')}},
                {'kind':'field','resource':'Example__c.Note__c','checks':{k:observation(True,'computed allowed') for k in ('read','create','update')}},
                {'kind':'class','resource':'ExampleService','checks':{'configured_entry_grant':observation(None,'not established')}}]}

    def load(self,data):
        p=self.root/'evidence.json';p.write_text(json.dumps(data));return load_evidence(p)

    def test_object_denial_gates_positive_field_flags(self):
        report=self.load(self.evidence())
        self.assertEqual(report['summary'],{'allowed':0,'denied':7,'unknown':1})
        self.assertEqual(report['record_access'],'not_assessed')

    def test_unknown_object_does_not_allow_field(self):
        d=self.evidence();d['rows'][0]['checks']['read']=observation(None,'missing')
        self.assertEqual(self.load(d)['rows'][1]['checks']['read']['status'],'unknown')

    def test_inactive_user_is_not_allowed(self):
        d=self.evidence();d['user_active']=False
        self.assertEqual(self.load(d)['summary']['denied'],8)

    def test_unknown_user_activity_is_unknown(self):
        d=self.evidence();d['user_active']=None
        self.assertEqual(self.load(d)['summary']['unknown'],8)

    def test_stale_future_and_naive_timestamps_refused(self):
        for stamp in [(datetime.now(timezone.utc)-timedelta(days=2)).isoformat(),(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),'2026-11-05T00:00:00']:
            d=self.evidence();d['captured_at']=stamp
            with self.assertRaises(ValueError):self.load(d)

    def test_missing_duplicate_and_out_of_scope_rows_refused(self):
        for kind in ('missing','duplicate','extra'):
            d=self.evidence()
            if kind=='missing':d['rows'].pop()
            elif kind=='duplicate':d['rows'][1]=d['rows'][0]
            else:d['rows'][0]['resource']='Other__c'
            with self.assertRaises(ValueError):self.load(d)

    def test_string_boolean_is_not_an_observation(self):
        d=self.evidence();d['rows'][0]['checks']['read']['status']='true'
        with self.assertRaises(ValueError):self.load(d)

    def test_unknown_checks_refused(self):
        d=self.evidence();d['rows'][0]['checks']['execute']=observation(True,'bad')
        with self.assertRaises(ValueError):self.load(d)

    def test_html_escapes_evidence_text(self):
        d=self.evidence();d['rows'][0]['checks']['read']['reason']='<img src=x onerror=alert(1)>'
        text=render_access(self.load(d));self.assertNotIn('<img',text);self.assertIn('&lt;img',text)

    def test_scope_is_explicit_and_bounded(self):
        self.assertEqual(scope_from_dict({'fields':['Example__c.Note__c']})['objects'],['Example__c'])
        for d in [{'objects':['Account\' OR Id != null']},{'classes':['*']},{'objects':['Account']*2},{'fields':['Name']},{'other':[]},{'objects':[]}]:
            with self.assertRaises(ValueError):scope_from_dict(d)

    def test_queries_reject_injected_ids_and_unknown_shapes(self):
        for kind,params in [('user',{'user':"005000000000001' OR Id != null"}),('entity',{'name':'Account; delete'}),('grants',{'class_id':CLASS,'ids':["0PS000000000001' OR Id != null"]}),('delete',{}),('user',{'user':USER,'extra':True})]:
            with self.assertRaises(ValueError):query_plan(kind,**params)

    def test_transport_rejects_truncation_and_missing_completion(self):
        t=Mock();q=AccessQueryTransport(t,'sfg-source-000000000000',self.root)
        for result in [{'records':[],'totalSize':0},{'done':True,'records':[],'totalSize':1},{'done':False,'records':[],'totalSize':0}]:
            t._invoke.return_value=result
            with self.assertRaises(ValueError):q.query('user',user=USER)

    def bridge(self):
        b=Mock();b.root=self.root;b.transport=Mock();b._load.return_value={'source':{'alias':'sfg-source-000000000000','org_id':ORG}}
        return b

    def query(self,kind,**params):
        return {'user':[{'Id':USER,'IsActive':True,'ProfileId':PROFILE}],
            'entity':[{'DurableId':'Example__c','QualifiedApiName':'Example__c'}],'field':[{'DurableId':'Example__c.Note__c','QualifiedApiName':'Note__c','EntityDefinition':{'QualifiedApiName':'Example__c'}}],
            'entity_access':[{'DurableId':'Example__c.'+USER,'UserId':USER,'IsReadable':False,'IsCreatable':False,'IsUpdatable':False,'IsDeletable':False}],
            'field_access':[{'DurableId':'Example__c.Note__c.'+USER,'UserId':USER,'IsAccessible':True,'IsCreatable':True,'IsUpdatable':True}],
            'profile':[{'Id':PS,'ProfileId':PROFILE,'IsOwnedByProfile':True,'HasActivationRequired':False,'Type':'Profile','PermissionsAuthorApex':False,'PermissionsModifyAllData':False}],
            'assignments':[],'class':[{'Id':CLASS,'Name':'ExampleService','NamespacePrefix':None}],'grants':[]}[kind]

    def test_collection_preserves_denied_and_no_grant(self):
        with patch.object(AccessQueryTransport,'query',side_effect=self.query):
            r=collect_access(self.bridge(),'source',USER,self.evidence()['scope'],self.root/'reports')
        self.assertEqual(r['summary']['denied'],8)

    def test_unreadable_computed_access_is_unknown(self):
        def query(kind,**params):
            if kind=='entity_access':raise ValueError('private detail must not leak')
            return self.query(kind,**params)
        with patch.object(AccessQueryTransport,'query',side_effect=query):
            r=collect_access(self.bridge(),'source',USER,{'objects':['Example__c']},self.root/'reports')
        self.assertEqual(r['summary']['unknown'],4);self.assertNotIn('private detail',str(r))

    def test_wrong_computed_principal_is_unknown(self):
        def query(kind,**params):
            rows=self.query(kind,**params)
            if kind=='entity_access':rows[0]['UserId']='005000000000002'
            return rows
        with patch.object(AccessQueryTransport,'query',side_effect=query):
            r=collect_access(self.bridge(),'source',USER,{'objects':['Example__c']},self.root/'reports')
        self.assertEqual(r['summary']['unknown'],4)

    def test_changing_org_binding_refused(self):
        b=self.bridge();b._load.side_effect=[{'source':{'alias':'sfg-source-000000000000','org_id':ORG}},{}]
        with patch.object(AccessQueryTransport,'query',side_effect=self.query):
            with self.assertRaisesRegex(ValueError,'role changed'):collect_access(b,'source',USER,{'objects':['Example__c']},self.root/'reports')

    def test_session_permission_never_treated_as_unconditional_grant(self):
        def query(kind,**params):
            rows=self.query(kind,**params)
            if kind=='profile':rows[0]['HasActivationRequired']=True
            return rows
        with patch.object(AccessQueryTransport,'query',side_effect=query):
            r=collect_access(self.bridge(),'source',USER,{'classes':['ExampleService']},self.root/'reports')
        self.assertEqual(r['summary']['unknown'],1)

    def test_invalid_user_refused_before_org_access(self):
        b=self.bridge()
        with self.assertRaises(ValueError):collect_access(b,'source','admin',{'objects':['Account']},self.root/'reports')
        b._verify_alias.assert_not_called()

    def test_18_character_computed_durable_user_suffix(self):
        self.assertTrue(access_identity_matches({'DurableId':'Example__c.'+USER+'ABC','UserId':USER+'ABC'},'Example__c',USER))
        self.assertFalse(access_identity_matches({'DurableId':'Other__c.'+USER+'ABC','UserId':USER+'ABC'},'Example__c',USER))
        self.assertFalse(access_identity_matches({'DurableId':'Example__c.'+USER+'ABC','UserId':'005000000000002'},'Example__c',USER))

    def test_attached_comparison_evidence_is_org_and_role_bound(self):
        from salesforce_guard.access import attach_access
        d=self.evidence();p=self.root/'evidence.json';p.write_text(json.dumps(d))
        report={'candidate_snapshot':{'provenance':{'role':'source','org_id':ORG}},'destination_snapshot':{'provenance':{'role':'destination','org_id':'00D000000000002'}}}
        attach_access(report,p,'after');self.assertIn('after',report['user_access'])
        with self.assertRaises(ValueError):attach_access(report,p,'before')

    def test_malformed_resource_types_are_clean_errors(self):
        for key in ('kind','resource'):
            d=self.evidence();d['rows'][0][key]=[]
            with self.assertRaises(ValueError):self.load(d)

    def test_recalculating_group_does_not_create_unconditional_apex_grant(self):
        def query(kind,**params):
            if kind=='assignments':return [{'AssigneeId':USER,'PermissionSetId':PS,'PermissionSetGroupId':'0PG000000000001','PermissionSetGroup':{'Status':'Updating'},'IsActive':True,'ExpirationDate':None}]
            if kind=='profile':return []
            return self.query(kind,**params)
        with patch.object(AccessQueryTransport,'query',side_effect=query):
            r=collect_access(self.bridge(),'source',USER,{'classes':['ExampleService']},self.root/'reports')
        self.assertEqual(r['summary']['unknown'],1)

    def test_expired_assignment_cannot_grant_apex_access(self):
        def query(kind,**params):
            if kind=='assignments':return [{'AssigneeId':USER,'PermissionSetId':PS,'PermissionSetGroupId':None,'IsActive':True,'ExpirationDate':'2000-01-01T00:00:00Z'}]
            return self.query(kind,**params)
        with patch.object(AccessQueryTransport,'query',side_effect=query):
            r=collect_access(self.bridge(),'source',USER,{'classes':['ExampleService']},self.root/'reports')
        self.assertEqual(r['summary']['denied'],1)

    def test_positive_direct_grant_survives_other_unknown_session_grants(self):
        def query(kind,**params):
            if kind=='grants':return [{'ParentId':PS,'SetupEntityId':CLASS}]
            if kind=='assignments':return [{'AssigneeId':USER,'PermissionSetId':'0PS000000000002','PermissionSetGroupId':None,'IsActive':True,'ExpirationDate':None}]
            if kind=='sets':return [{'Id':'0PS000000000002','HasActivationRequired':True,'Type':'Regular','PermissionsAuthorApex':False,'PermissionsModifyAllData':False}]
            return self.query(kind,**params)
        with patch.object(AccessQueryTransport,'query',side_effect=query):
            r=collect_access(self.bridge(),'source',USER,{'classes':['ExampleService']},self.root/'reports')
        self.assertEqual(r['summary']['allowed'],1)

    def test_computed_boolean_string_stays_unknown(self):
        def query(kind,**params):
            rows=self.query(kind,**params)
            if kind=='entity_access':rows[0]['IsReadable']='false'
            return rows
        with patch.object(AccessQueryTransport,'query',side_effect=query):
            r=collect_access(self.bridge(),'source',USER,{'objects':['Example__c']},self.root/'reports')
        self.assertEqual(r['summary']['unknown'],1)

    def test_unassigned_permission_set_response_cannot_supply_grant(self):
        rogue='0PS000000000003'
        def query(kind,**params):
            if kind=='assignments':return [{'AssigneeId':USER,'PermissionSetId':'0PS000000000002','PermissionSetGroupId':None,'IsActive':True,'ExpirationDate':None}]
            if kind=='sets':return [{'Id':rogue,'HasActivationRequired':False,'Type':'Regular','PermissionsAuthorApex':False,'PermissionsModifyAllData':False}]
            if kind=='grants':return [{'ParentId':rogue}] if rogue in params['ids'] else []
            return self.query(kind,**params)
        with patch.object(AccessQueryTransport,'query',side_effect=query):
            r=collect_access(self.bridge(),'source',USER,{'classes':['ExampleService']},self.root/'reports')
        self.assertEqual(r['summary']['allowed'],0)

    def test_wrong_resource_definition_is_not_access_evidence(self):
        def query(kind,**params):
            if kind=='entity':return [{'DurableId':'Other__c','QualifiedApiName':'Other__c'}]
            if kind=='entity_access':return [{'DurableId':'Other__c.'+USER,'UserId':USER,'IsReadable':True,'IsCreatable':True,'IsUpdatable':True,'IsDeletable':True}]
            return self.query(kind,**params)
        with patch.object(AccessQueryTransport,'query',side_effect=query):
            r=collect_access(self.bridge(),'source',USER,{'objects':['Example__c']},self.root/'reports')
        self.assertEqual(r['summary']['unknown'],4)

    def test_duplicate_json_keys_refused(self):
        from salesforce_guard.access import load_json
        p=self.root/'duplicate.json';p.write_text('{"user_active":false,"user_active":true}')
        with self.assertRaises(ValueError):load_json(p)

    def test_deep_json_is_cleanly_refused(self):
        from salesforce_guard.access import load_json
        p=self.root/'deep.json';p.write_text('['*2000+'0'+']'*2000)
        with self.assertRaises(ValueError):load_json(p)

    def test_digest_uses_the_bytes_that_were_parsed(self):
        import hashlib
        d=self.evidence();raw=json.dumps(d).encode('utf-8');p=self.root/'same-read.json';p.write_bytes(raw)
        with patch.object(Path,'read_bytes',side_effect=AssertionError('Unexpected second file read')):
            report=load_evidence(p)
        self.assertEqual(report['evidence_sha256'],hashlib.sha256(raw).hexdigest())

    def test_wrong_assignment_principal_cannot_supply_grant(self):
        def query(kind,**params):
            if kind=='assignments':return [{'AssigneeId':'005000000000002','PermissionSetId':'0PS000000000002','PermissionSetGroupId':None,'IsActive':True,'ExpirationDate':None}]
            if kind=='grants':return []
            return self.query(kind,**params)
        with patch.object(AccessQueryTransport,'query',side_effect=query):
            r=collect_access(self.bridge(),'source',USER,{'classes':['ExampleService']},self.root/'reports')
        self.assertEqual(r['summary']['allowed'],0);self.assertEqual(r['summary']['unknown'],1)

    def test_wrong_class_identity_does_not_grant_requested_class(self):
        def query(kind,**params):
            if kind=='class':return [{'Id':CLASS,'Name':'OtherService','NamespacePrefix':None}]
            if kind=='grants':return [{'ParentId':PS,'SetupEntityId':CLASS}]
            return self.query(kind,**params)
        with patch.object(AccessQueryTransport,'query',side_effect=query):
            r=collect_access(self.bridge(),'source',USER,{'classes':['ExampleService']},self.root/'reports')
        self.assertEqual(r['summary']['unknown'],1)

    def test_wrong_profile_owner_is_not_used_for_grants(self):
        def query(kind,**params):
            rows=self.query(kind,**params)
            if kind=='profile':rows[0]['ProfileId']='00e000000000002'
            return rows
        with patch.object(AccessQueryTransport,'query',side_effect=query):
            r=collect_access(self.bridge(),'source',USER,{'classes':['ExampleService']},self.root/'reports')
        self.assertEqual(r['summary']['unknown'],1)

    def test_wrong_field_parent_is_not_used(self):
        def query(kind,**params):
            rows=self.query(kind,**params)
            if kind=='field':rows[0]['EntityDefinition']['QualifiedApiName']='Other__c'
            if kind=='entity_access':
                for key in ('IsReadable','IsCreatable','IsUpdatable','IsDeletable'):rows[0][key]=True
            return rows
        with patch.object(AccessQueryTransport,'query',side_effect=query):
            r=collect_access(self.bridge(),'source',USER,{'fields':['Example__c.Note__c']},self.root/'reports')
        self.assertEqual(r['summary']['unknown'],3)

    def test_nonfinite_numbers_rejected(self):
        from salesforce_guard.access import load_json
        for value in ('NaN','Infinity','-Infinity','1e999','-1e999'):
            p=self.root/'nonfinite.json';p.write_text('{"untrusted":'+value+'}')
            with self.assertRaises(ValueError):load_json(p)

    def test_oversized_and_invalid_utf8_evidence_refused(self):
        from salesforce_guard.access import load_json
        p=self.root/'bytes.json'
        for raw in (b' '*(2*1024*1024+1),b'\xff\xfeinvalid'):
            p.write_bytes(raw)
            with self.assertRaises(ValueError):load_json(p)

    def test_json_element_budget_refused(self):
        from salesforce_guard.access import load_json
        p=self.root/'many.json';p.write_text(json.dumps([0]*50001))
        with self.assertRaises(ValueError):load_json(p)


if __name__=='__main__':unittest.main()
