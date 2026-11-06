# Original fictional access fixture

For operator-authorized disposable test orgs only. This fixture adds:

- One private custom object, `SFGAccessExample__c`, with two optional text fields.
- `SFGAccessReader`, granting object Read, public-field Read and the existing fictional `SFGExampleReviewService` entry grant.
- `SFGAccessSensitive`, a separate read-only sensitive-field grant used for optional additional tests.

The live baseline/candidate fixture in `examples/live-validation` supplies the Apex class and test dependency. This project does not create users or assign permission sets automatically. It creates no business records and supplies no org IDs, addresses or credentials. Check for naming collisions before any installation.

The tested restricted users were newly created on the existing Minimum Access profile. Existing users and profiles were not modified. Raw setup and capture evidence stays outside source control. See [access workflow](../../docs/ACCESS.md) and [sanitized live validation](../../docs/LIVE-VALIDATION.md).
