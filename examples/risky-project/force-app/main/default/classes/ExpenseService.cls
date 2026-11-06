// Fictional fixture: the permission check's presence is not proof of safe input scope.
public with sharing class ExpenseService {
    public static void approve(List<Expense__c> expenses) {
        if (!FeatureManagement.checkPermission('Approve_Example_Expenses')) {
            throw new SecurityException('Approval permission required');
        }
        update as user expenses;
    }
}
