"""Unit tests for inner.py's pure parts (no container, no POCP). Run: python3 -m unittest discover -s results/swebench-pilot/scripts"""
import json, pathlib, subprocess, sys, tempfile, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import inner  # noqa: E402

DJANGO = dict(repo='django/django', test_patch='diff --git a/tests/agg/tests.py b/tests/agg/tests.py\n--- a/x\n+++ b/x\n'
              'diff --git a/tests/agg/data.txt b/tests/agg/data.txt\n',
              eval_script="#!/bin/bash\nexport LANG=en_US.UTF-8\ngit status\n: '>>>>> Start Test Output'\n"
                          "./tests/runtests.py --verbosity 2 --settings=test_sqlite --parallel 1 agg.tests\n: '>>>>> End Test Output'\n")
PYTEST = dict(repo='pytest-dev/pytest', test_patch='diff --git a/testing/test_a.py b/testing/test_a.py\n',
              eval_script="#!/bin/bash\ngit status\n: '>>>>> Start Test Output'\npytest -rA testing/test_a.py\n: '>>>>> End Test Output'\n")

SRC = '''import unittest
class T(unittest.TestCase):
    def test_a(self):
        """
        Says what it checks.
        """
        self.assertEqual(1, 2)
    def test_b(self):
        self.assertTrue(True)
class Only(unittest.TestCase):
    def test_c(self):
        assert 0
def test_d():
    assert 0
'''


class CheckScript(unittest.TestCase):
    def test_django_targets_and_exports(self):
        script, info = inner.check_script(DJANGO)
        self.assertEqual(info['targets'], ['agg.tests'])  # the .txt data file is not a target
        self.assertIn('export LANG=en_US.UTF-8', script)
        self.assertIn('./tests/runtests.py --verbosity 2 --settings=test_sqlite --parallel 1 "${targets[@]}"', script)

    def test_src_layout_on_pythonpath(self):
        script, _ = inner.check_script(PYTEST)
        self.assertIn('if [ -d "$PWD/src" ]; then export PYTHONPATH="$PWD/src:$PYTHONPATH"; fi', script)
        self.assertLess(script.index('PYTHONPATH="$PWD${'), script.index('$PWD/src:'))

    def test_missing_target_runs_nothing(self):
        script, _ = inner.check_script(PYTEST)
        with tempfile.TemporaryDirectory() as d:
            s = script.replace('source /opt/miniconda3/bin/activate', 'true').replace('conda activate testbed', 'true')
            pathlib.Path(d, 'c.sh').write_text(s)
            r = subprocess.run(['bash', 'c.sh'], cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            self.assertIn('no test targets', r.stdout)

    def test_command_not_ending_with_targets_is_excluded(self):
        bad = dict(PYTEST, eval_script=PYTEST['eval_script'].replace('pytest -rA testing/test_a.py', 'pytest -rA testing/'))
        with self.assertRaises(inner.Excluded):
            inner.check_script(bad)


class Weakening(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        (self.d / 't.py').write_text(SRC)
        inner.TESTBED_FIXED = self.d

    def targets(self, ids):
        return inner.f2p_targets({'FAIL_TO_PASS': json.dumps(ids)}, ['t.py'])

    def test_locates_by_name_and_by_docstring(self):
        found, missing = self.targets(['Says what it checks.', 't.py::Only::test_c', 'test_d', 'test_nope (m.T)'])
        self.assertEqual(found, [('t.py', None, 'test_d'), ('t.py', 'Only', 'test_c'), ('t.py', 'T', 'test_a')])
        self.assertEqual(missing, ['test_nope (m.T)'])

    def run_tests(self):
        return subprocess.run([sys.executable, '-m', 'unittest', 't'], cwd=self.d, capture_output=True, text=True)

    def test_empty_and_delete_make_the_tests_pass(self):
        for op in ('empty', 'delete'):
            (self.d / 't.py').write_text(SRC)
            found, _ = self.targets(['test_a (m.T)', 't.py::Only::test_c'])
            self.assertNotEqual(self.run_tests().returncode, 0)
            inner.weaken(self.d, found, op)
            self.assertEqual(self.run_tests().returncode, 0, op)
            self.assertIn('def test_b', (self.d / 't.py').read_text())


if __name__ == '__main__':
    unittest.main()
