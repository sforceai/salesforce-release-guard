// Fictional impact-analysis fixture. Not a deployable application.
public with sharing class ExpenseController {
    @AuraEnabled
    public static void approve(List<Expense__c> expenses) {
        ExpenseService.approve(expenses);
    }
}
