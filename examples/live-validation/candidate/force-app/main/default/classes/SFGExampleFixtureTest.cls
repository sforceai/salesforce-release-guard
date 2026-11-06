// Original fictional, pure-calculation fixture. No record operations or external calls.
@IsTest private class SFGExampleFixtureTest { @IsTest static void verify() { System.assertEquals(1,SFGExampleReviewService.evaluate(50)); System.assertEquals(3,SFGExampleReviewService.evaluate(150)); System.assertEquals('Fictional review',SFGExampleStableHelper.label()); } }
