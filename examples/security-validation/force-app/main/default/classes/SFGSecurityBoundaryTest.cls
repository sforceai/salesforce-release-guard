// Original fictional security tests. All test-created users/records roll back.
@IsTest
private class SFGSecurityBoundaryTest {
    private static User restricted(String suffix) {
        Profile p = [SELECT Id FROM Profile WHERE Name = 'Minimum Access - Salesforce' WITH SYSTEM_MODE LIMIT 1];
        User u = new User(
            Username = 'sfg.boundary.' + suffix + '.' + String.valueOf(Crypto.getRandomLong()) + '@example.invalid',
            Email = 'sfg.boundary@example.invalid', LastName = 'FictionalBoundary', Alias = 'sfgbound',
            ProfileId = p.Id, TimeZoneSidKey = 'Australia/Sydney', LocaleSidKey = 'en_US',
            EmailEncodingKey = 'UTF-8', LanguageLocaleKey = 'en_US'
        );
        insert as system u;
        return u;
    }

    private static void grant(User u, String permissionName) {
        PermissionSet p = [SELECT Id FROM PermissionSet WHERE Name = :permissionName WITH SYSTEM_MODE LIMIT 1];
        insert as system new PermissionSetAssignment(AssigneeId = u.Id, PermissionSetId = p.Id);
    }

    @IsTest static void noGrantDeniesReadAndCreate() {
        User u = restricted('deny');
        System.runAs(u) {
            System.assertEquals(false, SFGAccessExample__c.SObjectType.getDescribe().isAccessible());
            Boolean readDenied = false;
            try { List<SFGAccessExample__c> rows = [SELECT Id FROM SFGAccessExample__c WITH USER_MODE]; }
            catch (QueryException expected) { readDenied = true; }
            System.assert(readDenied, 'User-mode read must be refused even for an empty table');
            SFGAccessExample__c row = new SFGAccessExample__c(Name = 'Fictional denied create');
            Boolean createDenied = false;
            try { insert as user row; }
            catch (Exception expected) {
                System.assert(new Set<String>{'System.DmlException','System.SecurityException','System.TypeException'}.contains(expected.getTypeName()));
                createDenied = true;
            }
            System.assert(createDenied, 'User-mode create must be refused');
            System.assertEquals(null, row.Id, 'Denied create must not assign an ID');
            System.assertEquals(0, [SELECT COUNT() FROM SFGAccessExample__c WITH SYSTEM_MODE]);
        }
    }

    @IsTest static void readerAllowsPublicFieldAndDeniesSecretAndWrite() {
        User u = restricted('reader'); grant(u, 'SFGAccessReader');
        System.runAs(u) {
            System.assertEquals(true, SFGAccessExample__c.SObjectType.getDescribe().isAccessible());
            List<SFGAccessExample__c> visible = [SELECT Id, PublicNote__c FROM SFGAccessExample__c WITH USER_MODE];
            System.assertEquals(0, visible.size());
            Boolean fieldDenied = false;
            try { List<SFGAccessExample__c> hidden = [SELECT SensitiveNote__c FROM SFGAccessExample__c WITH USER_MODE]; }
            catch (QueryException expected) { fieldDenied = true; }
            System.assert(fieldDenied, 'Withheld field must fail user-mode SELECT');
            SFGAccessExample__c seed = new SFGAccessExample__c(Name = 'Fictional owned record');
            insert as system seed;
            seed.PublicNote__c = 'Attempted denied write';
            Boolean updateDenied = false;
            try { update as user seed; }
            catch (Exception expected) {
                System.assert(new Set<String>{'System.DmlException','System.SecurityException','System.TypeException'}.contains(expected.getTypeName()));
                updateDenied = true;
            }
            System.assert(updateDenied, 'Read-only user must not update its own record');
            System.assertEquals(null, [SELECT PublicNote__c FROM SFGAccessExample__c WHERE Id = :seed.Id WITH SYSTEM_MODE].PublicNote__c);
        }
    }

    @IsTest static void explicitSystemModeDemonstratesBypassRisk() {
        User u = restricted('system');
        System.runAs(u) {
            System.assertEquals(false, SFGAccessExample__c.SObjectType.getDescribe().isCreateable());
            SFGAccessExample__c seed = new SFGAccessExample__c(Name = 'Fictional system-mode test');
            insert as system seed;
            System.assertNotEquals(null, seed.Id, 'Explicit system mode can bypass denied CRUD');
            System.assertEquals(1, [SELECT COUNT() FROM SFGAccessExample__c WITH SYSTEM_MODE]);
        }
    }

    @IsTest static void objectReadDoesNotGrantPrivateRecordVisibility() {
        User owner = restricted('owner'); User other = restricted('other');
        grant(owner, 'SFGAccessReader'); grant(other, 'SFGAccessReader');
        System.runAs(owner) {
            insert as system new SFGAccessExample__c(Name = 'Fictional private record');
            System.assertEquals(1, [SELECT COUNT() FROM SFGAccessExample__c WITH USER_MODE]);
        }
        System.runAs(other) {
            System.assertEquals(true, SFGAccessExample__c.SObjectType.getDescribe().isAccessible());
            System.assertEquals(0, [SELECT COUNT() FROM SFGAccessExample__c WITH USER_MODE]);
        }
    }

    @IsTest static void additiveReadGrantDoesNotGrantFieldWrites() {
        User u = restricted('additive'); grant(u, 'SFGAccessReader'); grant(u, 'SFGAccessSensitive');
        System.runAs(u) {
            List<SFGAccessExample__c> rows = [SELECT SensitiveNote__c FROM SFGAccessExample__c WITH USER_MODE];
            System.assertEquals(0, rows.size());
            System.assertEquals(true, SFGAccessExample__c.SensitiveNote__c.getDescribe().isAccessible());
            System.assertEquals(false, SFGAccessExample__c.SensitiveNote__c.getDescribe().isUpdateable());
        }
    }
}
