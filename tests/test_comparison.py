import json
from pathlib import Path
import tempfile
import unittest

from salesforce_guard.snapshot import load_snapshot,parse_manifest
from salesforce_guard.compare import compare_snapshots
from salesforce_guard.comparison_view import render_comparison


def manifest(path,items):
    groups={}
    for kind,name in items: groups.setdefault(kind,[]).append(name)
    text='<Package xmlns="http://soap.sforce.com/2006/04/metadata">'+''.join('<types>'+''.join('<members>'+n+'</members>' for n in names)+'<name>'+kind+'</name></types>' for kind,names in groups.items())+'<version>67.0</version></Package>'
    path.write_text(text,encoding='utf-8'); return path


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'candidate';self.target=self.root/'destination'
        self.source.mkdir();self.target.mkdir()
        self.scope=self.root/'package.xml';self.delete=self.root/'delete.xml'

    def apex(self,root,name,body=None,api='67.0'):
        body=body or ('public class '+name+' {}')
        folder=root/'force-app/main/default/classes';folder.mkdir(parents=True,exist_ok=True)
        (folder/(name+'.cls')).write_text(body,encoding='utf-8')
        (folder/(name+'.cls-meta.xml')).write_text('<ApexClass><apiVersion>'+api+'</apiVersion><status>Active</status></ApexClass>')

    def coverage(self,root,types=None,absent=None,**extra):
        (root/'sfg-snapshot.json').write_text(json.dumps({'schema':'sfg.snapshot.v1','complete_types':types or [],'absent_components':absent or [],**extra}))

    def compare(self,items,pre=None,post=None):
        manifest(self.scope,items)
        return compare_snapshots(self.source,self.target,self.scope,pre,post)

    def test_new_requires_positive_absence_coverage(self):
        self.apex(self.source,'NewClass');self.coverage(self.target,['ApexClass'])
        result=self.compare([('ApexClass','NewClass')])
        self.assertEqual(result['summary']['new'],1)

    def test_missing_target_without_coverage_is_unknown(self):
        self.apex(self.source,'NewClass')
        result=self.compare([('ApexClass','NewClass')])
        self.assertEqual(result['summary']['unknown'],1);self.assertEqual(result['summary']['new'],0)

    def test_explicit_component_absence_can_establish_new(self):
        self.apex(self.source,'NewClass');self.coverage(self.target,absent=[{'type':'ApexClass','full_name':'NewClass'}])
        self.assertEqual(self.compare([('ApexClass','NewClass')])['summary']['new'],1)

    def test_same_identity_modified(self):
        self.apex(self.source,'Demo','public class Demo { void added() {} }');self.apex(self.target,'Demo')
        self.assertEqual(self.compare([('ApexClass','Demo')])['summary']['modified'],1)

    def test_same_content_unchanged_across_different_directories(self):
        self.apex(self.source,'Demo');self.apex(self.target,'Demo')
        self.assertEqual(self.compare([('ApexClass','Demo')])['summary']['unchanged'],1)

    def test_api_version_change_is_a_modification(self):
        self.apex(self.source,'Demo',api='67.0');self.apex(self.target,'Demo',api='66.0')
        self.assertEqual(self.compare([('ApexClass','Demo')])['summary']['modified'],1)

    def test_metadata_formatting_whitespace_ignored(self):
        for root,text in [(self.source,'<PermissionSet>\n <label>Example</label>\n</PermissionSet>'),(self.target,'<PermissionSet><label>Example</label></PermissionSet>')]:
            p=root/'permissionsets';p.mkdir();(p/'Example.permissionset-meta.xml').write_text(text)
        self.assertEqual(self.compare([('PermissionSet','Example')])['summary']['unchanged'],1)

    def test_missing_candidate_is_not_a_deletion(self):
        self.apex(self.target,'Demo')
        result=self.compare([('ApexClass','Demo')])
        self.assertEqual(result['summary']['unknown'],1);self.assertEqual(result['summary']['destructive'],0)

    def test_baseline_only_outside_scope_retained(self):
        self.apex(self.target,'Keep');self.apex(self.target,'Demo');self.apex(self.source,'Demo')
        result=self.compare([('ApexClass','Demo')])
        self.assertIn('Keep',[x['full_name'] for x in result['untouched_destination_components']])
        self.assertTrue(any(n['id']=='apex:keep' for n in result['after_impact']['nodes']))

    def test_explicit_post_deletion(self):
        self.apex(self.target,'Retire');manifest(self.delete,[('ApexClass','Retire')])
        result=compare_snapshots(self.source,self.target,None,delete_post=self.delete)
        self.assertEqual(result['summary']['destructive'],1);self.assertEqual(result['rows'][0]['deletion_phase'],'post')
        self.assertFalse(any(n['id']=='apex:retire' for n in result['after_impact']['nodes']))

    def test_pre_and_post_same_deletion_is_conflict(self):
        self.apex(self.target,'Retire');manifest(self.delete,[('ApexClass','Retire')])
        result=compare_snapshots(self.source,self.target,None,self.delete,self.delete)
        self.assertEqual(result['summary']['conflict'],1)
        self.assertTrue(any(n['id']=='apex:retire' for n in result['after_impact']['nodes']))

    def test_add_and_delete_same_identity_conflict(self):
        self.apex(self.source,'Demo');self.apex(self.target,'Demo');manifest(self.delete,[('ApexClass','Demo')])
        self.assertEqual(self.compare([('ApexClass','Demo')],post=self.delete)['summary']['conflict'],1)

    def test_unknown_deletion_target_not_approved(self):
        manifest(self.delete,[('ApexClass','Missing')])
        result=compare_snapshots(self.source,self.target,None,delete_post=self.delete)
        self.assertEqual(result['summary']['unknown'],1)

    def test_already_absent_deletion_is_noop(self):
        self.coverage(self.target,['ApexClass']);manifest(self.delete,[('ApexClass','Missing')])
        result=compare_snapshots(self.source,self.target,None,delete_post=self.delete)
        self.assertEqual(result['summary']['unchanged'],1)

    def test_deletion_preserves_upstream_before_evidence(self):
        self.apex(self.target,'Retire','public class Retire { public static void go() {} }')
        self.apex(self.target,'Caller','public class Caller { void go() { Retire.go(); } }')
        manifest(self.delete,[('ApexClass','Retire')])
        result=compare_snapshots(self.source,self.target,None,delete_post=self.delete)
        self.assertGreater(result['rows'][0]['upstream_reference_count'],0)
        self.assertTrue(any(e['confidence']=='unresolved' for e in result['after_impact']['edges']))

    def test_method_removal_is_modified_with_review_note(self):
        self.apex(self.target,'Demo','public class Demo { public static String oldMethod() { return \'x\'; } }');self.apex(self.source,'Demo')
        row=self.compare([('ApexClass','Demo')])['rows'][0]
        self.assertEqual(row['classification'],'modified');self.assertTrue(any('oldMethod' in n for n in row['review_notes']))

    def test_namespace_mismatch_not_guessed(self):
        self.apex(self.source,'Demo');self.apex(self.target,'Demo');self.coverage(self.source,namespace='Example')
        self.assertEqual(self.compare([('ApexClass','Demo')])['summary']['unknown'],1)

    def test_reversed_snapshot_roles_rejected(self):
        self.coverage(self.source,provenance={'role':'destination'})
        with self.assertRaisesRegex(ValueError,'role declarations'):self.compare([('ApexClass','Demo')])

    def test_wildcard_scope_rejected(self):
        manifest(self.scope,[('ApexClass','*')])
        with self.assertRaises(ValueError): parse_manifest(self.scope)

    def test_entity_manifest_rejected(self):
        self.scope.write_text('<!DOCTYPE x [<!ENTITY a SYSTEM "file:///secret">]><Package/>')
        with self.assertRaises(ValueError): parse_manifest(self.scope)

    def test_empty_intent_rejected(self):
        with self.assertRaises(ValueError): compare_snapshots(self.source,self.target,None)

    def test_missing_companion_makes_component_unknown(self):
        p=self.source/'classes';p.mkdir();(p/'Demo.cls').write_text('public class Demo {}')
        self.coverage(self.target,['ApexClass'])
        self.assertEqual(self.compare([('ApexClass','Demo')])['summary']['unknown'],1)

    def test_capture_hash_mismatch_invalidates_snapshot(self):
        self.apex(self.target,'Demo');snap=load_snapshot(self.target)
        hashes={p:h for p,(t,h) in snap.files.items()};self.coverage(self.target,['ApexClass'],files_sha256=hashes)
        self.apex(self.target,'Demo','public class Demo { void changed() {} }')
        self.assertEqual(load_snapshot(self.target).state('|ApexClass|Demo'),'unknown')

    def test_contradictory_absence_invalidates_snapshot(self):
        self.apex(self.target,'Demo');self.coverage(self.target,absent=[{'type':'ApexClass','full_name':'Demo'}])
        self.assertEqual(load_snapshot(self.target).state('|ApexClass|Demo'),'unknown')

    def test_malformed_coverage_declaration_is_rejected(self):
        self.coverage(self.target,absent={'not':'a list'})
        with self.assertRaises(ValueError):load_snapshot(self.target)

    def test_field_identity_uses_object_name(self):
        folder=self.source/'objects'/'Expense__c'/'fields';folder.mkdir(parents=True)
        (folder/'Note__c.field-meta.xml').write_text('<CustomField><fullName>Note__c</fullName></CustomField>')
        self.assertIn('|CustomField|Expense__c.Note__c',load_snapshot(self.source).components)

    def test_field_deletion_keeps_before_field_callers(self):
        folder=self.target/'objects'/'Expense__c'/'fields';folder.mkdir(parents=True)
        (folder/'Note__c.field-meta.xml').write_text('<CustomField><fullName>Note__c</fullName></CustomField>')
        self.apex(self.target,'Caller','public class Caller { void go() { List<Expense__c> x=[SELECT Note__c FROM Expense__c WITH USER_MODE]; } }')
        manifest(self.delete,[('CustomField','Expense__c.Note__c')])
        result=compare_snapshots(self.source,self.target,None,delete_post=self.delete)
        self.assertGreater(result['rows'][0]['upstream_reference_count'],0)
        self.assertTrue(any(e['target']=='field:expense__c.note__c' and e['confidence']=='unresolved' for e in result['after_impact']['edges']))

    def test_parent_delete_child_update_conflict(self):
        manifest(self.delete,[('CustomObject','Expense__c')])
        result=self.compare([('CustomField','Expense__c.Note__c')],post=self.delete)
        self.assertEqual(result['summary']['conflict'],2)

    def test_field_filename_fullname_conflict_is_unknown(self):
        folder=self.source/'objects'/'Expense__c'/'fields';folder.mkdir(parents=True)
        (folder/'Note__c.field-meta.xml').write_text('<CustomField><fullName>Different__c</fullName></CustomField>')
        self.coverage(self.target,['CustomField'])
        self.assertEqual(self.compare([('CustomField','Expense__c.Note__c')])['summary']['unknown'],1)

    def test_bundle_nested_file_path_change_is_not_ignored(self):
        for root,sub in [(self.source,'a'),(self.target,'b')]:
            folder=root/'lwc'/'example'/sub;folder.mkdir(parents=True);(folder/'same.js').write_text('export const value=1;')
        self.assertNotEqual(load_snapshot(self.source).components['|LightningComponentBundle|example']['hash'],load_snapshot(self.target).components['|LightningComponentBundle|example']['hash'])

    def test_report_payload_is_escaped(self):
        self.apex(self.source,'Demo');self.apex(self.target,'Demo')
        report=self.compare([('ApexClass','Demo')]);report['rows'][0]['reason']='</script><script>alert(9)</script>'
        self.assertNotIn('</script><script>alert(9)</script>',render_comparison(report))

    def test_fictional_release_counts(self):
        base=Path(__file__).resolve().parents[1]/'examples/release-demo'
        result=compare_snapshots(base/'candidate',base/'destination',base/'package.xml',delete_post=base/'destructiveChangesPost.xml')
        self.assertEqual(result['summary'],{'new':1,'modified':2,'destructive':1,'unchanged':1,'unknown':0,'conflict':0})

    def test_optional_unknown_coverage_example(self):
        base=Path(__file__).resolve().parents[1]/'examples/release-demo'
        result=compare_snapshots(base/'candidate',base/'destination',base/'scope-with-unknown.xml',delete_post=base/'destructiveChangesPost.xml')
        self.assertEqual(result['summary']['unknown'],1);self.assertEqual(result['review_status'],'incomplete')


if __name__=='__main__': unittest.main()
