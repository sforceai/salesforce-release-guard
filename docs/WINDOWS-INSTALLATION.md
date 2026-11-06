# Windows installation: supported route and integrity check

Use a short Hermes home and a short, dedicated review-profile name. Do not put the review profile inside deeply nested project folders. Model configuration is separate; do not copy org credentials or your everyday profile.

## Supported setup

In PowerShell, choose a short folder you can write. This example uses a new home under Local AppData:

```powershell
$env:HERMES_HOME = Join-Path $env:LOCALAPPDATA 'HG'
hermes profile create review --no-alias --no-skills
hermes --profile review plugins install https://github.com/sforceai/salesforce-guard-release#hermes-plugin --ref bb14a41aa90f68b2a9a45c5ee61cfe8a41773ece --enable
```

Keep using that home when opening the profile. This is a separate environment, not a migration of existing settings or credentials. Configure its AI provider normally if you want a conversational demo. This release repository is public; GitHub authentication is not required for cloning it.

## Check the installed files

From a full source checkout containing the operator checker, with Python 3.10+:

```powershell
python scripts/check_install.py (Join-Path $env:HERMES_HOME 'profiles/review/plugins/salesforce-guard')
```

The native marketplace bundle does not install this operator script. It performs no network requests, model calls, commands, org access or writes. For the recorded v0.4.3 bundle, expect `complete`, 64 declared files and no problems. Exit code 2 means missing, unreadable, changed or invalid inputs. Stop and reinstall into a shorter supported location if incomplete. Checksums cover declared file bytes; the local inventory is not an independent signature or security certification.

Then ask for the fictional demo. Expect 1 new, 2 modified, 1 destructive, 1 unchanged, 0 unknown and 0 conflict; the separate access demo has 3 allowed, 8 denied and 0 unknown. Do not reinterpret an unknown row as a successful review.

## What was reproduced

On 7 November 2026, the normal installed Hermes Git workflow failed a fresh deep-path checkout with `Filename too long`. It kept installation scanning enabled. The host isolates Git global/system configuration and inherited config overrides, so merely setting global `core.longpaths` is not a reliable fix for that workflow.

A diagnostic-only invocation adding `-c core.longpaths=true` to Git got past checkout, but ordinary Windows file reads and temporary-folder cleanup still failed on long paths. That diagnostic is not a supported plugin install path, was not shipped, and did not alter installed Hermes code or system settings. Do not patch Hermes or turn off its guards to install this plugin.

A new short-home, short-profile install using the normal CLI passed all 64 source hashes, the complete fictional comparison, access and impact handlers, approval/revocation checks and pre-dispatch foreign-tool blocking. The new standalone checker also rejected the retained incomplete installation.

The historical two-file omission cannot be reconstructed fully from its retained logs. Controlled tests establish Windows long-path failures, not that every earlier omitted-file event has been forensically explained. Arbitrarily deep Windows installation remains unsupported; the supported short-path route is verified on the recorded host.

References: [Git for Windows long-path FAQ](https://gitforwindows.org/faq) and [Git configuration documentation](https://git-scm.com/docs/git-config). Installer/runtime observations above are executed local evidence, not claims that those references certify this plugin.
