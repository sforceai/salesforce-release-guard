"""Optional operator-run Code Analyzer integration. Never runs from an agent tool.

Only a preinstalled CLI is invoked, with fixed arguments on a staged source snapshot.
Project-provided configuration and suppressions are not copied or executed.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile

from .scan import inventory, MAX_FILE


CONFIG = '''engines:
  pmd:
    disable_engine: false
  cpd:
    disable_engine: true
  sfge:
    disable_engine: true
  eslint:
    disable_engine: true
  retire-js:
    disable_engine: true
  regex:
    disable_engine: true
  flow:
    disable_engine: true
'''


def _execute(args, cwd, env, stdout, stderr, timeout):
    """Bound the whole scanner process tree, including Java/CLI child processes."""
    process = subprocess.Popen(args, cwd=cwd, env=env, shell=False, stdin=subprocess.DEVNULL,
        stdout=stdout, stderr=stderr, start_new_session=os.name != 'nt',
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        else:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)
        raise


def parse_output(data):
    if not isinstance(data, dict) or not isinstance(data.get('violations'), list) or not isinstance(data.get('versions'), dict):
        raise ValueError('Unsupported Salesforce Code Analyzer JSON schema')
    if len(data['violations']) > 20000:
        raise ValueError('External findings limit exceeded')
    results = []
    for entry in data['violations']:
        if not isinstance(entry, dict) or not isinstance(entry.get('rule'), str):
            raise ValueError('Malformed Code Analyzer violation')
        if type(entry.get('severity')) is not int or entry['severity'] not in range(1, 6):
            raise ValueError('Invalid Code Analyzer severity')
        # Preserve raw findings separately; no claim that an engine finding is a confirmed defect.
        results.append({key: entry.get(key) for key in ('rule', 'engine', 'severity', 'message', 'locations', 'tags')})
    return {'versions': data['versions'], 'findings': results, 'raw_count': len(data['violations']),
            'confirmed_vulnerabilities': 0, 'disposition': 'requires_review'}


def run_analyzer(root, output, command=None, timeout=180):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    receipt = {'status': 'failed', 'started_at': datetime.now(timezone.utc).isoformat(),
               'scope': 'PMD security rules on staged Apex snapshot; not all Code Analyzer engines',
               'completion': 'not_established', 'findings': []}
    command = command or [shutil.which('sf') or 'sf']
    if not command or any(not isinstance(p, str) or not p for p in command):
        raise ValueError('Invalid CLI command')
    if os.name == 'nt' and Path(command[0]).suffix.lower() in {'.cmd', '.bat', '.ps1'}:
        receipt.update(status='unavailable', reason='On Windows supply --node and --sf-js for the installed CLI; shell wrappers are not executed.')
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        return receipt
    root, files, issues = inventory(root)
    if issues or not any(p.endswith(('.cls', '.trigger')) for p in files):
        receipt.update(reason='Cannot stage an incomplete or empty Apex inventory', inventory_issues=issues)
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        return receipt
    # Never propagate org tokens, plugin-loader settings or NODE_OPTIONS from the parent.
    allowed = {'PATH', 'PATHEXT', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'JAVA_HOME', 'USERPROFILE', 'HOME', 'APPDATA', 'LOCALAPPDATA', 'SF_DATA_DIR', 'SF_CACHE_DIR', 'SF_CONFIG_DIR'}
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    env.update(SF_DISABLE_TELEMETRY='true', SF_AUTOUPDATE_DISABLE='true', SF_SKIP_NEW_VERSION_CHECK='true',
               SF_LOG_LEVEL='error', SF_LOG_STDERR='true', DEBUG='salesforce-guard', CI='true')
    # Discover first: JIT-only entries must never trigger automatic installation.
    try:
        preflight = output / 'installed-plugins.json'
        with preflight.open('wb') as stdout, (output / 'preflight.stderr.log').open('wb') as stderr:
            exit_code = _execute([*command, 'plugins', '--json'], output, env, stdout, stderr, min(timeout, 30))
        if preflight.stat().st_size > 16 * 1024 * 1024:
            raise ValueError('CLI plugin inventory exceeds limit')
        installed = json.loads(preflight.read_text(encoding='utf-8-sig'))
        if exit_code or not isinstance(installed, list):
            raise ValueError('Cannot establish installed scanner availability')
        scanner_plugins = [p for p in installed if isinstance(p, dict) and p.get('name') == '@salesforce/plugin-code-analyzer' and p.get('type') != 'jit' and p.get('root')]
        ready = bool(scanner_plugins)
        if not ready:
            receipt.update(status='unavailable', reason='Salesforce Code Analyzer is not installed. Provision the official scanner separately; no JIT installation was started.')
            (output / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
            return receipt
        receipt['cli_plugin_version'] = scanner_plugins[0].get('version', 'unknown')
    except subprocess.TimeoutExpired:
        receipt.update(status='timeout', reason='Installed-scanner discovery timed out; no scan or JIT installation was started.')
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        return receipt
    except (OSError, ValueError) as exc:
        receipt.update(reason=str(exc))
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        return receipt
    with tempfile.TemporaryDirectory(prefix='sfg-analyzer-', ignore_cleanup_errors=True) as temporary:
        stage = Path(temporary)
        for relative, (text, digest) in files.items():
            path = stage / 'source' / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with (root / relative).open('rb') as stream:
                original_bytes = stream.read(MAX_FILE + 1)
            if hashlib.sha256(original_bytes).hexdigest() != digest:
                receipt.update(status='source_changed', reason='Source changed while staging; no external scan was started.')
                (output / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
                return receipt
            path.write_bytes(original_bytes)
        (stage / 'code-analyzer.yml').write_text(CONFIG, encoding='utf-8')
        args = [*command, 'code-analyzer', 'run', '--workspace', str(stage / 'source'),
                '--rule-selector', 'pmd:Security', '--no-suppressions', '--config-file', str(stage / 'code-analyzer.yml'),
                '--output-file', str(output / 'code-analyzer.json')]
        receipt['command'] = args
        receipt['source_hashes'] = {p: digest for p, (_, digest) in files.items()}
        try:
            with (output / 'stdout.log').open('wb') as stdout, (output / 'stderr.log').open('wb') as stderr:
                exit_code = _execute(args, stage, env, stdout, stderr, timeout)
            receipt['exit_code'] = exit_code
            raw = output / 'code-analyzer.json'
            if not raw.exists() or raw.stat().st_size > 16 * 1024 * 1024:
                raise ValueError('Missing or oversized Code Analyzer JSON output')
            parsed = parse_output(json.loads(raw.read_text(encoding='utf-8-sig')))
            receipt.update(parsed)
            receipt['raw_sha256'] = hashlib.sha256(raw.read_bytes()).hexdigest()
            logs = '\n'.join((output / n).read_text(encoding='utf-8', errors='replace')[:2000000] for n in ('stdout.log', 'stderr.log'))
            receipt['engine_log_status'] = 'not_found'
            for log_name in re.findall(r'[^\r\n]*sfca-[^\r\n]*\.log', logs):
                log_path = Path(log_name.strip())
                if log_path.is_file() and not log_path.is_symlink() and log_path.resolve().parent == Path(tempfile.gettempdir()).resolve() and log_path.stat().st_size <= 8 * 1024 * 1024:
                    shutil.copyfile(log_path, output / 'engine.log')
                    logs += '\n' + log_path.read_text(encoding='utf-8', errors='replace')
                    receipt['engine_log_status'] = 'preserved'
                    break
            engine_error = any(term.lower() in logs.lower() for term in ('InternalExecutionError', 'LimitReached', 'engine error', 'failed to run', 'No rule matches'))
            receipt['status'] = 'process_completed_requires_review' if exit_code == 0 and not engine_error else 'incomplete'
            receipt['completion'] = 'process_only_engine_coverage_not_proven'
            receipt['reason'] = 'Inspect raw engine output and logs. Exit zero does not prove every path completed.'
        except subprocess.TimeoutExpired:
            receipt.update(status='timeout', reason='Code Analyzer exceeded the operator time limit; no complete scan claimed.')
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            receipt.update(reason=str(exc))
    receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
    if Path(temporary).exists():
        receipt['cleanup_warning'] = 'Temporary staged source could not be removed; remove it after scanner children exit.'
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return receipt
