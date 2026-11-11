import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('package_plugin',ROOT/'scripts/package_plugin.py')
package=importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)

class PackagingTests(unittest.TestCase):
 def test_distribution_paths_and_archive(self):
  with tempfile.TemporaryDirectory() as tmp:
   output=package.build(Path(tmp)/'plugin.zip')
   with zipfile.ZipFile(output) as archive:
    names=archive.namelist()
    self.assertEqual(len(names),8)
    self.assertFalse(any('.ai-research/' in n or 'marketplace.json' in n or '__pycache__' in n for n in names))
    archive.extractall(tmp)
   skill=Path(tmp)/'human-ai-research-alignment/skills/human-ai-research-alignment'
   result=subprocess.run([sys.executable,'-m','harp','--help'],cwd=skill,capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr)
   self.assertIn('resume',result.stdout)

if __name__=='__main__': unittest.main()
