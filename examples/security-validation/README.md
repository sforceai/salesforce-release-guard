# Validation-only security fixture

Original fictional Apex tests for the object and permission sets in `examples/access-validation`. Execute only with an explicit, operator-authorized `--dry-run` deployment and `RunSpecifiedTests` for `SFGSecurityBoundaryTest`.

The tests create disposable users and fictional records inside test transactions; all roll back. No class installation is required. Do not deploy this fixture as a business service. It deliberately includes explicit system-mode operations to demonstrate the difference from user-mode enforcement.

The supplied test orgs reported five passing methods each. See [sanitized test evidence](../../docs/SECURITY-TESTING.md). No org details or credentials are included here.
