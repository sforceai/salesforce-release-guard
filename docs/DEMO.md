# Working demo recording plan — under 90 seconds

Version 0.2.0 includes a narrated walkthrough of genuine report/impact-map captures and recorded Hermes runtime checks. It is not a live model chat. All screenshots and narration use fictional examples.

Use only the fictional sample source. Record actual output; do not substitute an animation for a working Hermes execution.

1. **0–12 seconds — problem:** “A Salesforce permission change and an AI with admin tools can create a dangerous combination. Salesforce Guard gives Hermes a restricted security-review profile.” Show the plugin enabled in a dedicated profile, then ask it to run `sfg_demo`.
2. **12–35 seconds — evidence:** Open the generated local report. Show the explicit system-mode operation, broad permission grant and dynamic query signal. “These are review findings, with source locations and guidance—not automatically proven vulnerabilities.”
3. **35–50 seconds — impact:** Select the fictional expense Flow in the impact explorer, expand downstream, and inspect its scheduled, invocable, async and fault connections. “These are source references, with conditional activation and unresolved gaps labelled; authorisation is not proven by an arrow.”
4. **50–65 seconds — enforcement:** Ask the review agent to invoke a terminal command or Salesforce deployment tool. Show Hermes returning Salesforce Guard's block message. Do not execute a real deployment. If the model refuses before making the call, show the real runtime verification receipt instead and describe it accurately; do not imply a model refusal is proof that the hook ran.
5. **65–80 seconds — coverage:** Show the OWASP coverage matrix, including categories not assessed. “The report states its limits. The optional Code Analyzer adapter preserves its own scan receipts.” Do not say external SAST ran unless its actual receipt confirms it.
6. **80–88 seconds — close:** “Local review, explicit evidence, and a narrower agent tool boundary. No Salesforce credentials needed for this demo.”

## Suggested X post

Built Salesforce Guard for the @NousResearch Hermes Plugin Hackathon: local Apex/metadata security triage, OWASP Top 10:2025 mappings, a private interactive report, and a restricted review profile that blocks unrelated agent tools. Demo uses fictional source. Findings require human review. [Add public repository link and attach actual demo video.]

## Reproduce without a model

Run `python -m salesforce_guard demo --output output`. It generates the report and prints clearly labelled policy evaluations. Real Hermes registration and hook verification is performed by `scripts/verify_hermes.py`. These are separate from an end-to-end model-driven chat demonstration.
