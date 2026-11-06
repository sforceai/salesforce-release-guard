# Scoped live validation — 5 November 2026

The operator authenticated two user-authorized Developer Edition test orgs through the installed Salesforce CLI. Each connection was checked against an independently supplied expected org ID, and the roles were confirmed to be different orgs. Org identifiers, domains, aliases, authorization material and raw receipts are deliberately omitted here.

## Executed

- A read-only probe capture correctly declared one explicitly named, absent fictional Apex class in each org.
- Before installation, Apex metadata inventories were checked for collisions with the exact proposed `SFGExample` class names. No collisions were found.
- The original fictional projects in `examples/live-validation` were validated using `project deploy start --dry-run`, `RunSpecifiedTests` and `SFGExampleFixtureTest`. Both validations completed successfully.
- The candidate project installed four Apex classes, including one test class. The baseline installed five, including one test class. Both deployments completed successfully and each ran one passing Apex test method with zero test errors. The same test method also passed during each pre-install validation.
- The read-only capture bridge retrieved the explicitly scoped fictional classes: four present and two absent in the source; five present and one absent in the destination. Snapshot hashes and org provenance were retained privately.
- The local comparison returned one new, two modified, one unchanged and one destructive-intent row, with zero unknown or conflict rows. The proposed deletion's baseline impact retained two upstream references, including a destination caller outside the release scope.

The destructive row is review intent only. No destructive manifest was deployed, and no component was deleted. The operator fixture setup used the CLI outside the review plugin; the native plugin and org bridge did not gain deployment capability. The fixtures perform pure calculations and label returns, with no business-record queries, DML, callouts, triggers, Flows, permission assignments or scheduled jobs.

## Limits and remaining work

This verifies the happy path for these fictional Apex fixtures in two specific test orgs. It does not verify all metadata types, least-privileged users, expired or denied live authorizations, custom client-app policies, disconnect/revoke behavior, concurrent changes, deployment merge semantics, sandbox behavior or AppExchange readiness. These cases remain open work.

Version 0.4.0 adds the scoped configuration validation below. Record access and effective execution remain **not assessed**. The after graph is a static projection. A successful sign-in, Apex test or retrieval is not proof of complete authorization enforcement or vulnerability absence.

Raw deployment responses, logs, connection state, snapshots and the generated comparison report stay in excluded local folders. They must not be uploaded to the repository or used in public screenshots without a separate privacy review. Only the original fictional fixture source and this sanitized summary are intended for the repository.

## v0.4.0 restricted-user access validation

- One new test user was created in each org on the existing Minimum Access - Salesforce profile after checking available licenses. Fictional undeliverable email addresses were used; no password was set and no existing user or profile was changed. The two test users remain available for the fictional demonstration.
- The original `examples/access-validation` fixture was checked for object/permission-set name collisions, validated and installed in both orgs. It contains one private fictional object, two text fields and two narrow permission sets. The existing fictional Apex fixture test passed during validation and installation with zero test errors.
- Before assigning permissions, each selected user's scoped report returned **0 allowed, 11 denied, 0 unknown** checks: object CRUD, field Read/Create/Update for two fields and a configured Apex entry grant.
- After assigning only the fictional read-only permission set, each report returned **3 allowed, 8 denied, 0 unknown**. Object Read, public-field Read and the configured Apex entry grant were allowed. Object writes, all field writes and withheld-field Read remained denied.
- The separate sensitive-field permission set was installed but not assigned. No business records, existing users, existing profiles or destructive changes were involved.
- Salesforce's returned composite DurableId normalized the selected-user suffix to 18 characters. The collector was corrected to verify both resource identity and normalized principal identity, with a regression test. The first unknown report and failed expectation were retained privately and are not counted as a passing test.
- The latest private source/destination reader evidence was attached to the earlier captured comparison. Org/role binding passed on both sides. The report labels it `scoped_configuration_only`, retaining `not_assessed` for effective execution.

These are happy-path and denial configuration tests, not actual login or business operations performed as the restricted users. Complex permission-set-group/muting, session activation, license effects, live expiration, record access and runtime bypass behavior still require separate validation. The native review plugin still performs no org calls or setup changes.


## v0.4.1 runtime security pass

Five validation-only Apex security methods passed in each org, covering denied CRUD/FLS, private-record sharing, additive read grants and explicit system-mode bypass. The class was not saved and all test-created users/records rolled back. The strengthened collector was rerun read-only and retained the expected 3 allowed / 8 denied result in each org. See [SECURITY-TESTING.md](SECURITY-TESTING.md) for evidence, corrections and limits.
