// Fictional release-review fixture. Not a deployable application.
public with sharing class ExpenseService { public static List<Expense__c> review() { OldExpenseUtility.label(); return [SELECT Id, Amount__c FROM Expense__c WITH USER_MODE]; } public static String legacyLabel() { return 'Example'; } }
