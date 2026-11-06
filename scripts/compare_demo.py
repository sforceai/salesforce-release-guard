"""One-click fictional comparison. No authentication, network or deployment."""
from pathlib import Path
import sys
import webbrowser
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from salesforce_guard.compare import compare_snapshots
from salesforce_guard.comparison_view import save_comparison

if __name__=='__main__':
    base=ROOT/'examples/release-demo'
    result=compare_snapshots(base/'candidate',base/'destination',base/'package.xml',delete_post=base/'destructiveChangesPost.xml')
    out=save_comparison(result,ROOT/'output')
    print('Fictional comparison completed:',result['summary'])
    webbrowser.open((out/'comparison.html').as_uri())
