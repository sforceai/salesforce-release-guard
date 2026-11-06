# Your Salesforce Guard prototype

Version 0.4.2 unifies the report design around a release-review desk, with source impact and scoped user-access evidence. No org login is needed to inspect the fictional examples.

## Easiest way to inspect it

Open the supplied `Salesforce-Guard-Demo.html` in a browser. It contains actual results from the fictional Salesforce project. Scroll to Upstream & downstream impact, choose a component or method, then change the direction/depth. Click a connection to inspect its evidence. The OWASP table shows both partial coverage and categories not assessed.

Open `Salesforce-Guard-Comparison.html` for the release example. Filter by change classification, inspect an explicit deletion's before impact, and switch graph sides. Destination-only components remain in context. No video was generated for this release.

To regenerate the local demonstration after extracting the source ZIP, double-click `Demo.cmd` on Windows with Python installed. It opens a new local report. This simple demonstration runs the built-in checks; the optional external scanner has its own setup instructions in the README.

Double-click `Compare-Demo.cmd` to regenerate the fictional comparison. `Connect-Orgs.cmd` separately starts Salesforce CLI browser sign-in for your source/destination, with expected org-ID verification. Follow `docs/CONNECTIONS.md` for app setup, permissions, capture and disconnect. A scoped fictional Apex live test passed in two authorized Developer Edition orgs; other configurations still need verification. Do not paste credentials into chat.

## What works

- Local checks for Apex access-mode risks, broad permissions, Flow context and selected coding patterns.
- Source evidence, hashes, qualified findings, interactive reports and partial OWASP Top 10:2025 mapping.
- A clickable upstream/downstream impact explorer with explicit, conditional and unresolved connections, declared access context and suggested regression checks.
- A restricted native Hermes review profile that blocks unrelated tools while enabled.
- A separately tested Salesforce Code Analyzer integration, with raw findings and run receipts.
- Two-snapshot comparison with explicit scope/deletion intent, plus an operator-only source/destination login and metadata-capture bridge. The scoped fictional Apex live happy path is verified; broader cases remain open.

## What has not happened

Two authorized Developer Edition test orgs were connected and original fictional Apex fixtures were installed with passing tests. No business records or destructive changes were involved. This is a prototype, not a complete security audit. Its warnings need review, and its tool restriction is not an operating system sandbox.

The source repository and prioritized known issues have been created. No catalog PR, X post or hackathon form submission has been completed. The supplied submission kit contains the description, disclosures, catalog-entry generator and recording plan. Those account-level publication steps still need to be completed before entering the competition. A prize is not guaranteed.


## Selected-user access

Open `Salesforce-Guard-Access.html` in the delivery kit or double-click `Access-Demo.cmd` from the extracted source. These use fictional evidence. For live selected-user object/FLS collection and attaching it to reviews, follow [ACCESS.md](ACCESS.md). Record access and effective execution remain unassessed.
