"""A stalled/failed host check must not leave a stale passing receipt."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


class VerificationBoundaryTests(unittest.TestCase):
    def test_timeout_replaces_stale_success_and_reports_incomplete(self):
        script=Path(__file__).resolve().parents[1]/'scripts/verify_hermes.py'
        spec=importlib.util.spec_from_file_location('verify_boundary_harness',script)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);receipt=root/'receipt.json';receipt.write_text('{"success":true}')
            with patch.object(sys,'argv',[str(script),'--plugin',str(root),'--output',str(receipt),'--timeout','5']),patch('salesforce_guard.analyzer._execute',side_effect=subprocess.TimeoutExpired('host',5)) as execute:
                self.assertEqual(module.main(),2)
            result=json.loads(receipt.read_text())
            self.assertEqual(result['completion'],'not_established');self.assertNotIn('success',result)
            self.assertIn('--worker',execute.call_args.args[0])


if __name__=='__main__':unittest.main()
