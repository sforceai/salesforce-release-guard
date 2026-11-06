# Hackathon submission kit

## Entry description

Salesforce Guard adds release-impact and scoped-access review to Hermes. It compares a proposed release with a destination snapshot, requires explicit deletion intent, and traces supported upstream/downstream source references, including retained callers outside the release. Separate local evidence describes scoped user object/field access and configured Apex entry grants; record sharing and effective execution authorization remain unassessed. Bounded source heuristics provide review signals with partial OWASP mappings, not confirmed exploits or org-wide security assurance. Native tools persist interactive local reports, and a profile hook blocks unrelated tools while loaded and enabled. No live Salesforce credentials are needed for the fictional demo; conversational use needs the user's configured Hermes model.

The optional operator-only Salesforce Code Analyzer adapter runs PMD Security on staged source and preserves raw output, versions and incomplete/timeout receipts. Local findings are heuristic review signals, not verified exploits. It does not claim full OWASP coverage, AppExchange acceptance or an unbypassable OS boundary.

## Catalog PR description

Adds Salesforce Guard, a community plugin for release-impact and scoped-access review in a restricted Hermes profile. Catalog installation targets the `hermes-plugin` subdirectory, not the development repository root.

Surfaces: nine `ctx.register_tool` tools and one `pre_tool_call` hook. No core overrides, private runtime imports in the plugin, Desktop modifications or self-updating code.

Disclosure: native tools read supported Salesforce files and explicit snapshot/release/deletion manifests, inside operator-approved project folders or bundled fictional inputs; write profile-scoped local reports; perform no network calls, credential reads, shell commands or background work. Tool results go to the active Hermes model. Custom-folder approval explicitly acknowledges this sharing and is available only through the separate operator workflow; the model cannot grant it. Separate operator utilities can explicitly invoke installed Salesforce CLI for Code Analyzer, browser OAuth, fixed identity checks, scoped metadata listing/retrieval and explicit logout. Salesforce CLI owns token storage/refresh; this project reads no credential store or token-display output. Operator role bindings store aliases/org IDs without tokens. No deployment or anonymous Apex command is exposed. Dependencies have their own privileges. No telemetry. Reports contain source/schema information. The plugin intentionally blocks unrelated tools in its active review profile; install in a separate profile with no competing policy plugins. It is not an OS sandbox or a complete security assessment.

Validation: attach the current `docs/VERIFICATION.md` and genuine validation receipts from the exact pinned source. Do not claim checks not executed.

## Catalog entry

Generate the final entry with `python scripts/catalog_entry.py --repo https://github.com/OWNER/REPOSITORY --maintainer OWNER --sha FULL_40_CHARACTER_COMMIT --output output/salesforce-guard.yaml` after publishing and committing the final source. The generator rejects placeholders and non-commit pins. Add that YAML as `plugin-catalog/salesforce-guard.yaml` in a PR to `NousResearch/hermes-agent`.

## Remaining publication steps

1. Use the clean public source repository; keep runtime output and proprietary reports out of it.
2. Pin the final source commit and validate the packaged plugin against a current Hermes release.
3. Open the catalog PR. The announcement says an open PR is sufficient to submit; maintainer acceptance remains separate.
4. Review the prepared 70-second live demo, post it on X tagging `@NousResearch`, and retain its URL.
5. Submit the PR and demo URLs through https://form.typeform.com/to/FwJLvOln after checking its entrant/award terms.

Stated announcement deadline: 11 November 2026 at 5pm EST, equivalent to 12 November at 9am Sydney time. Recheck organizer updates before submission. No submission, public post, prize eligibility or payout has been claimed by this kit.


Version 0.4.0 adds scoped selected-user object/FLS observations and configured Apex entry grants. The operator collects fixed-shape access queries; native `sfg_access` imports only local evidence, with a credential-free fictional demo. Source/comparison reports can attach private evidence; comparison attachments must match captured org and role. Record sharing and effective execution remain unassessed. See `docs/ACCESS.md` and `docs/LIVE-VALIDATION.md`.


## Current presentation and admission status

See `docs/REQUIREMENTS-CHECK.md` for open gates and `docs/DEMO-FILM.md` for the prepared 70-second live recording and Indian English synthetic narration. The clean source repository is public; no X demo post, catalog PR or form submission has been made. An isolated authenticated native install passed; its bundle passed all 15 pinned-official-validator checks with a safe verdict and no admission warnings, as well as registered-handler checks. Earlier whole-source validation had a private-import warning in its operator test harness. These results do not establish a fresh dependency environment, anonymous public installation, or catalog acceptance.

Version 0.4.3 adds operator-approved custom inputs, a prominent report coverage/evidence panel, and an end-to-end first-review guide. See [verification and remaining limits](V043-IMPROVEMENTS.md).
