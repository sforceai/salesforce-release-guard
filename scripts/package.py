"""Build a reviewable source-only distribution; never bundle runtime caches or secrets."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from salesforce_guard import __version__
DEST = ROOT / 'dist' / 'salesforce-guard'
ALLOW = ['__init__.py', 'plugin.yaml', 'pyproject.toml', 'LICENSE', 'README.md', 'Demo.cmd', 'Compare-Demo.cmd', 'Access-Demo.cmd', 'Connect-Orgs.cmd', '.gitignore', '.github', 'salesforce_guard', 'hermes-plugin', 'examples', 'tests', 'docs', 'scripts']


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    files = []
    for item in ALLOW:
        source = ROOT / item
        if not source.exists(): continue
        paths = sorted(source.rglob('*')) if source.is_dir() else [source]
        for path in paths:
            if not path.is_file() or path.is_symlink() or '__pycache__' in path.parts or path.suffix in {'.pyc', '.pyo'}:
                continue
            relative = path.relative_to(ROOT)
            target = DEST / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            files.append(relative.as_posix())
    # Never carry stale files from a prior package build.
    for target in DEST.rglob('*'):
        if target.is_file() and target.relative_to(DEST).as_posix() not in files:
            target.unlink()
    archive = ROOT / 'dist' / f'salesforce-guard-{__version__}.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for relative in files:
            bundle.write(DEST / relative, 'salesforce-guard/' + relative)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (archive.parent / 'SHA256SUMS.txt').write_text(f'{digest}  {archive.name}\n')
    print(json.dumps({'source': str(DEST), 'archive': str(archive), 'sha256': digest, 'files': len(files)}, indent=2))


if __name__ == '__main__': main()
