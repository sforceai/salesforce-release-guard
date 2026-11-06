"""Open an original fictional access report, no live org access."""
from pathlib import Path
import json
import sys
import uuid
import webbrowser

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from salesforce_guard.access_demo import demo_evidence
from salesforce_guard.access import load_evidence,save_access

if __name__=='__main__':
    folder=ROOT/'output'/uuid.uuid4().hex;folder.mkdir(parents=True,exist_ok=False)
    evidence=folder/'fictional-access-evidence.json';evidence.write_text(json.dumps(demo_evidence()),encoding='utf-8')
    dest=save_access(load_evidence(evidence),ROOT/'output')
    print('Opening fictional access evidence. No Salesforce connection used.')
    webbrowser.open((dest/'access.html').resolve().as_uri())
