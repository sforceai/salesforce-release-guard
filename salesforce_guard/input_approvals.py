"""Explicit operator-only approval updates; excluded from the native bundle."""
import json
import os
from pathlib import Path
import tempfile
from contextlib import contextmanager
from .input_boundary import canonical_path, read_roots, POLICY_NAME, SCHEMA


@contextmanager
def _lock(policy):
    lock = policy.parent / '.input-approvals.lock'
    try:
        handle = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('Input approvals are busy; retry after the other operator action finishes.') from None
    try:
        yield
    finally:
        os.close(handle)
        lock.unlink()


def update_approval(policy_file, root, *, approve, model_sharing=False):
    if approve and model_sharing is not True:
        raise ValueError('Approval requires --allow-model-sharing: requested excerpts/evidence go to the selected Hermes model.')
    policy = canonical_path(policy_file, exists=False)
    if policy.name != POLICY_NAME:
        raise ValueError('Use the input-approvals.json location returned by sfg_policy.')
    folder = canonical_path(root, exists=approve)
    if (approve and not folder.is_dir()) or folder == Path(folder.anchor):
        raise ValueError('Select a project folder, not a file or filesystem root.')
    policy.parent.mkdir(parents=True, exist_ok=True)
    canonical_path(policy.parent)
    with _lock(policy):
        roots = set(read_roots(policy))
        if approve:
            roots.add(folder)
        else:
            roots.discard(folder)
        if len(roots) > 64:
            raise ValueError('At most 64 project folders may be approved.')
        data = {'schema': SCHEMA, 'model_sharing_approved': True, 'roots': sorted(map(str, roots))}
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=policy.parent,
                                             prefix='.input-approvals-', delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(data, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, policy)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
    return {'action': 'approved' if approve else 'revoked', 'approved_root_count': len(roots),
            'policy_file': str(policy), 'notice': 'Native input approval only. No org permissions or OS isolation are changed.'}
