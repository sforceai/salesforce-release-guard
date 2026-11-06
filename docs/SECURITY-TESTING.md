# Broader security testing — v0.4.1

Executed on 5 November 2026 against local code and two user-authorized test orgs. All examples are original fictional fixtures. Raw org responses, logs and identities remain private locally.

## Executed runtime tests

The five methods in `examples/security-validation/SFGSecurityBoundaryTest` were executed through Salesforce validation-only deployments in both orgs. Each org reported five completed tests and zero test errors. The class was not installed. Test-created users and records rolled back.

| Case | Verified behavior |
| --- | --- |
| Minimum-access user, no grants | User-mode query and create denied; denied create left no record ID or record |
| Read-only user | Public field query allowed; withheld-field query denied; update of an owned record denied without changing the field |
| Explicit system-mode operation | A test-only system-mode insert succeeded despite denied user Create permission, demonstrating why CRUD/FLS observations alone cannot prove runtime enforcement |
| Private record sharing | Object Read allowed, but another equally restricted user could not see the owner's private fictional record in user mode |
| Additive read grant | Additional sensitive-field Read allowed without granting field Update |

Persistent test-class installation was rejected by automatic approval review because it would add metadata beyond the testing request. The safer validation-only path completed the requested runtime checks without saving the class. No approval to install it is needed for these results.

The initial validation run identified two incorrect test expectations: denied DML surfaced as SecurityException/TypeException, rather than only DmlException. The test now accepts only the explicit denial exception variants and asserts the denied side effects. The corrected suite passed in both orgs; the earlier run is not counted as a pass.

## Defensive defects reproduced and fixed

| Area | Reproduced issue | Correction |
| --- | --- | --- |
| Access-response correlation | A mocked response for the wrong object, or an unassigned permission set, could be shown as an allowed observation | Check resource API name/parent, selected principal, profile ownership, requested permission-set IDs and requested Apex identity; discard unrelated rows and retain unknown where evidence is incomplete |
| Ambiguous/unbounded JSON structure | Duplicate keys and excessive nesting were accepted | Reject duplicate keys, non-finite numbers, depth over 64 and more than 50,000 elements; bound the actual read to 2 MiB |
| Evidence digest | Parsing and hashing used separate file reads | Parse and hash the same bounded byte sequence, so a later reread cannot misattribute the parsed evidence |
| Verification timeout | A future host stall could outlive stage diagnostics or leave an old passing receipt | Add a bounded outer process timeout using owned-process-tree cleanup; a failed/timed-out check overwrites stale success with `not_established` |

The correlation cases were malformed-response simulations, not observed Salesforce server faults or confirmed remote exploits. These fixes improve review reliability; the plugin still grants no org execution capability to a model.

## Local and host checks

- Local suite: 171 tests, 170 passed and one actual Windows symlink test skipped.
- Adversarial tool identities, Unicode lookalikes, control characters and common query-injection payloads refused. No foreign executable tool was run.
- Mismatched user, resource, field parent, profile owner, class, permission-set assignment and grant evidence tested. Incomplete/uncertain evidence must not produce a positive observation.
- Duplicate/stale/future/oversized/deep JSON evidence, object gating, inactive users, expired/session/recalculating-group cases and local HTML escaping covered by targeted tests.
- Native Hermes 0.21.2 against the packaged v0.4.1 source: nine tools and one hook, no Doctor findings, installed validator checks pass, real registered access/comparison/scan handlers exercised and the terminal probe blocked before execution. The new outer timeout was enabled.

The strengthened collector was also rerun read-only against the two existing restricted users. Each still returned three allowed, eight denied and zero unknown observations, with no correlation gaps and no changes to their assignments.

## Limits

This is a bounded security test pass, not a penetration-test certification, full OWASP assessment or AppExchange acceptance. Runtime results cover the supplied fixtures only. They do not prove arbitrary customer code enforces authorization.

Live permission-set-group muting/session activation, expired authorizations, collector access denied under a separate authenticated restricted account, revocation, filesystem races, complete runtime/data-flow coverage and current catalog admission checks remain open. Arbitrary record-access assessment is not a feature; private-record behavior was tested only in the isolated Apex fixture.

Edited evidence can still lie: files are not independently signed, and org permissions can change during or after collection. Hashing identifies the captured bytes; it does not authenticate the author. The tool gate is not an operating-system boundary.

Official references used for test design: [runAs](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-testing-tools-runas.html), [mixed DML in tests](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-dml-non-mix-sobjects-test-methods.html), [explicit user/system modes](https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-classes-enforce-usermode.html).
