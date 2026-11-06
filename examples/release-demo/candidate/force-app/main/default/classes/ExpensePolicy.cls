// Fictional release-review fixture. Not a deployable application.
public with sharing class ExpensePolicy { public static void validate() { if (!FeatureManagement.checkPermission('Example_Expense_Review')) { throw new SecurityException('Example permission required'); } } }
