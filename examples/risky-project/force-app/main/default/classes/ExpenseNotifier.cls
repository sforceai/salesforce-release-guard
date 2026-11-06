// Fictional invocable-to-queueable dependency fixture. No real message is sent.
public with sharing class ExpenseNotifier {
    @InvocableMethod(label='Prepare example expense notice')
    public static void send(List<Id> expenseIds) {
        System.enqueueJob(new ExpenseNoticeJob());
    }
}
