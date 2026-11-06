# Impact explorer — 0.2.0

Select an Apex component/method, Flow/element, object, field or supported metadata node. Choose upstream, downstream or both, with depth 1–4. Click a node to refocus; click a connection's source location to inspect its evidence and boundary information. Findings with a supported source mapping offer an Inspect impact button. Unsupported mappings are labelled rather than silently failing.

## What the graph means

- Explicit reference: a supported source call, import, metadata connector or grant was found. It does not establish runtime execution or authorisation.
- Conditional relationship: a possible branch, scheduled path or record-write/Flow activation relationship. Conditions, deployed activation and runtime record values remain unverified.
- Unresolved target: supplied source cannot identify an implementation, overload, receiver or dynamic target. The graph shows the uncertainty instead of inventing a connection.

Structural containment identifies component scope but is not an execution step. A method selection does not automatically pull unrelated sibling methods into its downstream impact. Declared class-access grants are supplied as separate context; no permission-set assignment, group muting or effective-access calculation is claimed.

## Supported extraction

- Top-level Apex class/trigger source and supported method bodies; direct class calls, same-class calls and simple local declared receiver types.
- Unique method resolution by name/arity. Same-arity overloads, inheritance, nested types, property bodies and unresolved receivers are not inferred.
- Directly constructed or simply typed async jobs for enqueueJob, executeBatch, schedule and scheduleBatch. Future annotations are noted on resolved call boundaries.
- Static SOQL object and simple selected-field references; DML targets from simple local parameter/declaration types, with explicit user/system mode or API-aware defaults.
- Flow elements, normal/decision/fault connectors, scheduled paths, invocable Apex actions, subflow references and explicit record targets (including simple lookup-backed input references).
- Conditional links from supported DML operations to source-declared active record-triggered Flows with matching objects/events. Entry filters, prior values, transaction order, installed overrides and deployed activation are not evaluated.
- Apex class and field-access grants in permission/profile XML, and supported single-line LWC Apex imports.

Dynamic SOQL object/field dependencies are not resolved. No single source-only graph can prove complete org-wide impact. Unsupported input references and external source boundaries stay visible as gaps. Object/field references do not establish that those definitions exist in an org.

## Limits and security

Maximum 2,500 graph nodes, 6,000 graph relationships and 120 nodes in a queried/displayed view. Query depth is limited to four. Cycles terminate through visited-node tracking. Graph-limit gaps are separate from scanner traversal/parsing gaps. A completed local scan can therefore still have a partial graph; inspect both.

Source-derived labels, excerpts and paths are treated as untrusted text. Apex string literal values are redacted from excerpts. Graph JSON escapes script-delimiter characters, and the UI uses textContent/DOM APIs for source values. There are no remote graph assets, model calls, live org requests, automatic fixes or deployments.

Regression suggestions cover allowed/denied callers, record effects, fault/recovery routes, async revalidation, duplicates and least-privileged access where supported references justify them. Suggestions are not an executed test plan or proof that controls protect every path.

## Demonstration provenance

The shipped expense-workflow examples were written for this project and are fictional, non-deployable fixtures. No customer repository, proprietary application, production process map or customer schema is bundled or used as demonstration data.
