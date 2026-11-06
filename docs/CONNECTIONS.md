# Secure source/destination connections — operator bridge

The separate operator utilities use Salesforce CLI for authentication and capture. Obtain the full source checkout at the same reviewed commit as the native plugin; the marketplace `hermes-plugin/` bundle does not include `Connect-Orgs.cmd` or the operator CLI. Follow [the first-review walkthrough](FIRST-REVIEW.md) for setup through interpretation. Native tools intentionally receive local snapshots and never start sign-in, read Salesforce CLI credentials or gain generic org-execution tools.

Salesforce CLI owns browser OAuth, PKCE/client handling, credentials, refresh and optional logout. The bridge never reads `.sf`, `.sfdx`, a keychain, an auth JSON file or a token. It does not call token-display commands. Its own connection registry contains generated aliases, expected org IDs, login URLs, environment flags and timestamps only. Native/model-facing tools have no connection-mutation capability.

## Connect both orgs

With Python and Salesforce CLI installed, double-click `Connect-Orgs.cmd`. Supply each org's login/My Domain URL and expected org ID from Setup → Company Information. Use the browser to authenticate. Do not paste a password, token or client secret into the wizard or chat.

For a custom External Client App, enter its public client ID and configure it for the Salesforce CLI web-server/PKCE flow and loopback callback. Use an admin-approved app where your org requires one. A client configuration requiring an interactive secret is not supported by this non-secret bridge. With no client ID, Salesforce CLI uses its own default client subject to your org's policies. This project does not impersonate another OAuth client or build its own refresh-token store.

Command-line equivalent:

```console
python -m salesforce_guard org login source --instance-url https://example-source.my.salesforce.com --expected-org-id YOUR_SOURCE_ORG_ID
python -m salesforce_guard org login destination --instance-url https://example-target.my.salesforce.com --expected-org-id YOUR_DESTINATION_ORG_ID
python -m salesforce_guard org status --verify
```

Example URLs are fictional placeholders. Substitute your actual org URLs/IDs. Each role gets a unique generated alias; neither becomes the default org. A fixed Organization identity query verifies the ID before binding and again around capture. Source and destination cannot be the same org. Retargeted aliases, failed authorisation, wrong IDs and unfinished retrievals are rejected. Registry updates are atomic and serialised. This is not protection against a malicious local administrator or a modified installed Salesforce CLI.

## Capture scoped snapshots

In v0.4.3, custom inputs passed to native Hermes review tools also need operator folder approval and model-sharing acknowledgement. Authentication alone does not grant that approval. Keep your manifests, snapshots and access evidence together in a private review folder; see [step 7 of the walkthrough](FIRST-REVIEW.md#7-approve-the-folder-for-the-native-review-tools).

Use an explicit context manifest containing the proposed components, intended deletion targets and existing callers/dependencies that should be reviewed. A release-only export cannot reveal the entire destination's upstream context.

```console
python -m salesforce_guard org capture source --manifest context.xml --output output/snapshots
python -m salesforce_guard org capture destination --manifest context.xml --output output/snapshots
```

The bridge lists requested metadata types, retrieves only existing explicit members into a fresh controlled DX project, checks completion and identity, and writes a hashed snapshot. Components absent from a supported scoped listing get named absence declarations; no complete org-wide coverage is claimed. Child/standard metadata whose absence cannot be established remains unknown. Listings at the conservative 1,000-item boundary and incomplete/unreadable retrieves are refused. Capture is limited to 200 explicit requested components; comparison supports larger bounded local exports.

If CLI discovery fails on Windows, use the known installed executable paths, before the `login`, `status` or `capture` subcommand:

```console
python -m salesforce_guard org --node C:\tools\node.exe --sf-js C:\tools\salesforce-cli\bin\run.js status
```

No `.cmd`, `.bat` or `.ps1` launcher is evaluated by the transport. It uses argument arrays with `shell=False`. CLI errors are sanitised; raw CLI stdout/stderr is discarded rather than included in reports. Parent access-token variables and `NODE_OPTIONS` are not inherited. Install/maintain the official CLI separately; the bridge installs nothing.

## Disconnect

```console
python -m salesforce_guard org disconnect source
python -m salesforce_guard org disconnect destination --revoke
```

Default disconnect removes the local role binding only. `--revoke` explicitly asks Salesforce CLI to log out the bound user after identity verification; that may affect other CLI work using the same authorised user. No token files are edited by this project.

## Permission and privacy boundaries

Metadata APIs can require powerful Salesforce permissions. OAuth `api` and a user's metadata permissions are not inherently read-only. The bridge limits its own operations to login, fixed identity queries, metadata listing/retrieval and explicitly requested logout; it exposes no deploy, delete, business-record query or Apex execution command. Other programs and direct use of Salesforce CLI can still use the same authorisation according to that user's actual permissions.

Snapshots contain source code and schema information. Keep them, the `.sfg-connections` directory and reports out of public repositories; the provided ignore rules exclude generated outputs and connection state. A scoped live happy-path test of browser authorization, identity checks and fictional Apex capture passed in two authorized Developer Edition test orgs; see [live validation](LIVE-VALIDATION.md). Automated adverse-path tests use fictional CLI responses. Other metadata types, user privileges, custom app policies and live failure/revocation cases still need validation before production reliance.

Official references:

- https://developer.salesforce.com/docs/platform/salesforce-cli-reference/guide/cli_reference_org_login_web.html
- https://developer.salesforce.com/docs/platform/sfdx-dev/guide/sfdx-dev-auth-eca.html
- https://developer.salesforce.com/docs/platform/salesforce-cli-reference/guide/cli_reference_org_list_metadata.html
- https://developer.salesforce.com/docs/platform/salesforce-cli-reference/guide/cli_reference_project_retrieve_start.html
- https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission


## Scoped selected-user configuration

The separate `org access` action performs fixed, validated setup/access SELECT queries for an explicitly selected user. It writes private object/FLS observations and configured Apex entry-grant evidence for local review. It does not add generic queries or writes to the bridge. See [ACCESS.md](ACCESS.md).
