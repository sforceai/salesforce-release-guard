// Fictional release-review fixture. Not a deployable application.
public with sharing class ExpenseService { public static List<Expense__c> review() { ExpensePolicy.validate(); return [SELECT Id, Amount__c FROM Expense__c WITH SYSTEM_MODE]; } }
