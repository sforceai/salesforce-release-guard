# Fictional live-validation fixtures

Original examples for two separate disposable Salesforce test orgs. No customer metadata, data, org addresses, IDs or credentials are included.

`candidate` contains four Apex classes, including one test class. `baseline` contains five, including one test class. All component names start with `SFGExample`. They perform pure integer calculations and return a fictional label. They contain no queries, DML, callouts, triggers, Flows, permission assignments or scheduled jobs.

The candidate changes the review service and its test, adds a policy class and retains an unchanged helper. The baseline includes legacy rules and an existing caller. `release.xml` scopes the proposed change. `context.xml` includes the surrounding references for capture. `delete-review-only.xml` declares a proposed deletion for local review only: the existing caller deliberately demonstrates a remaining dependency.

Do not deploy the deletion manifest. No deletion was performed during the live validation. These fixtures are separate from the intentionally risky, non-deployable scanner examples.

Installation is an operator action outside the review plugin. Before installing into disposable orgs, verify their identities, refuse existing component-name collisions, validate each exact project using `SFGExampleFixtureTest`, and inspect the deployment result. Never assume a supplied org is disposable or overwrite existing components.

Captured snapshots and generated reports contain org provenance and must remain private in excluded output folders. Public evidence should use only a sanitized summary.
