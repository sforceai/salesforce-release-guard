# Your first Salesforce release review

There are two starting points. The fictional demo needs only the Hermes plugin and a working model connection. Reviewing your own orgs also needs the separate operator utilities below. The marketplace bundle intentionally does not contain Salesforce sign-in or command-execution tools.

**Data choice first:** local processing does not mean the AI provider sees nothing. Source excerpts, schema names and access evidence returned through Hermes go to your selected model. Use an environment approved for that data. Never paste Salesforce credentials into chat.

## 1. Try the fictional demo

Follow [installation](INSTALLATION.md), select the dedicated review profile, and ask:

> Review the fictional Salesforce Guard release demo. Show what's new, modified and explicitly deleted, trace the deletion's before-change callers, and run the separate fictional user-access demo. No live org access or deployments.

Expect 1 new, 2 modified, 1 destructive and 1 unchanged component, two source callers of the removed utility, and 3 allowed / 8 denied scoped access checks. No folder approval or org sign-in is needed for these bundled fixtures.

## 2. Obtain the separate operator utilities

On the computer holding your local captures, install Python 3.10+ and Salesforce CLI from their official sources. Obtain the full Salesforce Guard source at the same reviewed commit as the native plugin. For a Git checkout:

```console
git clone https://github.com/sforceai/salesforce-release-guard.git
cd salesforce-release-guard
git checkout bb14a41aa90f68b2a9a45c5ee61cfe8a41773ece
python -m salesforce_guard --help
```

The checkout pin must match the native installation pin in the installation guide. Run the following operator commands from this checkout. The project needs no third-party Python runtime packages. Installing only `hermes-plugin/` does not install these utilities or `Connect-Orgs.cmd`.

## 3. Prepare the review inputs

Keep a private project folder, for example `C:/ReviewData/release-1`. Put the release manifest, context manifest, optional pre/post destructive manifests and captured output inside it. The supplied `examples/review-setup/` files are fictional templates: replace their API names with your own scope. Do not deploy those templates as an application.

- **Release manifest:** components you intend to deliver.
- **Context manifest:** release components, deletion targets and known existing callers/dependencies you want to inspect. It is broader than the release manifest and does not itself authorize a change.
- **Deletion manifest:** only deliberate removals. Missing candidate files never authorize deletion.

The tool does not automatically discover every caller in an org. A narrow capture produces a narrow dependency map. Zero references means none found in the supplied source, not that the whole org is clear.

## 4. Connect source and destination separately

Use [the connection guide](CONNECTIONS.md). Authenticate each role in Salesforce's browser flow, bind its expected org ID and run `org status --verify`. Salesforce CLI owns the tokens. Signing in proves the connected identity, not what another user can read or execute.

Do not grant extra permissions just to make a review pass. Metadata capture and inspecting another user's setup access may need an authorized operator. Missing access must remain a gap, not become an empty successful scan.

## 5. Capture both sides

Use your private context manifest in both roles:

```console
python -m salesforce_guard org capture source --manifest C:/ReviewData/release-1/context.xml --output C:/ReviewData/release-1/snapshots
python -m salesforce_guard org capture destination --manifest C:/ReviewData/release-1/context.xml --output C:/ReviewData/release-1/snapshots
```

Copy each returned `snapshot_path` locally and label its role. Do not guess the generated directory name or treat an incomplete retrieval as absence. These are scoped point-in-time snapshots, not a complete org export or a deployment simulation.

## 6. Choose the user whose access matters

The assessed user can differ from the connected operator. Use [ACCESS.md](ACCESS.md) to capture a named user's scoped object/field observations and configured Apex entry grants in each relevant role. Keep the evidence inside the private review folder. Evidence older than 24 hours is refused on import; missing or inaccessible results are unknown.

Record sharing and effective execution authorization are not assessed. Explicit system-mode code can behave differently from a user's CRUD/FLS permissions. Do not infer deployment-user authority or runtime safety from a successful login or an allowed row.

## 7. Approve the folder for the native review tools

Ask Hermes to run `sfg_policy`. It returns `input_boundary.policy_file`, the profile-specific location of `input-approvals.json`. Copy that location locally. Then, in the full source checkout, run:

```console
python -m salesforce_guard inputs approve --policy-file ABSOLUTE_POLICY_FILE --root C:/ReviewData/release-1 --allow-model-sharing
```

Replace `ABSOLUTE_POLICY_FILE` with the path just returned. Choose only the project folder needed for this review. The flag explicitly acknowledges model sharing. The agent has no approval, revocation or generic command tool. A missing, malformed or nonmatching policy denies custom inputs before source analysis. Built-in fictional demos and the plugin's own generated reports remain available.

To remove this approval later:

```console
python -m salesforce_guard inputs revoke --policy-file ABSOLUTE_POLICY_FILE --root C:/ReviewData/release-1
```

Revocation stops future native reads of that folder. It cannot retract previous reports or data already shared with the model. A parent-folder approval also covers its descendants; revoke the parent if that is what granted access. The standalone operator CLI runs with the operator's own file permissions and does not use this native-tool boundary.

This is a profile tool control, not an OS sandbox. A local administrator or other program can change files. Project approvals are not independently signed; filesystem race resistance against a malicious local writer is not claimed. Approval writes are atomic and serialized; a busy update fails instead of silently overwriting another action.

## 8. Ask for the actual review

Give Hermes the absolute candidate and destination snapshot paths, your release manifest, intentional deletion manifests, and any matching before/after access evidence. Ask it to use `sfg_compare`, then inspect important changes with `sfg_impact` and `sfg_changes`. Add `sfg_scan` if you also want bounded security-pattern signals.

Open the generated HTML as the operator. In **What was actually checked?**, verify input coverage, capture timestamps, selected user, missing evidence and the next review action. Trace each important removal in the destination-before graph and inspect its caller source.

## 9. Make a human decision

Resolve unknown inputs, inspect high-impact references and decide what tests or additional captures are needed. Refresh destination snapshots before a later deployment because this review does not lock or recheck the org. A generated report is not approval to deploy. Guard does not deploy, execute anonymous Apex, delete components or change user permissions.

## If something stops

| Message or symptom | Operator action |
| --- | --- |
| Input not approved | Check `sfg_policy`, approve the correct project folder and acknowledge model sharing. Do not disable the guard. |
| Invalid policy | Inspect the local approval file; correct its schema/roots through the operator workflow. Never ask the model to edit it. |
| Approvals busy | Wait for the other operator action. If a crash left `.input-approvals.lock`, verify no approval command is running before manually removing that lock file. |
| Org identity mismatch | Verify the source/destination bindings; do not retarget an alias silently. |
| Missing or stale evidence | Recapture the authorized scope. Unknown is not denied or allowed. |
| No callers found | Check capture coverage and dynamic/unresolved relationships before drawing a conclusion. |
| Hermes cannot answer | Check the model connection and its usage limits separately from Salesforce authentication. |
