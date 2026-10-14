"""Benign process-level controls for assertion-dependent scientific entries."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
ENTRIES = ('test_supporter_equivalence', 'test_update_bridge', 'test_update_contract')


class AssertionGateTests(unittest.TestCase):
    def child(self, entry, code, optimized=False):
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
        command = [sys.executable, '-B'] + (['-O'] if optimized else [])
        command += ['-c', 'import ' + entry + ' as m; ' + code]
        return subprocess.run(command, cwd=HERE, env=environment, capture_output=True,
                              text=True, encoding='utf-8', timeout=20)

    def test_normal_entries_keep_semantic_checks(self):
        for entry in ENTRIES:
            with self.subTest(entry=entry):
                result = self.child(entry, 'import json; print(json.dumps(m.run()["passed"]))')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIs(json.loads(result.stdout), True)

    def test_optimized_entries_refuse_before_fixtures(self):
        for entry in ENTRIES:
            with self.subTest(entry=entry):
                result = self.child(entry, 'm.fixtures=lambda: (_ for _ in ()).throw('
                                    'AssertionError("fixture evaluated")); m.run()', True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('scientific comparisons require assertions', result.stderr)
                self.assertNotIn('fixture evaluated', result.stderr)
                self.assertEqual(result.stdout, '')

    def test_corrupt_supporter_cannot_emit_pass_in_either_mode(self):
        for optimized in (False, True):
            with self.subTest(optimized=optimized):
                result = self.child('test_supporter_equivalence',
                                    'm.witnesses=lambda *a, **k: []; m.run()', optimized)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')
                self.assertIn('RuntimeError' if optimized else 'AssertionError', result.stderr)

    def test_anchor_work_bound_is_unconditional(self):
        for optimized in (False, True):
            with self.subTest(optimized=optimized):
                result = self.child('test_supporter_equivalence',
                                    'm.witnesses({"options": list(range(13))}, 0)', optimized)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('twelve-option bound', result.stderr)


if __name__ == '__main__':
    unittest.main()
