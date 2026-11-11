"""Run from the repository root: python3 examples/demo.py (synthetic only)."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from harp.cli import main

def run(root,*args):
 out=io.StringIO()
 with contextlib.redirect_stdout(out):
  code=main(['--root',str(root),*args])
 if code: raise RuntimeError(args)
 return json.loads(out.getvalue())

def review(root,item):
 run(root,'review',item,'--verdict','accept','--reviewer','Synthetic demo researcher','--reason','Demonstration only','--confirm')

with tempfile.TemporaryDirectory() as directory:
 root=Path(directory)
 for args in [('init',),('config','user.name','Demo'),('config','user.email','demo@example.invalid')]:
  subprocess.run(['git','-C',directory,*args],check=True,capture_output=True)
 (root/'results.csv').write_text('group,before,after\ntreated,10,14\ncontrol,10,12\n')
 subprocess.run(['git','-C',directory,'add','results.csv'],check=True)
 subprocess.run(['git','-C',directory,'commit','-m','Synthetic baseline'],check=True,capture_output=True)
 run(root,'init','--mode','existing')
 goal=run(root,'propose','goals','Estimate treatment effect','--source','Synthetic interview','--visibility','shareable')['id']; review(root,goal)
 evidence=run(root,'propose','evidence','Synthetic 2x2 table','--source','results.csv')['id']; review(root,evidence)
 finding=run(root,'propose','findings','Toy DID is +2; no identification established','--source','Synthetic calculation','--evidence',evidence,'--validation','preliminary','--visibility','shareable')['id']; review(root,finding)
 new=run(root,'propose','goals','Estimate effect with uncertainty','--source','Synthetic review','--supersedes',goal)['id']
 assert run(root,'diff',new)['before']=='Estimate treatment effect'
 review(root,new)
 session=run(root,'session','--provider','demo','--model','unknown','--summary','Synthetic planning only')['id']
 capture=run(root,'capture','--session',session,'--items',finding)['id']; review(root,capture)
 assert not run(root,'check')['flags']
 assert len(run(root,'resume')['active'])==3
 target=root/'.ai-research'/'disclosure.md'
 run(root,'export','--include-shareable','--output',str(target))
 print(target.read_text())
