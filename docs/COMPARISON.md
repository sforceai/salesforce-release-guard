# Two-snapshot release review — 0.3.0

Run `Compare-Demo.cmd` or `python -m salesforce_guard compare-demo --output output` to open the original fictional example. It contains one new component, two modifications, one explicit post-deletion and one unchanged component. Destination-only callers/helpers remain in context. A separate `scope-with-unknown.xml` intentionally adds a field without destination absence coverage, demonstrating an unknown result.

## Review real exports

```console
python -m salesforce_guard compare /path/to/candidate /path/to/destination --scope /path/to/package.xml --delete-post /path/to/destructiveChangesPost.xml --output output
```

Omit `--delete-post` and `--delete-pre` when there is no deletion intent. Delete-only reviews can omit `--scope`. Both deletion phases are supported explicitly. No command deploys, deletes, compiles, runs tests in an org or executes anonymous Apex.

Native Hermes tools: `sfg_compare`, `sfg_compare_demo` and `sfg_changes`. The `sfg_impact` tool accepts a comparison report ID plus `comparison_side: before|after` (default before). Org sign-in/capture remain operator-only and are not available to the reviewing agent.

## Classification

Identity is `(declared namespace, metadata type, full name)`. Supported types are ApexClass, ApexTrigger, Flow, PermissionSet, Profile, ApexPage, ApexComponent, LightningComponentBundle, CustomObject and decomposed CustomField.

- New: candidate is present and destination coverage explicitly declares the identity absent.
- Modified: the same identity exists on both sides with a different supported canonical fingerprint.
- Unchanged: canonical content matches, or an explicitly deleted identity is already absent under declared coverage.
- Destructive: a supplied pre/post deletion manifest explicitly names a component present in the destination snapshot.
- Unknown: source is missing/incomplete, destination absence is not established, snapshot hashes no longer match capture, or namespace matching would require an assumption.
- Conflict: the same component is updated and deleted, a deletion is declared twice/across both phases, or parent-object deletion overlaps child-field intent.

XML formatting-only whitespace and attribute order are ignored; meaningful text and element order are retained. Apex content normalises line endings only. Component bundles include relative file identities. Companion metadata participates in Apex/page/component hashes. Duplicate definitions, missing companions and malformed XML prevent an ordinary classification.

Renames are not guessed. Public/global method-name removal stays a class modification with a caller-review note. Permission entries changed/omitted stay modifications; no assumption is made that omission revokes a deployed grant. Data loss, effective permissions, package upgrade compatibility and Salesforce deployment merge semantics require separate validation.

## Coverage declaration

Offline exports without a declaration can still establish presence, modification and equality, but missing components are unknown. To declare known completeness/absence, supply `sfg-snapshot.json` at the snapshot root:

```json
{
  "schema": "sfg.snapshot.v1",
  "namespace": "",
  "complete_types": ["ApexClass"],
  "absent_components": [{"type": "PermissionSet", "full_name": "ExampleReviewer"}],
  "provenance": {"kind": "operator_export", "role": "destination"}
}
```

This is an input assertion, not a signed attestation or proof of current live-org state. Declare only coverage actually established by the export. The operator capture bridge writes scoped, named absence declarations and file hashes automatically. Editing captured files invalidates its inventory until a fresh snapshot is taken. Do not turn a partial export into `complete_types` just to obtain a green comparison.

## Impact

The before graph uses the destination snapshot. The proposed-after graph retains destination context, replaces only classified new/modified components and removes explicit deletion targets. Unknown/conflicting changes are not applied. It is a source review projection, not a deployment simulation. Review deletions against incoming before-graph references; do not lose callers just because the target disappears from the after view.

The tool does not lock the destination or detect changes made after capture. Recapture and recompare before a later deployment. Manifests must contain explicit supported members; wildcards are rejected. Review scope must include necessary destination context to discover more than the supplied references. Standard/managed/protected metadata and unsupported child forms can remain incomplete.
