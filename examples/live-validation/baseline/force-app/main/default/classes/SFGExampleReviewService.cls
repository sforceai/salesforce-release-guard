// Original fictional, pure-calculation fixture. No record operations or external calls.
public with sharing class SFGExampleReviewService { public static Integer evaluate(Integer amount) { return SFGExampleLegacyRules.score(amount); } }
