// Original fictional, pure-calculation fixture. No record operations or external calls.
public with sharing class SFGExamplePolicy { public static Integer score(Integer amount) { return amount > 100 ? 3 : 1; } }
