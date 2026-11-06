"""Generate original fictional fixtures only. Never connects to an org."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'examples'/'release-demo'
HEADER='// Fictional release-review fixture. Not a deployable application.\n'
META='<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata"><apiVersion>67.0</apiVersion><status>Active</status></ApexClass>\n'


def write(side,relative,text):
    path=ROOT/side/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')


def apex(side,name,text):
    write(side,'force-app/main/default/classes/'+name+'.cls',HEADER+text+'\n')
    write(side,'force-app/main/default/classes/'+name+'.cls-meta.xml',META)


def main():
    apex('destination','ExpenseService',"public with sharing class ExpenseService { public static List<Expense__c> review() { OldExpenseUtility.label(); return [SELECT Id, Amount__c FROM Expense__c WITH USER_MODE]; } public static String legacyLabel() { return 'Example'; } }")
    apex('candidate','ExpenseService',"public with sharing class ExpenseService { public static List<Expense__c> review() { ExpensePolicy.validate(); return [SELECT Id, Amount__c FROM Expense__c WITH SYSTEM_MODE]; } }")
    apex('candidate','ExpensePolicy',"public with sharing class ExpensePolicy { public static void validate() { if (!FeatureManagement.checkPermission('Example_Expense_Review')) { throw new SecurityException('Example permission required'); } } }")
    apex('destination','OldExpenseUtility',"public with sharing class OldExpenseUtility { public static String label() { return 'Legacy example'; } }")
    apex('destination','ExistingExpenseCaller',"public with sharing class ExistingExpenseCaller { public static void run() { OldExpenseUtility.label(); ExpenseService.legacyLabel(); } }")
    apex('destination','KeepExpenseHelper',"public with sharing class KeepExpenseHelper { public static void keep() {} }")
    for side in ('candidate','destination'):
        apex(side,'UnchangedExpenseHelper',"public with sharing class UnchangedExpenseHelper { public static void run() {} }")
        editable='true' if side=='candidate' else 'false'
        write(side,'force-app/main/default/permissionsets/ExampleExpenseReviewer.permissionset-meta.xml',f'<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata"><label>Fictional reviewer</label><fieldPermissions><editable>{editable}</editable><field>Expense__c.Amount__c</field><readable>true</readable></fieldPermissions></PermissionSet>\n')
        write(side,'sfg-snapshot.json',json.dumps({'schema':'sfg.snapshot.v1','namespace':'','complete_types':['ApexClass','PermissionSet'],
            'provenance':{'kind':'fictional_fixture','role':'source' if side=='candidate' else 'destination'}},indent=2))
    write('candidate','force-app/main/default/objects/Expense__c/fields/ReviewNote__c.field-meta.xml','<CustomField xmlns="http://soap.sforce.com/2006/04/metadata"><fullName>ReviewNote__c</fullName><label>Fictional review note</label><type>Text</type><length>80</length></CustomField>\n')
    package='''<Package xmlns="http://soap.sforce.com/2006/04/metadata"><types><members>ExpenseService</members><members>ExpensePolicy</members><members>UnchangedExpenseHelper</members><name>ApexClass</name></types><types><members>ExampleExpenseReviewer</members><name>PermissionSet</name></types><version>67.0</version></Package>'''
    (ROOT/'package.xml').write_text(package,encoding='utf-8')
    (ROOT/'scope-with-unknown.xml').write_text(package.replace('<version>','<types><members>Expense__c.ReviewNote__c</members><name>CustomField</name></types><version>'),encoding='utf-8')
    (ROOT/'destructiveChangesPost.xml').write_text('<Package xmlns="http://soap.sforce.com/2006/04/metadata"><types><members>OldExpenseUtility</members><name>ApexClass</name></types><version>67.0</version></Package>',encoding='utf-8')
    print(ROOT)


if __name__=='__main__': main()
