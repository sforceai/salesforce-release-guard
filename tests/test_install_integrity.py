import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from scripts.check_install import check_install


class InstallIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / 'Example.cls'
        self.file.write_bytes(b'fictional fixture\n')
        self.hash = hashlib.sha256(self.file.read_bytes()).hexdigest()

    def ledger(self, entries):
        (self.root / 'BUILD.json').write_text(json.dumps({'source_sha256': entries}), encoding='utf-8')

    def test_complete_then_changed_then_missing(self):
        self.ledger({'Example.cls': self.hash})
        self.assertEqual(check_install(self.root)['state'], 'complete')
        self.file.write_bytes(b'changed')
        self.assertEqual(check_install(self.root)['problems'][0]['state'], 'changed')
        self.file.unlink()
        self.assertEqual(check_install(self.root)['state'], 'incomplete')

    def test_forged_paths_and_hashes_fail_before_declared_reads(self):
        for name in ('../outside', '/outside', 'C:/outside', 'nested\\outside', 'nested//outside'):
            self.ledger({name: self.hash})
            with self.assertRaises(ValueError):
                check_install(self.root)
        self.ledger({'Example.cls': 'not a hash'})
        with self.assertRaises(ValueError):
            check_install(self.root)

    def test_duplicate_and_oversized_inventories_fail_closed(self):
        ledger = self.root / 'BUILD.json'
        ledger.write_text('{"source_sha256":{},"source_sha256":{}}')
        with self.assertRaises(ValueError):
            check_install(self.root)
        ledger.write_bytes(b' ' * (1024 * 1024 + 1))
        with self.assertRaises(ValueError):
            check_install(self.root)
