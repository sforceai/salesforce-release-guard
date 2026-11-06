# Verification record — 0.4.1 · 5 November 2026

> Historical development evidence: old development commit IDs below are retained as receipt identifiers and are not install pins in the clean public history. Use [PUBLIC-VERIFICATION.md](PUBLIC-VERIFICATION.md) for current public installation.

## Executed

- Local Python unit/integration suite: 171 tests, 170 passed and one skipped. Includes snapshot/deletion controls, connection/capture isolation, access query injection refusal, stale/incomplete/mismatched evidence, object-gated field results, inactive users, session/expired/recalculating group handling, comparison org/role binding and Salesforce's normalized 18-character computed-access user suffix.
- Native Hermes 0.21.2 Doctor against the source-only v0.4.1 package: no registration errors; nine tools and one hook discovered. The registered access handler generated the fictional result of three allowed and eight denied scoped observations.
- Installed Hermes validation: all ten checks supplied by this installed version passed, with no warnings. This older installed validator does not provide every gate described in the latest online catalog documentation; current admission CI remains outstanding.
- Real Hermes runtime: invokes the registered hook for demo/impact, terminal, Salesforce Apex execution, Salesforce deployment and messaging tool identities. Review tools are allowed; the four foreign identities are blocked. Dangerous tools are never executed. The registered demo handler generated 15 review signals over 20 fictional source files; the registered impact handler returned a dependency slice with evidence.
- Real registered comparison tools: fictional comparison returned one new, two modified, one destructive and one unchanged component; the change-report tool returned all five rows and the impact tool retained upstream before-deletion references.
- Real Salesforce Code Analyzer CLI plugin 5.15.0: explicitly installed into a workspace-only tools directory and linked into an isolated CLI data directory. PMD Security scan completed on staged fictional source and returned three high-severity scanner observations: ApexSOQLInjection, ApexCRUDViolation and VfUnescapeEl. Raw output reports Code Analyzer core module 0.52.0 and PMD engine module 0.45.0. These engine findings are unconfirmed and may overlap local signals.
- Isolated headless Edge: desktop and 390px mobile layouts rendered; severity/search filters, upstream import navigation, downstream conditional activation, connection evidence, scheduled/invocable/fault/async relationships and finding-to-map navigation passed; no page-wide mobile overflow. Screenshots visually inspected.
- Comparison browser checks: change filters, explicit deletion selection, before/after switching, absence of stale graphs for missing/deleted components, evidence controls and 390px mobile overflow checks passed. Desktop/mobile screenshots visually inspected.
- Operator auth/capture tests use fictional CLI responses, not user credentials. They cover both roles, wrong org IDs, retargeted aliases, missing/null/truncated inventory, incomplete retrieves, disconnection, raw-output redaction and excluded parent token/Node injection variables. Installed Salesforce CLI invocation is smoke-checked with the login command's help only; no sign-in is initiated.
- No MP4 was generated for this release.

- Hardening regression checks: arbitrary business-record queries refused before execution; login/logout hold the registry lock during CLI calls; option-like client IDs and deeply nested metadata XML rejected. Reports explicitly mark effective user access as not assessed.
- Synthetic comparison benchmark: 500 components / 1,001 files per snapshot; 50 modifications and 450 unchanged correctly classified in 9.125 seconds with allocation tracing enabled; peak traced Python allocations 5.04 MiB. One local Windows/Python 3.12 measurement, not a live-org load test or scalability guarantee. See `scripts/benchmark.py` and delivered `benchmark-result.json`.

- v0.4.0 live selected-user configuration: two newly created Minimum Access users returned 0 allowed/11 denied before assignment and 3 allowed/8 denied after the fictional read-only assignment, with zero unknown observations. The withheld field and all scoped writes stayed denied. Live evidence also attached to the captured comparison with both org/role bindings verified. See LIVE-VALIDATION.md.
- Fictional access HTML: 11 check rows, three allowed/eight denied; limitations visible; desktop and 390px mobile layouts passed without page overflow. Mobile cards visually inspected.

## Not executed / limitations

- One actual filesystem symlink test is skipped because this Windows account cannot create symlinks. Traversal checks remain covered by source review; no claim of race-proof filesystem isolation.
- Live happy-path browser authorization, expected-org identity checks, fictional Apex validation/installation with tests, scoped capture and comparison passed in two authorized Developer Edition orgs. See [sanitized live evidence](LIVE-VALIDATION.md). Scoped object/FLS and configured Apex grants now have separate live evidence. Record access, effective execution, live authorization failure/revocation cases, broader metadata types, sandbox integration, AppExchange review and proprietary code review remain unverified.
- No model-driven Hermes chat and no video posted to X. Runtime tests are deterministic host integration checks, not proof of a model's choices.
- Source repository publishing and known-issue creation are complete. PR #7 CI passed all four Windows/Linux Python 3.11/3.12 jobs at head c9055b136dd43419e908bf241473d1c6d67452dd (run 42023193265). Current catalog admission review and hackathon submission remain outstanding. The tested v0.4.0 PR is open pending explicit merge authorization.

## Earlier attempts retained accurately

The Hermes stall was narrowed to using the full development workspace as Doctor input. The source-only package completed verification promptly. The harness now refuses development roots containing runtime/output folders, prints stage diagnostics and verifies the packaged plugin. The first v0.4.0 host run exposed a package-relative import error in the new handler; it was corrected and the native check passed. Live custom-object access initially stayed unknown because Salesforce normalized the composite user suffix from 15 to 18 characters; identity normalization was fixed, with regression coverage. These unsuccessful attempts are not counted as passing evidence.

The first 0.3.1 Hermes verification rerun produced no output and was interrupted; it is not counted as a successful run. The separately recorded completed receipt is the evidence for the host integration checks.

The first test invocation encountered Windows temporary-folder access restrictions. Rerunning with a workspace-owned temporary directory resolved these infrastructure errors; do not interpret them as scanner findings. The first external scanner attempt encountered an absent JIT plugin and timed out; it did not constitute a completed scan. The adapter was hardened to check installed plugins before scanning, refuse JIT-only availability, stop its owned process tree on timeout, and preserve incomplete states. The later isolated PMD scan is a separate successful run.

## Scope

This release is a working local prototype with real native Hermes registration, comparison/impact tools and a tool gate, a separately exercised external SAST adapter, and an operator-only Salesforce CLI authentication/capture bridge tested with fictional responses. It is not a production security guarantee or a contest acceptance result.

All new graph examples are original fictional expense-workflow fixtures. No customer process map, source archive, proprietary schema or product name is included. Source and delivery archives are checked for accidental proprietary references before delivery. The graph is a bounded static reference view; it does not establish complete runtime impact or effective authorisation.


## v0.4.1 broader security pass

See [SECURITY-TESTING.md](SECURITY-TESTING.md) for five validation-only runtime methods passing in each org, malformed-response correlation regressions, strict bounded JSON parsing, same-read evidence hashing and the verified outer host timeout. No persistent test class or test-created records/users were saved. v0.4.1 remote CI is tracked separately from the earlier v0.4.0 run.


## v0.4.2 presentation and current admission check

The three local reports share an original offline visual identity and use no external fonts or assets. The comparison hero promotes a real deletion/reference count and its action opens the before graph. Browser checks passed for filters, evidence, stale-graph clearing and desktop/mobile overflow; access-panel text contrast measured 14.45:1. Screenshots were visually inspected and a dark-panel contrast regression was corrected before delivery. The local 171-test suite still passes (170 passed, one skipped).

Pinned current official validator source 65a0cb48510db539442dd56490babbe465acc096 passed 15 checks and reported install scan safe. One warning concerns operator-only verification-harness private core imports; native runtime code uses supported registration APIs. This was run with existing installed dependencies, not a fresh --install-deps installation or maintainer admission. See docs/evidence/current-admission.json and REQUIREMENTS-CHECK.md.
