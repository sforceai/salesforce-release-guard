# Design and scope

The native entry point registers nine tools and one tool-control hook through supported Hermes APIs. No core patching, self-updater, remote code loader, binary payload, secrets access or overridden tools.

`scan.py` inventories supported source and companion metadata, hashes original bytes, masks comments/string literals, produces explicitly qualified signals, and records traversal/parsing gaps. `rules.py` defines original explanations and OWASP mappings. `report.py` escapes all source-derived HTML data and uses no network assets. `policy.py` defaults to denial for every tool identity outside an exact allowlist. Registration itself performs no file writes or network calls.

The plugin intentionally offers no Salesforce executor. It cannot fix, deploy, query a live org or run anonymous Apex. The review restriction blocks foreign tools in its active profile, including seemingly read-only connectors, instead of trying to classify arbitrary shell strings or tool arguments. This is restrictive but makes the boundary small and testable. Source can still be read by the bounded scan tool. Source content remains untrusted and should not be interpreted as instructions.

The standalone analyzer adapter is separated from model-facing tools. It copies only the supported source snapshot, writes a controlled PMD-only configuration, invokes an operator-selected installed executable without shell evaluation, and retains raw findings and an execution receipt. An external scanner finding is not automatically promoted into a confirmed local vulnerability. A changed source snapshot prevents results being represented as one coherent scan.

## Limits

At most 4,000 supported files, 1 MiB per file, 32 MiB total source and 20,000 visited directory entries. Unsupported files and generated directories are outside scope. Tests are inventoried separately and not used to inflate production analysis. Unknown API versions, unreadable/oversized files, linked directories, parsing errors and empty production scope are recorded as incomplete. XML DTD/entity declarations are rejected. This is not a full XML schema validator or Apex compiler.

The impact extractor adds bounded static call/import/metadata relationships. It does not prove interprocedural authorisation, assignment populations, guest accessibility, effective CRUD/FLS, runtime Flow-to-Apex path feasibility, async principals, sanitiser correctness or actual exploitability. `with sharing` and database access modes remain separate evidence. An intentional privileged service may be correct, and requires a human disposition rather than an automatic rewrite.

`impact.py` models components, Apex methods, Flow elements, objects/fields, LWC imports and permission metadata. Structural source containment is separate from execution/dependency edges. Record-write-to-Flow links are conditional object/event matches; they do not evaluate prior values or entry filters. Unknown targets remain explicit unresolved nodes. Node/edge/query limits and extraction gaps are retained in JSON and the local report. `impact_view.py` renders an SVG view and evidence table using DOM text APIs, never source-derived HTML or remote assets.

Native tool results contain metadata names and redacted Apex excerpts, not complete source. The active model receives requested results. Reports and scanner logs can still reveal private schema information. Keep proprietary results private.

## Future work

Parser-backed data-flow integration; effective-access calculations using scoped org metadata; targeted least-privileged sandbox tests; native Desktop SDK report pane; granular operations with scoped human approval. None of these are claimed as shipped in 0.3.0.

## Snapshot comparison and connections

`snapshot.py` inventories supported component identities and canonical fingerprints, preserves metadata companions and validates optional capture hashes. Absence requires a declared complete type or a named absence record; missing files alone remain unknown. `compare.py` classifies explicit release/deletion intent, retains destination-only context, and builds before/proposed-after source graphs. It never performs deployment, metadata deletion or live drift locking. `comparison_view.py` switches graph sides and clears absent-component views so stale nodes cannot masquerade as the selected component.

`orgs.py` is imported only by the operator CLI/wizard, never by native tool registration. The installed host lacks the newer Hermes OAuth helper. The bridge therefore delegates browser OAuth, token lifecycle and scoped metadata capture to installed Salesforce CLI instead of implementing a token store or reading another tool's authentication. It binds distinct roles to expected org IDs, serialises registry writes, verifies identity around capture and refuses unfinished/truncated/unreadable responses. No model-facing auth or org execution tool is registered. Live Salesforce verification is outstanding; current integration tests use fictional CLI responses.
