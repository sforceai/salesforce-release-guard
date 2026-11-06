# Native plugin installation

Prerequisite: Hermes is already installed. Create an empty review profile once; do not clone your everyday profile:

```console
hermes profile create salesforce-guard-review --no-alias --no-skills
```

Use that dedicated profile with no live org credentials or competing policy hooks. Configure an AI provider separately for conversational use. Provider charges and usage limits apply; the plugin itself requires no paid scanner or Salesforce connection for the fictional demo.

One install command, pinned to the tested development version:

```text
hermes --profile salesforce-guard-review plugins install https://github.com/sforceai/salesforce-guard#hermes-plugin --ref 811323f502d1b4b3ee7a77d4120d30e062d87eb9 --enable
```

Desktop's Install from Git accepts the same repository fragment. Select the review profile and a reviewed full commit. Do not change repository visibility to resolve authentication. A private repository needs GitHub authentication on the installing computer. Model sign-in is separate and profile-specific.

Open the review profile after installation, then paste this demo request:

> Review the fictional Salesforce Guard release demo. Show what's new, modified and explicitly deleted, trace the deletion's before-change callers, and run the separate fictional user-access demo. Use the native Guard tools, give a concise summary and the local HTML report paths. No live org access or deployments.

Expected fixture results: 1 new, 2 modified, 1 destructive, 1 unchanged; 2 static callers of the removed utility; 3 allowed, 8 denied and 0 unknown scoped access checks. Open the generated local HTML files as the operator. The reviewing agent's browser tools remain blocked.

If a gateway already loaded an earlier version, its active policy may require a reload. A Desktop window restart alone did not reload the shared gateway in our Windows test. Do not run an unattended gateway-service setup to solve this; see [the observed restart behavior](DESKTOP-VERIFICATION.md).

## What has actually been proved

- Exact pinned native bundle installed and enabled in a new empty Hermes home on 6 November 2026, using existing GitHub authentication. This used the installed Hermes runtime on the current Windows host.
- v0.4.3 installed registered-handler checks passed, including approval, rejection and revocation. The earlier real Desktop/model-driven fictional workflow is recorded separately; it was not rerun for v0.4.3.
- **Anonymous public installation is pending:** the GitHub repository is still private. A public clone, exact-pin install and judge demo request must be repeated after the owner approves publication and the final source commit is selected.

The development pin above is not a substitute for final-release validation or catalog acceptance.

## Why a separate bundle

The development root contains tests with deliberately malicious XML and synthetic credential strings, live-validation fixture setup metadata, and operator-only Salesforce CLI/browser/video utilities. A real install attempt scanned these development files and returned DANGEROUS (22 findings), including two critical test-fixture matches. Installation was blocked; the scan was not disabled or overridden.

`hermes-plugin/` contains the native entry point, manifest, license, the complete dependency closure of its nine tools, and their fictional demo inputs. It does not contain operator-only modules, tests or development scripts. All included source bytes are unchanged copies of the root source; `BUILD.json` records their SHA-256 hashes and `python scripts/build_plugin.py --check` enforces parity in CI. This is distribution scoping, not a scanner suppression or a security exemption. All shipped runtime code is scanned.

The installed Hermes scanner returned SAFE / ALLOWED for the native bundle, with ten medium heuristic findings. These match Salesforce permission-metadata handling and JSON escaping in local HTML visualizations. SAFE does not mean no findings or a complete security audit. The earlier whole-repository catalog validation is a different check and does not replace testing the actual installer.

## Verification

Run Doctor and registered-handler checks against the native bundle, install it at a pinned Git commit, confirm nine tools in the Desktop review profile, then test a real model-driven fictional comparison and access report. The earlier Desktop workflow passed on 6 November 2026; v0.4.3 installed-handler and admission checks passed separately, without a new model-driven Desktop recording; see [Desktop verification](DESKTOP-VERIFICATION.md) for results, the gateway reload issue, and scope. Repeat these checks for a changed release or host. Never disable install scanning, use a dangerous-verdict bypass, or copy org credentials into the review profile.

## Reviewing your own files (v0.4.3)

The fictional demo works immediately. Custom source, manifests and access evidence require an operator-approved project folder. Run `sfg_policy` to obtain this profile's approval-policy location, then use the separate full-source operator CLI to approve only the required folder and explicitly acknowledge model sharing. Native tools cannot grant themselves approval. See [Your first review](FIRST-REVIEW.md) for exact commands, the two-org capture workflow and revocation.

The marketplace bundle does not install the operator CLI or `Connect-Orgs.cmd`. Requested excerpts and evidence returned through Hermes reach the selected AI provider. Use a provider/environment approved for the data. Folder approval controls native inputs; it does not provide OS isolation or retract previous reports/model data.

Version-specific verification and limits are recorded in [v0.4.3 improvements](V043-IMPROVEMENTS.md). Earlier Desktop/video receipts describe their recorded version, not an unperformed new Desktop run.

## Confirm installation completeness

Check the exact fictional counts above, not only the installer's success message. An unexpected unknown row means the demo is incomplete. The current source verification harness checks every shipped BUILD.json hash and the full expected comparison summary. A deep isolated Windows installation was observed missing two fixtures; a shorter-path installation of the same pin passed every file hash and all fixture counts. Long-path compatibility remains an open issue in [Known issues](KNOWN-ISSUES.md). Never hide the unknown row or disable installation scanning.

For Windows, use [the tested short-folder installation and standalone integrity check](WINDOWS-INSTALLATION.md). Global Git long-path settings alone do not address all observed host limits.
