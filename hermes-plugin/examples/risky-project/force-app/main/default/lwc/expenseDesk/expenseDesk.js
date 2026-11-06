// Fictional import-only fixture. This does not implement a complete LWC.
import approveExpenses from '@salesforce/apex/ExpenseController.approve';
export function approveExample(records) {
    return approveExpenses({ expenses: records });
}
