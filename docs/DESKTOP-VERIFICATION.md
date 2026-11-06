# Hermes Desktop verification

> Historical development evidence: old development commit IDs below are retained as receipt identifiers and are not install pins in the clean public history. Use [PUBLIC-VERIFICATION.md](PUBLIC-VERIFICATION.md) for current public installation.

Observed on 6 November 2026 using Hermes Desktop 0.22.7 and Salesforce Guard 0.4.2, pinned to `e77f30c162f07fc2f3d76257270f9f6522139523`, in a dedicated review profile. All inputs were fictional; no live Salesforce org was accessed.

## Result

The model-driven workflow completed with **five tool calls and no tool-call errors**: restricted schema discovery, native snapshot comparison, change inspection, before-change impact inspection, and scoped access reporting.

- Comparison: 1 new, 2 modified, 1 destructive, 1 unchanged; 0 unknown or conflicting changes.
- Explicit post-deletion: `OldExpenseUtility`.
- Two static upstream callers of its `label()` method: `ExistingExpenseCaller.run()` and `ExpenseService.review()`.
- Fictional access checks: 3 allowed, 8 denied, 0 unknown.
- Both local HTML reports were generated. Counts are test-fixture results, not a security assurance for arbitrary orgs.

The active `sfg_policy` response included `conditional_tools`, limiting `tool_describe` to the nine Guard tools. A separate check using the installed Hermes verification harness passed registration, catalog validation, native comparison/access/impact calls, mixed/foreign schema rejection, and pre-dispatch blocking of a shell request.

## Resolved test-environment issue

Earlier Desktop turns used an old in-memory plugin policy and rejected schema discovery. Closing and reopening the Desktop window did not stop the shared gateway: its process predated the window restart. Restarting the gateway loaded the installed policy; the subsequent workflow completed without the discovery failures. Installation metadata alone is insufficient evidence that a running gateway has reloaded a plugin.

On this Windows installation, the official `gateway restart` command unexpectedly entered startup-service setup and created a login shortcut. That shortcut was removed and its absence verified. Do not prescribe this command as an unattended restart without reviewing the host version's service behavior. No administrator approval was accepted.

## Scope

Static dependency references are not verified execution paths. Access evidence is scoped and does not prove all effective authorization or record sharing. The tool gate is a Hermes profile boundary, not an operating-system sandbox. Public catalog acceptance and hackathon submission are separate outstanding steps.
