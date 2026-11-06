"""Read-only declared-file integrity check; no Hermes, model, credentials or network."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate inventory key')
        result[key] = value
    return result


def _linked(path):
    info = path.lstat()
    return path.is_symlink() or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def check_install(directory):
    root = Path(directory).absolute()
    if any(_linked(p) for p in (root, *root.parents)):
        raise ValueError('Installation path traverses a link or reparse point')
    ledger = root / 'BUILD.json'
    if _linked(ledger):
        raise ValueError('Inventory is linked')
    with ledger.open('rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Inventory exceeds size limit')
    data = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique)
    files = data.get('source_sha256') if isinstance(data, dict) else None
    if not isinstance(files, dict) or not 1 <= len(files) <= 256:
        raise ValueError('Invalid declared-file inventory')
    # Validate every entry before reading any declared file.
    for name, digest in files.items():
        if (not isinstance(name, str) or not name or '\\' in name or ':' in name
                or PurePosixPath(name).is_absolute()
                or any(part in ('', '.', '..') for part in name.split('/'))
                or not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest)):
            raise ValueError('Unsafe path or invalid hash in inventory')
    problems = []
    total = 0
    for name, digest in files.items():
        path = root / name
        try:
            if any(_linked(p) for p in (path, *path.parents) if p.is_relative_to(root)):
                raise ValueError('Linked declared input')
            with path.open('rb') as stream:
                content = stream.read(4 * 1024 * 1024 + 1)
            total += len(content)
            if len(content) > 4 * 1024 * 1024 or total > 64 * 1024 * 1024:
                raise ValueError('Declared input exceeds size limit')
            if hashlib.sha256(content).hexdigest() != digest:
                problems.append({'file': name, 'state': 'changed'})
        except (OSError, ValueError):
            problems.append({'file': name, 'state': 'missing_or_unreadable'})
    return {'state': 'complete' if not problems else 'incomplete',
            'declared_files': len(files), 'problems': problems,
            'notice': 'Checks declared file bytes only. This is not a source-authenticity or security certification. Use a shorter Windows installation path if inputs are unreadable.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('installation', help='Installed salesforce-guard plugin folder')
    args = parser.parse_args()
    try:
        result = check_install(args.installation)
    except (OSError, ValueError, RecursionError) as exc:
        result = {'state': 'incomplete', 'error': str(exc)}
    print(json.dumps(result, indent=2))
    return 0 if result['state'] == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
