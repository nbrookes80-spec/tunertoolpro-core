"""Every shared module imports on its own, in a fresh interpreter, whatever the import order. A cycle that only works
when another module happened to be imported first breaks the first app that imports in a different order."""

import pkgutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ('tunertoolpro.scanner', 'tunertoolpro.link')
SINGLES = ('tunertoolpro.live', 'tunertoolpro.grading', 'tunertoolpro.prefs', 'tunertoolpro.recorder')


def modules():
    found = list(SINGLES)
    for name in PACKAGES:
        package = __import__(name, fromlist=['x'])
        found.append(name)
        found += [f'{name}.{m.name}' for m in pkgutil.iter_modules(package.__path__)]
    return sorted(found)


class ImportOrderTests(unittest.TestCase):
    def test_each_module_imports_first(self):
        for name in modules():
            with self.subTest(module=name):
                run = subprocess.run([sys.executable, '-c', f'import {name}'], cwd=ROOT,
                                     capture_output=True, text=True, env={'PYTHONPATH': str(ROOT)})
                self.assertEqual(run.returncode, 0, run.stderr[-400:])


if __name__ == '__main__':
    unittest.main()
