import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from harp.cli import main, Store, view, active

class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)
 def runcli(self,*args,ok=True):
  out=io.StringIO(); err=io.StringIO()
  with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
   code=main(['--root',str(self.root),*args])
  self.assertEqual(code,0 if ok else 2,err.getvalue())
  return json.loads(out.getvalue()) if code==0 else err.getvalue()
 def init(self,mode='new'): self.runcli('init','--mode',mode)
 def propose(self,kind='goals',text='Test result',*args):
  return self.runcli('propose',kind,text,'--source','synthetic',*args)['id']
 def accept(self,i):
  self.runcli('review',i,'--verdict','accept','--reviewer','Researcher','--reason','Inspected exact record','--confirm')
 def git(self,*args):
  return subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True).stdout
 def test_modes_and_no_overwrite(self):
  self.init('existing'); self.runcli('init',ok=False)
  self.assertEqual(self.runcli('resume')['active'],[])
  self.assertIn('.ai-research/',(self.root/'.gitignore').read_text())
 def test_review_drift_diff_and_resume(self):
  self.init(); old=self.propose(); self.accept(old)
  new=self.propose('goals','Changed goal','--supersedes',old)
  self.assertEqual(self.runcli('diff',new)['before'],'Test result')
  self.assertIn('proposed_drift',[x['type'] for x in self.runcli('check')['flags']])
  self.assertEqual(self.runcli('resume')['active'][0]['id'],old)
  self.accept(new)
  self.assertEqual(self.runcli('resume')['active'][0]['id'],new)
  self.runcli('propose','goals','Stale','--source','x','--supersedes',old,ok=False)
 def test_human_confirmation_and_validation_are_separate(self):
  self.init(); i=self.propose('priors')
  self.runcli('review',i,'--verdict','accept','--reviewer','R','--reason','yes',ok=False)
  self.accept(i)
  self.assertEqual(self.runcli('resume')['active'][0]['validation'],'unverified')
  self.runcli('propose','findings','Unsupported','--source','x','--validation','verified',ok=False)
  e=self.propose('evidence','Synthetic table'); self.accept(e)
  f=self.propose('findings','Positive effect','--evidence',e,'--validation','verified'); self.accept(f)
  self.runcli('review',e,'--verdict','reject','--reviewer','R','--reason','Evidence invalid','--confirm')
  self.assertIn('unsupported_finding',[x['type'] for x in self.runcli('check')['flags']])
 def test_git_session_capture_and_changes(self):
  self.git('init'); self.git('config','user.name','Test'); self.git('config','user.email','test@example.invalid')
  (self.root/'paper.txt').write_text('First')
  self.git('add','paper.txt'); self.git('commit','-m','Initial')
  self.init()
  s=self.runcli('session','--provider','manual','--model','unknown','--summary','Synthetic change')['id']
  c=self.runcli('capture','--session',s)['id']; self.accept(c)
  self.assertEqual(self.runcli('check')['flags'],[])
  (self.root/'paper.txt').write_text('Second')
  self.assertIn('git_drift',[x['type'] for x in self.runcli('check')['flags']])
  self.runcli('capture','--session','missing',ok=False)
 def test_private_export_and_no_overwrite(self):
  self.init(); self.propose('goals','SECRET_PRIVATE')
  self.propose('consensus','SAFE_SHAREABLE','--visibility','shareable')
  target=self.root/'report.md'
  self.runcli('export','--output',str(target))
  self.assertNotIn('SECRET_PRIVATE',target.read_text()); self.assertNotIn('SAFE_SHAREABLE',target.read_text())
  self.runcli('export','--output',str(target),ok=False)
  target2=self.root/'share.md'; self.runcli('export','--include-shareable','--output',str(target2))
  self.assertNotIn('SECRET_PRIVATE',target2.read_text()); self.assertIn('SAFE_SHAREABLE',target2.read_text())
 def test_tamper_detected(self):
  self.init(); self.propose()
  store=Store(self.root); data=json.loads(store.path.read_text()); data['events'][0]['payload']['text']='tampered'
  store.path.write_text(json.dumps(data)); self.runcli('resume',ok=False)
 def test_adaptive_interview(self):
  self.init(); i=self.propose('goals','Goal already supplied'); self.accept(i)
  self.assertNotIn('goals',[q.get('kind') for q in self.runcli('questions')])
  with patch('builtins.input',side_effect=['Agreed definitions','yes','Human','','','','','','']):
   self.runcli('interview')
  self.assertEqual(len(self.runcli('resume')['active']),2)
 def test_invalid_evidence_and_non_git(self):
  self.init(); self.runcli('propose','findings','x','--source','x','--evidence','bad',ok=False)
  s=self.runcli('session','--provider','x','--model','x','--summary','x')['id']
  self.runcli('capture','--session',s,ok=False)

 def test_rejected_findings_do_not_block_current_state(self):
  self.init(); finding=self.propose('findings','Unsupported')
  self.runcli('review',finding,'--verdict','reject','--reviewer','R','--reason','Unsupported','--confirm')
  self.assertEqual(self.runcli('check')['flags'],[])
 def test_replacement_chain_and_stale_parallel_proposal(self):
  self.init(); first=self.propose(); self.accept(first)
  second=self.propose('goals','Second','--supersedes',first)
  stale=self.propose('goals','Parallel','--supersedes',first)
  self.accept(second)
  self.runcli('review',stale,'--verdict','accept','--reviewer','R','--reason','Stale','--confirm',ok=False)
  self.runcli('review',stale,'--verdict','reject','--reviewer','R','--reason','Stale','--confirm')
  third=self.propose('goals','Third','--supersedes',second); self.accept(third)
  self.assertEqual(self.runcli('check')['flags'],[])
  self.assertEqual(self.runcli('resume')['active'][0]['id'],third)
 def test_superseded_evidence_cannot_verify_new_finding(self):
  self.init(); old=self.propose('evidence'); self.accept(old)
  new=self.propose('evidence','Corrected evidence','--supersedes',old); self.accept(new)
  self.runcli('propose','findings','Outdated','--source','test','--evidence',old,'--validation','verified',ok=False)
 def test_unborn_git_and_imported_session(self):
  self.git('init'); self.init('existing')
  session=self.runcli('session','--provider','unknown','--model','unknown','--summary','Historical metadata','--origin','imported')['id']
  capture=self.runcli('capture','--session',session)['id']
  self.assertIsNone(self.runcli('status')['captures'][capture]['git']['head'])
  self.assertEqual(self.runcli('status')['sessions'][session]['origin'],'imported')

if __name__=='__main__': unittest.main()
