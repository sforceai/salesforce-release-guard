"""Original rule descriptions, mapped to OWASP Top 10:2025 categories.

Mappings are contextual triage aids, not OWASP certification or exhaustive coverage.
"""
OWASP = {
    "A01": ("Broken Access Control", "partial", "Privileged Apex operations, sharing declarations and permission grants."),
    "A02": ("Security Misconfiguration", "partial", "Broad grants and Flow execution context; no live org configuration audit."),
    "A03": ("Software Supply Chain Failures", "not_assessed", "No dependency provenance or package vulnerability database."),
    "A04": ("Cryptographic Failures", "partial", "Legacy digest algorithms and credential-shaped literal assignments."),
    "A05": ("Injection", "partial", "Concatenated dynamic SOQL and unescaped Visualforce output signals."),
    "A06": ("Insecure Design", "not_assessed", "Requires business requirements, architecture and threat modelling."),
    "A07": ("Authentication Failures", "not_assessed", "No authentication flow or session testing."),
    "A08": ("Software or Data Integrity Failures", "not_assessed", "No build integrity or trusted-data verification."),
    "A09": ("Security Logging and Alerting Failures", "partial", "Debug logging signals only; no assessment of alerting effectiveness."),
    "A10": ("Mishandling of Exceptional Conditions", "partial", "Empty catch blocks; no complete error-path analysis."),
}

RULES = {
    "APEX001": ("Explicit system-mode database operation", "high", "A01", "Verify operation-specific authorisation, record scope and CRUD/FLS intent. Use user mode where caller permissions should apply; retain justified privileged automation."),
    "APEX002": ("Legacy implicit database access mode", "medium", "A01", "Trace the caller and any applicable permission checks. For API <=66, consider explicit user-mode operations when caller permissions should apply. A file-level signal is not proof of a bypass."),
    "APEX003": ("Class bypasses record sharing", "medium", "A01", "Review exposed entry points and why cross-record access is needed. This declaration alone does not establish a CRUD/FLS bypass."),
    "APEX004": ("Concatenation in dynamic SOQL expression", "high", "A05", "Trace values into the query. Prefer bind variables and queryWithBinds with user mode; allowlist identifiers. Concatenation of trusted constants may be justified."),
    "APEX005": ("Legacy digest algorithm", "medium", "A04", "Determine whether this is security-sensitive. Use an appropriate modern cryptographic construction; do not change an interoperable checksum blindly."),
    "APEX006": ("Empty exception handler", "medium", "A10", "Define failure behaviour, rollback and appropriate diagnostics. Verify callers cannot interpret failure as success."),
    "APEX007": ("Debug output requires data review", "low", "A09", "Review logged values for records, credentials and personal information; reduce or redact sensitive output."),
    "APEX008": ("Credential-shaped literal assignment", "high", "A04", "Confirm whether this literal is a credential. If real, rotate it and use Salesforce Named/External Credentials. Evidence values are redacted."),
    "META001": ("Broad user permission enabled", "high", "A02", "Confirm the intended population and business need. Prefer narrower permissions. A grant is confirmed; unintended exposure is not established."),
    "META002": ("Object-wide record access enabled", "high", "A01", "Review assignment population and sharing requirements. Effective user access requires profile, permission-set-group and muting context."),
    "META003": ("Field edit access granted", "medium", "A01", "Confirm this field should be editable for the assignment population. Field sensitivity and effective user permissions are not inferred."),
    "FLOW001": ("Flow declares system execution context", "medium", "A02", "Inspect Flow type, entry point, running principal and downstream Apex. Intentional system automation requires bounded inputs and authorisation."),
    "VF001": ("Visualforce output escaping disabled", "high", "A05", "Trace output values and sanitisation. Enable escaping for untrusted text or verify an appropriate HTML sanitiser."),
}

SOURCES = [
    {"title": "Salesforce Apex security and API-version defaults", "url": "https://developer.salesforce.com/docs/platform/lwc/guide/apex-security.html"},
    {"title": "Salesforce database access modes", "url": "https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-classes-enforce-usermode.html"},
    {"title": "Salesforce Code Analyzer", "url": "https://developer.salesforce.com/docs/platform/salesforce-code-analyzer/guide/analyze.html"},
    {"title": "OWASP Top 10:2025", "url": "https://owasp.org/Top10/2025/"},
    {"title": "Hermes plugin extension API", "url": "https://hermes-agent.nousresearch.com/docs/developer-guide/plugins"},
]
