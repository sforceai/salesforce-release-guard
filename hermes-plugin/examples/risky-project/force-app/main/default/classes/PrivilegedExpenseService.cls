// Fictional security-review fixture. System access can be intentional; review required.
public with sharing class PrivilegedExpenseService {
    @AuraEnabled
    public static List<Expense__c> allExpenses() {
        return [SELECT Id, Amount__c, BankAccount__c FROM Expense__c WITH SYSTEM_MODE];
    }
}
