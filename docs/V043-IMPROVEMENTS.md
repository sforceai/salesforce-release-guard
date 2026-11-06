# v0.4.3 review improvements

Custom native inputs now require operator approval of a project folder. Approval acknowledges that requested evidence/excerpts reach the selected Hermes model. The native plugin cannot grant or revoke approval. The separate full-source operator CLI writes atomic, serialized profile-local policy changes. Missing or malformed policies, sibling-folder escapes and linked paths fail closed before analysis. Built-in fictional demos remain available without sign-in or folder approval.

Comparison, security and access reports now show **What was actually checked?** prominently: supplied coverage, evidence timing, selected user or absent access evidence, unassessed areas and a concrete next review step. Zero static references is explicitly scoped to supplied source. No report approves a deployment.

[Your first review](FIRST-REVIEW.md) explains obtaining the separate operator checkout, connecting both roles, choosing release/context/deletion manifests, capturing snapshots, choosing the assessed user, approving inputs and making a human decision. Examples are fictional.

## Validation

- Full local suite: 181 tests, 179 passed and two Windows real-symlink tests skipped because this account cannot create them.
- Actual Hermes registered-handler verification passed, including custom source denied before approval, allowed after explicit operator approval, then denied after revocation. Foreign shell dispatch was blocked before execution.
- Desktop and 390px mobile browser checks covered comparison, access and security reports. No page-width overflow was observed at that breakpoint; the dependency shortcut selected the destination-before deletion graph.
- Native distribution source parity passed. Exact commit `811323f502d1b4b3ee7a77d4120d30e062d87eb9` installed and enabled in a fresh isolated review profile using existing private GitHub authentication and the installed Hermes runtime. Scanning remained enabled.
- That installed bundle passed all 15 admission checks using official validator `65a0cb48510db539442dd56490babbe465acc096`: safe verdict, no admission warnings. Installed registered-handler checks passed, including approval/revocation and pre-dispatch shell blocking.
- Windows/Linux Python 3.11/3.12 CI passed for the exact source commit, including tests, bundle parity, fictional demo and packaging.

Anonymous public installation, fresh host/dependency-environment validation and catalog acceptance remain open. SAFE is not complete security assurance.

This is a scoped source/access review. Record sharing, effective execution, complete dependency discovery, live drift and enterprise-scale behavior are not established. Approval is a native tool boundary, not OS isolation or independently signed consent. A malicious local writer/race is outside the established protection. Existing Desktop model-driven and video receipts predate this version; no new v0.4.3 model-driven recording is claimed.

## Film capture follow-up

The new 82-second film uses genuine v0.4.3 reports plus explicitly labeled earlier Hermes footage and recorded host checks. See [film provenance](DEMO-FILM.md).

Capture also exposed an installation-verification gap: a deep Windows profile lacked two fictional permission files. The comparison returned unknown correctly, while the earlier harness asserted only the deletion count. The strengthened harness verifies every BUILD.json source hash before execution and the entire expected comparison summary. It rejected that incomplete installation. A fresh shorter-path install of the same pin passed all 64 source hashes, the complete expected counts, approval/revocation, foreign-dispatch blocking and all 15 official admission checks. This supersedes any implication that the earlier deep-install receipt proved complete fixture delivery. Long-path compatibility is still open.
