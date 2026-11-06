"""Build the native plugin separately from operator utilities and adversarial tests.

The generated directory is committed so Hermes can install its Git subdirectory.
Every included file is an unchanged copy of the reviewed source. Nothing is
rewritten to suppress scanner findings. Run --check in CI to detect drift.
"""
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'hermes-plugin'
MODULES = (
    '__init__.py', 'access.py', 'access_demo.py', 'compare.py',
    'comparison_view.py', 'impact.py', 'impact_view.py', 'lexer.py',
    'policy.py', 'report.py', 'rules.py', 'scan.py', 'snapshot.py', 'visuals.py',
    'input_boundary.py', 'review_scope.py',
)


def expected():
    paths = [ROOT / name for name in ('__init__.py', 'plugin.yaml', 'LICENSE')]
    paths += [ROOT / 'salesforce_guard' / name for name in MODULES]
    for fixture in ('risky-project', 'release-demo'):
        paths += sorted(p for p in (ROOT / 'examples' / fixture).rglob('*') if p.is_file())
    return {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in paths
            if not p.is_symlink() and '__pycache__' not in p.parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    files = expected()
    files['BUILD.json'] = (json.dumps({
        'description': 'Byte-identical native runtime and fictional demo inputs; built by scripts/build_plugin.py.',
        'source_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        'excluded': 'Development tests, documentation, browser/video checks and operator-only Salesforce CLI utilities remain in the repository root; they are not native plugin capabilities.',
    }, indent=2) + '\n').encode()
    actual = {p.relative_to(DEST).as_posix(): p.read_bytes() for p in DEST.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc', '.pyo'}}
    if args.check:
        if actual != files:
            raise SystemExit('Native plugin bundle differs from source; run python scripts/build_plugin.py')
    else:
        DEST.mkdir(exist_ok=True)
        for name in actual.keys() - files.keys():
            (DEST / name).unlink()
        for name, data in files.items():
            target = DEST / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    print(json.dumps({'directory': str(DEST), 'files': len(files), 'source_parity': True}))


if __name__ == '__main__':
    main()
