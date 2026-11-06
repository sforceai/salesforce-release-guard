"""One-click local demonstration; no installation or credentials."""
from pathlib import Path
import sys
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from salesforce_guard.scan import scan_project
from salesforce_guard.report import save_report

if __name__ == '__main__':
    report = scan_project(ROOT / 'examples/risky-project')
    destination = save_report(report, ROOT / 'output')
    print(f"Completed local demonstration: {report['summary']['findings']} observations requiring review.")
    print(destination / 'report.html')
    webbrowser.open((destination / 'report.html').as_uri())
