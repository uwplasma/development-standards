import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from check import review


class PolicyTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.addCleanup(os.chdir, Path.cwd())
        os.chdir(work.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Contributor')
        self.git('config', 'user.email', 'person@example.org')
        self.base = self.commit('README.md', 'Example\n')

    def git(self, *args):
        return subprocess.check_output(['git', *args], text=True).strip()

    def commit(self, path, text, message='Update example'):
        path = Path(path)
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text(text)
        self.git('add', '--', str(path))
        self.git('commit', '-qm', message)
        return self.git('rev-parse', 'HEAD')

    def test_valid_example_and_cli(self):
        self.commit('examples/solve.py', 'N = 8\nprint(N)\n')
        self.commit('src/cli.py', 'def main(): pass\n')
        self.assertEqual(review(self.base, 'HEAD'), [])

    def test_equilibrium_removed_before_review(self):
        self.commit('case.txt', '&INDATA\n/\n')
        self.commit('case.txt', 'Load the local fixture by identifier.\n')
        self.assertEqual(review(self.base, 'HEAD')[0][:2], ('FAIL', 'case.txt'))

    def test_example_and_reference_table(self):
        self.commit('examples/solve.py', 'from argparse import ArgumentParser as AP\np = AP()\n')
        self.commit('tests/reference.csv', 'x,y\n')
        self.assertEqual([x[:2] for x in review(self.base, 'HEAD')],
                         [('FAIL', 'examples/solve.py'), ('REVIEW', 'tests/reference.csv')])

    def test_stacked_target_and_authorship(self):
        target = self.commit('old.ipynb', '{}')
        self.commit('README.md', 'Read this.\n')
        event = {'pull_request': {'user': {'type': 'User'}, 'body': 'Review the CUDA documentation.'}}
        self.assertEqual(review(target, 'HEAD', event), [])
        event['pull_request']['user']['type'] = 'Bot'
        self.assertEqual(review(target, 'HEAD', event)[0][:2], ('FAIL', 'PR author'))

    def test_archive_pointer_notebook_and_trailer(self):
        self.commit('case.dat', 'version https://git-lfs.github.com/spec/v1\n')
        self.commit('files.zip', 'archive payload')
        self.commit('simulation.ipynb', '{}', 'Change\n\nCo-authored-by: Claude <example@example.org>')
        failures = review(self.base, 'HEAD')
        self.assertEqual(len(failures), 4)
        self.assertTrue(all(s == 'FAIL' for s, _, _ in failures))

    def test_large_blob_and_small_deletion(self):
        previous = self.commit('large.dat', '0' * (5*1024*1024 + 1))
        self.assertEqual(review(self.base, previous)[0][:2], ('FAIL','large.dat'))
        self.git('rm','large.dat')
        self.git('commit','-qm','Remove artifact')
        self.assertEqual(review(previous, 'HEAD'), [])
