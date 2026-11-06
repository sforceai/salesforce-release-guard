// Fictional worker. External delivery is deliberately not implemented.
public with sharing class ExpenseNoticeJob implements Queueable {
    public void execute(QueueableContext context) {
        List<Expense__c> items = [SELECT Id, Amount__c FROM Expense__c WITH USER_MODE];
        System.debug('Example notice prepared');
    }
}
