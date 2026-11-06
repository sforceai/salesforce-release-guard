"""Fresh fictional evidence for local/native demonstrations; never live org details."""
from datetime import datetime,timezone
from .access import observation


def demo_evidence():
    return {'schema':'sfg.access.v1','role':'source','org_id':'00D000000000001','user_id':'005000000000001','user_active':True,
        'captured_at':datetime.now(timezone.utc).isoformat(),
        'scope':{'objects':['FictionalExpense__c'],'fields':['FictionalExpense__c.PublicNote__c','FictionalExpense__c.SecretNote__c'],'classes':['FictionalExpenseService']},
        'rows':[{'kind':'object','resource':'FictionalExpense__c','checks':{k:observation(k=='read','Fictional read-only object configuration') for k in ('read','create','update','delete')}},
            {'kind':'field','resource':'FictionalExpense__c.PublicNote__c','checks':{k:observation(k=='read','Fictional public field configuration') for k in ('read','create','update')}},
            {'kind':'field','resource':'FictionalExpense__c.SecretNote__c','checks':{k:observation(False,'Fictional withheld field configuration') for k in ('read','create','update')}},
            {'kind':'class','resource':'FictionalExpenseService','checks':{'configured_entry_grant':observation(True,'Fictional configured entry grant; no execution proof')}}]}
