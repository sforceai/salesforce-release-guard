import argparse
from pathlib import Path
import re
from urllib.parse import urlparse


def main():
    parser = argparse.ArgumentParser(description='Generate a pinned community catalog entry after publication.')
    parser.add_argument('--repo', required=True)
    parser.add_argument('--maintainer', required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    url = urlparse(args.repo)
    parts = url.path.strip('/').removesuffix('.git').split('/')
    if url.scheme != 'https' or url.hostname not in {'github.com', 'gitlab.com'} or url.username or url.password or url.query or url.fragment or len(parts) < 2 or any(not re.fullmatch(r'[A-Za-z0-9_.-]+', p) for p in parts):
        parser.error('Use a public HTTPS GitHub/GitLab repository URL without credentials.')
    if any(p.lower() in {'owner', 'repository', 'repo', 'yourname'} for p in parts):
        parser.error('Replace repository placeholders with the actual published repository.')
    if not re.fullmatch(r'[A-Fa-f0-9]{40}', args.sha):
        parser.error('Supply the exact 40-character commit SHA.')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', args.maintainer):
        parser.error('Supply the real maintainer handle.')
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(f'''name: salesforce-guard
title: Salesforce Guard
repo: {args.repo}
subdir: hermes-plugin
sha: {args.sha.lower()}
version: "0.4.3"
maintainer: {args.maintainer}
tier: community
category: tools
requires_hermes: ">=0.21.2"
description: >-
  Salesforce release-impact and scoped-access review: explicit-scope snapshot comparison,
  source-reference maps, local access evidence and HTML reports. Bounded security
  heuristics and partial OWASP mappings produce review signals, not org-wide assurance.
  Dedicated review profile blocks unrelated tools while the plugin is enabled.
  Custom native inputs require separate operator folder approval with model-sharing acknowledgement.
  Disclosure: reads user-supplied source directories and writes profile-local reports;
  no native network, credentials or shell. Optional operator CLI invokes installed
  Salesforce CLI for Code Analyzer, explicit browser sign-in, metadata capture, fixed scoped selected-user access queries and logout;
  Salesforce CLI owns credentials. No deploy/Apex execution. Findings require human review;
  not an OS sandbox.
capabilities:
  provides_tools: [sfg_scan, sfg_demo, sfg_report, sfg_policy, sfg_impact, sfg_compare, sfg_compare_demo, sfg_changes, sfg_access]
  provides_hooks: [pre_tool_call]
  provides_middleware: []
  requires_env: []
''', encoding='utf-8')
    print(destination.resolve())


if __name__ == '__main__': main()
