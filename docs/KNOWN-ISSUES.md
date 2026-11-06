# Known issues and remaining work

These are tracked work items through v0.4.3, not confirmed exploitable vulnerabilities. Priorities indicate delivery order. No live Salesforce credentials or customer data belong in issue reports.

## P1: Validate browser authentication and metadata capture against two disposable orgs

The scoped live happy path passed in two authorized Developer Edition test orgs: browser authorization, expected org-ID checks, collision-free fictional Apex installation with tests, scoped capture and comparison. See [sanitized evidence](LIVE-VALIDATION.md). Broader metadata types and live denied/expired/disconnect/revoke paths remain unverified.

Acceptance criteria:
- Connect distinct source and destination test orgs using browser OAuth and expected org IDs.
- Capture an explicit supported manifest in both roles and verify retrieved identities and hashes.
- Exercise denied permissions, expired authorization, wrong-org aliases, incomplete retrieval and disconnect/revoke.
- Preserve sanitized evidence without tokens, private metadata or raw authentication output.

## P1: Implement scoped effective-user access assessment

The core v0.4.0 scoped configuration feature is implemented: explicit selected user per org, Salesforce-computed object/FLS observations, configured Apex entry grants, local reports and org/role-bound comparison attachments. See [ACCESS.md](ACCESS.md). Record-level and effective execution authorization remain unassessed. Broader group/session and live failure coverage remains open.

Acceptance criteria:
- Define the assessed user separately for each org and identify the relevant review components.
- Evaluate supported object CRUD, field access and Apex class access, accounting for profiles, permission sets, groups and muting where supported.
- Report unsupported, inaccessible or stale evidence as unknown; never infer access from successful login.
- Distinguish user-mode checks from system-mode execution and record-level sharing; explain coverage limits.
- Use fictional permission fixtures and least-privilege, explicitly bounded read operations.

## Resolved: Stalled Hermes verification and current catalog checks

The stall was narrowed to passing the full development workspace to Doctor. Bounded source-only verification and the native distribution now pass. The pinned official validator completed all 15 checks on the recorded installed bundle. Catalog maintainer review, fresh dependency-environment validation and anonymous public installation remain separate open gates. See INSTALLATION.md and V043-IMPROVEMENTS.md.

Acceptance criteria:
- Add bounded execution and stage-level diagnostics to the verification harness.
- Diagnose the stall and produce a fresh successful v0.3.1 receipt for all eight tools and the pre-tool hook.
- Confirm foreign tools are blocked before execution without running dangerous actions.
- Run the current catalog validator and record versions, results and remaining gaps.

## P2: Expand comparison and impact reliability coverage

The after graph is a static review projection. Unsupported references, runtime dispatch and Salesforce deployment merge semantics prevent complete impact claims.

Acceptance criteria:
- Add representative fictional multi-component changes and deletion conflicts with retained baseline callers.
- Verify unsupported metadata and uncertain relationships remain visibly unknown or unresolved.
- Document supported metadata boundaries, API-version behavior and report interpretation.
- Keep all deployments and business-record changes outside the review workflow.

## P2: Validate resource limits and filesystem behavior across platforms

The local synthetic benchmark covers 500 components per snapshot. It is not an enterprise load test. One real symlink test is skipped on this Windows account; filesystem race resistance is not proven.

Acceptance criteria:
- Run Windows and Linux CI with real link/reparse-point cases where supported.
- Exercise file, byte, directory-entry, XML depth, graph and output limits at boundaries.
- Add larger and adverse synthetic workloads, capturing elapsed time, memory and truncation/unknown behavior.
- Document measured environments and limitations without unsupported scalability claims.

## P1: Complete release and hackathon submission readiness

No catalog PR, public submission or demo post has been completed. A 70-second live demo with Indian English synthetic narration and fictional screenshots has been prepared at the user's request. An isolated authenticated native install passed; anonymous public installation still requires publication approval and final-pin verification.

Acceptance criteria:
- Publish the audited source and confirm remote CI results.
- Reconcile README and submission disclosures with current verified behavior.
- Generate the catalog entry using the real repository URL and exact reviewed commit SHA.
- Prepare the catalog PR and check the organizer's current requirements and deadline.
- Track demo and form submission as explicit remaining steps; do not claim acceptance or a prize.

## Resolved in v0.4.3: Custom-input approval and setup ambiguity

Native custom inputs now require an operator-approved project folder and explicit acknowledgement of model sharing. All supplied inputs are checked before source analysis; the agent has no approval tool. The full-source operator CLI is explicitly separate from the marketplace bundle. Report coverage, evidence timing and selected-user gaps are prominent. See [first review](FIRST-REVIEW.md).

Remaining limits: folder controls are not OS isolation, approvals are locally editable and filesystem race resistance is not established. Revocation cannot retract prior model data/reports. Two real-link tests are skipped on the current Windows account; Linux CI must cover supported links. The existing recorded Desktop/video workflow predates these UI additions and must not be presented as a new v0.4.3 recording.

## Diagnosed: Windows installation path limits; supported short-path route verified

While preparing the v0.4.3 film, an isolated install in a deeply nested review profile was found to lack two bundled permission-set fixtures, despite an installer success message. Its comparison correctly returned an unknown result. Root cause is not established; path-length behavior is a candidate. A fresh shorter-path installation of the same exact source pin contained all 64 recorded source files with matching hashes and produced the complete expected fixture result.

The verification harness now checks BUILD.json hashes before host execution and asserts the entire comparison summary, rather than only the deletion count. It rejects the observed incomplete install and passes the complete one. Earlier admission/handler checks did not establish full fixture completeness for the deep install; use the stronger receipt for the complete short-path installation. The official admission validator also passed all 15 checks on that complete installation. Broader long-path compatibility remains open; do not convert unknown results to successful review.

Follow-up on 7 November: normal deep-path checkout reproduced `Filename too long`. A diagnostic Git long-path override still exposed ordinary Windows read/cleanup limits. The normal short-home/short-profile route passed complete native checks. `scripts/check_install.py` is a separate read-only operator check that refuses incomplete or invalid inventories. See [Windows instructions and exact evidence limits](WINDOWS-INSTALLATION.md). The historical two-file omission is not fully reconstructed; arbitrary deep installations are not claimed supported.
