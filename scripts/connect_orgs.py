"""Operator-only connection wizard. Never request or accept a password/token."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from salesforce_guard.orgs import OrgBridge,CliTransport,cli_command

def main():
    print('Connect source and destination through Salesforce CLI browser sign-in.')
    print('Do not paste passwords, access tokens, refresh tokens or client secrets here.')
    bridge=OrgBridge(ROOT/'.sfg-connections',CliTransport(cli_command()))
    for role in ('source','destination'):
        print('\n'+role.upper()+' ORG')
        url=input('Salesforce login/My Domain URL: ').strip()
        expected=input('Expected org ID from Setup > Company Information: ').strip()
        client=input('Public OAuth client ID (Enter for Salesforce CLI default): ').strip() or None
        print('Complete the Salesforce sign-in and any approval in your browser.')
        result=bridge.login(role,url,expected,client)
        print('Verified',role,'org:',result['org_id'])
    print('\nBoth role bindings saved. No deployment capability is exposed by this bridge.')
    print('Use the capture command described in docs/CONNECTIONS.md to retrieve scoped snapshots.')

if __name__=='__main__':
    try:main()
    except (OSError,ValueError) as exc:print('Connection not completed:',exc);raise SystemExit(2)
