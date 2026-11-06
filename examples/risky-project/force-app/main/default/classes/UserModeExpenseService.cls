// Comparison fixture: fewer local signals is not a security certification.
public with sharing class UserModeExpenseService {
    @AuraEnabled
    public static List<Expense__c> myExpenses() {
        return [SELECT Id, Amount__c FROM Expense__c WITH USER_MODE];
    }
}
