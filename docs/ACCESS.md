# Scoped selected-user access

Version 0.4.0 adds selected-user configuration evidence. It does not claim that a signed-in user can execute every reviewed operation.

## Try without credentials

Double-click `Access-Demo.cmd`, run `python -m salesforce_guard access-demo --output output`, or ask Hermes to run `sfg_access` without an evidence path. The original fictional example shows a read-only object, a readable field, a withheld field and a configured Apex entry grant. No org calls are made.

## Collect live evidence as an operator

Connect and verify the source/destination roles as described in [CONNECTIONS.md](CONNECTIONS.md). Select the user to assess explicitly; this may be a different user from the account authorizing the CLI connection. The connected operator needs permission to inspect the relevant setup/access information.

Create an explicit scope file, for example:

```json
{
  "objects": ["FictionalExpense__c"],
  "fields": ["FictionalExpense__c.PublicNote__c", "FictionalExpense__c.SecretNote__c"],
  "classes": ["FictionalExpenseService"]
}
```

Then run, substituting the real selected user's ID locally:

```console
python -m salesforce_guard org access source --user-id SELECTED_USER_ID --scope scope.json --output output/access
```

This operator command uses only fixed-shape, parameter-validated SELECT queries. It verifies org identity around collection and saves private `access-evidence.json`, `access.json` and `access.html` files. The standard review bridge still refuses generic queries. No native/model-facing tool authenticates, queries an org, creates users, assigns permissions or deploys metadata.

The limit is 100 explicit scope entries, at most 50 per kind, with field parent objects included. Names must be simple explicit API names. Namespaced Apex selectors, arbitrary SOQL, wildcard scope and record-level checks are not supported. Individual query responses and timeouts are bounded; a scope containing many resources may take several minutes because the operator bridge starts CLI queries separately.

## Interpret the result

- Object Read/Create/Update/Delete observations come from Salesforce `UserEntityAccess` for the selected principal.
- Field Read/Create/Update observations come from `UserFieldAccess` and are gated by the corresponding object permission. A positive field flag cannot override denied object access.
- Apex rows are **configured entry grants**, using profile-owned and assigned permission sets. Expired/inactive assignments are excluded; unresolved group calculation, session activation, broad privileges or incomplete grants remain unknown where they affect the answer. This is not proof that an invocation route is usable or that internal calls enforce access.
- False computed responses are denied; missing, malformed, mismatched or inaccessible evidence is unknown. An inactive selected user is denied; unknown user activity remains unknown.
- Group muting for object/FLS is delegated to Salesforce's computed response rather than manually reimplemented. No claim is made that every permission-set-group/session configuration has been validated live.
- Record sharing, restriction rules, login/session policy, license restrictions and actual execution are not assessed. Explicit system-mode code can bypass user CRUD/FLS.

Collection is not transactional: permissions can change during or after it. Local import refuses evidence older than 24 hours or materially future-dated, but timestamps and files are not independently signed and can be edited. Treat imported evidence as user-supplied, point-in-time evidence, not a security enforcement boundary.

## Use in review reports

Run `sfg_access` with an absolute evidence path to render local evidence. It returns the first 30 resource rows and saves the full local report. It sends requested results through the active Hermes model like other tools; keep private schemas out of unapproved model environments.

`scan --access-evidence` and native `sfg_scan`'s `access_evidence_path` attach selected-user context to a local source report. Local source alone does not establish which org it came from.

`compare --before-access` / `--after-access`, or the native comparison tool's corresponding arguments, attach baseline/candidate context. Each attachment must match the snapshot's captured org ID and destination/source role. A mismatch or missing provenance is refused. Different selected users can be assessed on the two sides; no permission equivalence is inferred between them.

Reports label this `scoped_configuration_only`; effective execution access stays unassessed. Access results are context for human review and do not automatically approve deployments or alter finding severities.

## Privacy and fixture setup

Org/user IDs, schema names, assignments and captured provenance are private. Store live evidence under excluded `output` folders. Do not upload raw responses, reports, connection state or screenshots from live captures.

The original metadata in `examples/access-validation` is an operator fixture, not an automatically installed dependency. It adds one fictional private object, two text fields and two narrow read-only permission sets. Existing users and profiles must not be modified for setup. User creation and fixture deployment require separate operator authorization and are intentionally outside the review plugin.

Official references: [Tooling API reference](https://resources.docs.salesforce.com/latest/latest/en-us/sfdc/pdf/api_tooling.pdf), [Tooling objects in standard WSDLs](https://developer.salesforce.com/docs/platform/api/guide/api-tooling-objects.html), [profiles and permissions data model](https://developer.salesforce.com/docs/platform/data-models/guide/profiles-and-permissions-management.html), [session-based permission sets](https://developer.salesforce.com/docs/platform/api-action/guide/actions-obj-activate-session-permission-set.html).


## Executed live scope

Two new Minimum Access test users were assessed before and after a narrow read-only assignment in the two authorized test orgs. Both returned 0 allowed / 11 denied before assignment and 3 allowed / 8 denied afterward, with zero unknown observations. This verifies the scoped configuration path, not restricted-user login or business execution. See [sanitized live evidence](LIVE-VALIDATION.md).


Version 0.4.1 also correlates returned resource names, field parents, assignment principals, profile ownership and Apex identities. Unrelated returned rows are discarded. JSON evidence rejects duplicate keys, non-finite numbers and excessive depth/element count; the bytes parsed and hashed are identical. See [security testing](SECURITY-TESTING.md).

## Native input approval

Custom evidence and attached before/after evidence must be inside an operator-approved project folder. Approval is separate from Salesforce authentication and requires explicit model-sharing acknowledgement. The built-in fictional access demo needs no approval. Follow [the first-review recipe](FIRST-REVIEW.md); the assessed user remains separate from the authenticated operator.
