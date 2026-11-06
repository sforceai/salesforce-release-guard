# Clean public release verification

Verified 7 November 2026. Repository: https://github.com/sforceai/salesforce-guard-release

Tested runtime pin: `bb14a41aa90f68b2a9a45c5ee61cfe8a41773ece`. Later documentation-only commits retain the same native bundle. [Sanitized receipt](evidence/public-release.json).

## Installation and execution

- Anonymous installation into two empty short-path profiles passed, including the README profile name. No GitHub credentials were resolved; installation scanning remained enabled. All 64 recorded source hashes matched.
- Registered native-handler verification passed: 1 new, 2 modified, 1 destructive, 1 unchanged, no unknown changes; 2 before-change callers; 3 allowed, 8 denied, no unknown scoped access checks. Foreign-tool blocking and custom-input approval/revocation checks passed.
- Official admission validation passed all 15 checks with a safe verdict and no admission warnings, using validator source `65a0cb48510db539442dd56490babbe465acc096`. This used the existing host virtual environment, not a fresh dependency installation. Installer heuristic signals are separate from admission warnings; neither establishes complete security.
- [Public CI](https://github.com/sforceai/salesforce-guard-release/actions/runs/42312710905) passed all four Windows/Linux Python 3.11/3.12 jobs against documentation commit `d3482bf4d191fb0a87bf9314781196aa03fb2ed1`.
- A real Hermes CLI conversation using Nous `upstage/solar-mini4:free` called native tools, returned the expected comparison/access counts and both deletion callers, and generated local HTML reports. This used an existing separately authenticated model profile with the tested public runtime. Model availability is independent of anonymous installation.

## Required host compatibility setting

On the tested Hermes host, deferred plugin tools were routed through generic `tool_call`, which Guard intentionally blocks. Setting `tools.tool_search.enabled` to `off` in the dedicated review profile exposed native schemas directly and allowed the successful conversation. The guard was never disabled or broadened. See [installation](INSTALLATION.md) for the command. This is a verified host configuration, not a claim of compatibility with every Hermes version.

## Privacy and limits

The clean history contains only approved `info@sforce.ai` attribution; prior development commits are excluded. An anonymous mirror audit found no configured private-data candidates or forbidden runtime/media paths. The old repository remains private. Raw host logs, model sessions, credentials, local paths and branded media are not published.

No live Salesforce connection, deployment or customer data was used in this public verification. Arbitrary deep Windows paths remain unsupported by this evidence; use the documented short-path route. Historical recordings predate this publication. No fresh Desktop recording, catalog acceptance, X post, form submission or prize result is claimed.
