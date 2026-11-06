"""Read-only, profile-local approval boundary for model-facing file inputs.

The operator owns this policy. Native tools cannot grant or revoke approval.
This is a tool boundary, not protection from a malicious local administrator.
"""
import json
from pathlib import Path
import stat

POLICY_NAME = 'input-approvals.json'
SCHEMA = 'sfg.input-approvals.v1'


def canonical_path(value, *, exists=True):
    if not isinstance(value, (str, Path)) or not str(value):
        raise ValueError('Supply an absolute local input path.')
    path = Path(value)
    if not path.is_absolute():
        raise ValueError('Supply an absolute local input path.')
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            if exists:
                raise ValueError('An input path is missing; check the supplied folder or file.') from None
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Input approval does not permit symbolic links or reparse points.')
    return path.resolve(strict=exists)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Input approval policy has duplicate keys.')
        result[key] = value
    return result


def read_roots(policy_file):
    path = canonical_path(policy_file, exists=False)
    if not path.exists():
        return []
    if not path.is_file() or path.stat().st_size > 65536:
        raise ValueError('Invalid or oversized input approval policy.')
    try:
        with path.open('rb') as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError('Oversized input approval policy.')
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique)
    except (OSError, UnicodeError, RecursionError, json.JSONDecodeError):
        raise ValueError('Input approval policy is unreadable or malformed.') from None
    if (not isinstance(data, dict) or data.get('schema') != SCHEMA
            or data.get('model_sharing_approved') is not True
            or not isinstance(data.get('roots'), list) or len(data['roots']) > 64):
        raise ValueError('Input approval policy is invalid; an operator must renew it.')
    roots = [canonical_path(value, exists=False) for value in data['roots']]
    if any((root.exists() and not root.is_dir()) or root == Path(root.anchor) for root in roots):
        raise ValueError('Approval roots must be project folders, not files or filesystem roots.')
    return roots


def authorize_inputs(data_dir, values, bundled_roots=()):
    paths = [canonical_path(value) for value in values]
    trusted = [canonical_path(root) for root in bundled_roots]
    reports = canonical_path(Path(data_dir) / 'reports', exists=False)
    trusted.append(reports)
    external = [path for path in paths if not any(path.is_relative_to(root) for root in trusted)]
    if external:
        roots = read_roots(Path(data_dir) / POLICY_NAME)
        if any(not any(path.is_relative_to(root) for root in roots) for path in external):
            raise ValueError('Input not approved. Ask the operator to approve its project folder with the separate inputs command and acknowledge model sharing. sfg_policy shows the policy-file location. The agent cannot grant approval.')
    return paths


def approval_status(data_dir):
    path = Path(data_dir) / POLICY_NAME
    try:
        roots = read_roots(path)
        return {'state': 'approved' if roots else 'demo_only', 'approved_root_count': len(roots),
                'policy_file': str(path), 'agent_can_grant_approval': False,
                'model_sharing': 'Requested source excerpts and evidence are sent through the selected Hermes model.'}
    except (OSError, ValueError):
        return {'state': 'invalid_policy', 'policy_file': str(path), 'agent_can_grant_approval': False}
