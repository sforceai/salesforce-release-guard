// Fictional security-review fixture. Do not deploy.
public without sharing class LegacyExpenseController {
    @AuraEnabled
    public static List<Expense__c> findExpenses(String ownerName) {
        return Database.query('SELECT Id, Amount__c, BankAccount__c FROM Expense__c WHERE Owner.Name = \'' + ownerName + '\'');
    }
    @AuraEnabled
    public static void updateExpenses(List<Expense__c> expenses) {
        try {
            update expenses;
            System.debug(expenses);
        } catch (Exception failure) {
            // Intentionally swallowed to demonstrate an error-path finding.
        }
    }
}
