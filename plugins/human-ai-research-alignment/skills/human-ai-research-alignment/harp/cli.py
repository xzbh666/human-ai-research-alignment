"""No network, model API, hooks, or background collection. Python 3.9+."""
import argparse
import hashlib
import difflib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

KINDS = ('goals', 'consensus', 'priors', 'hypotheses', 'evidence', 'findings', 'open_questions', 'decisions')
QUESTIONS = {
 'goals': 'What outcome and success criterion should this research pursue?',
 'consensus': 'Which definitions, scope and constraints do you want to agree on?',
 'priors': 'What do you expect before examining the evidence, and why?',
 'hypotheses': 'What falsifiable claim and disconfirming observation should we test?',
 'evidence': 'What source or result can be inspected? Include an explicit reference.',
 'findings': 'What result is currently supported, and which evidence IDs support it?',
 'open_questions': 'Which uncertainty or disagreement matters for the next step?',
 'decisions': 'What choice was made, why, and which alternatives were considered?'}

def stamp():
 return datetime.now(timezone.utc).isoformat()

def digest(value):
 return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def git(root, *args, optional=False):
 p = subprocess.run(['git', '-C', str(root), *args], capture_output=True, check=False)
 if p.returncode:
  if optional: return None
  raise ValueError('Git operation failed: ' + p.stderr.decode(errors='replace').strip())
 return p.stdout

def snapshot(root):
 # No remote URLs, author emails, diff text, or untracked file contents.
 head = git(root, 'rev-parse', '--verify', 'HEAD', optional=True)
 if git(root, 'rev-parse', '--show-toplevel', optional=True) is None:
  return {'available': False}
 status = git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=normal')
 diff = git(root, 'diff', '--binary', 'HEAD') if head else git(root, 'diff', '--cached', '--binary')
 return {'available': True, 'head': head.decode().strip() if head else None,
         'status_sha256': hashlib.sha256(status).hexdigest(),
         'diff_sha256': hashlib.sha256(diff or b'').hexdigest(),
         'coverage': 'tracked diff hash + status hash; untracked contents excluded'}

class Store:
 def __init__(self, root):
  self.root = Path(root).resolve()
  self.directory = self.root / '.ai-research'
  self.path = self.directory / 'ledger.json'
 def load(self):
  data = json.loads(self.path.read_text())
  if data.get('schema_version') != 1: raise ValueError('Unsupported schema version')
  previous = None
  for event in data['events']:
   body = {k:v for k,v in event.items() if k != 'hash'}
   if body['previous'] != previous or digest(body) != event['hash']:
    raise ValueError('Ledger integrity check failed')
   previous = event['hash']
  return data
 def save(self, data):
  self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
  fd, tmp = tempfile.mkstemp(dir=self.directory)
  try:
   with os.fdopen(fd, 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write('\n')
    f.flush()
    os.fsync(f.fileno())
   os.replace(tmp, self.path)
  finally:
   if os.path.exists(tmp): os.unlink(tmp)
 def append(self, data, action, payload):
  body = {'id':uuid4().hex[:12], 'at':stamp(), 'action':action, 'payload':payload,
          'previous':data['events'][-1]['hash'] if data['events'] else None}
  data['events'].append(dict(body, hash=digest(body)))
  self.save(data)
  return body['id']

def view(data):
 items, reviews, sessions, captures = {}, {}, {}, {}
 for e in data['events']:
  p = e['payload']
  if e['action'] == 'proposal': items[e['id']] = dict(p, id=e['id'])
  elif e['action'] == 'review': reviews[p['target']] = p
  elif e['action'] == 'session': sessions[e['id']] = p
  elif e['action'] == 'capture': captures[e['id']] = p
 return items, reviews, sessions, captures

def active(items, reviews):
 approved = {i for i in items if reviews.get(i, {}).get('verdict') == 'accept'}
 superseded = {items[i]['supersedes'] for i in approved if items[i].get('supersedes')}
 return approved - superseded

def questions(data):
 items, reviews, _, _ = view(data)
 live = active(items, reviews)
 result = []
 pending = [i for i in items if i not in reviews]
 if pending: result.append({'priority':'review', 'targets':pending, 'question':'Review these proposals before treating them as shared state.'})
 for kind in KINDS:
  if not any(items[i]['kind'] == kind for i in live):
   result.append({'kind':kind, 'question':QUESTIONS[kind]})
 for i in live:
  if items[i]['kind'] == 'hypotheses':
   result.append({'target':i, 'question':'What evidence would falsify this hypothesis? Record contradictory evidence, too.'})
 return result

def report(data, root):
 items, reviews, sessions, captures = view(data)
 live = active(items, reviews)
 flags = []
 for i,p in items.items():
  if i not in reviews: flags.append({'type':'unreviewed', 'id':i})
  if (i in live or i not in reviews) and p['kind'] == 'findings' and (not p['evidence'] or any(e not in live for e in p['evidence'])):
   flags.append({'type':'unsupported_finding', 'id':i})
  if p.get('supersedes') and i not in reviews:
   flags.append({'type':'proposed_drift', 'id':i, 'from':p['supersedes']})
 baseline = next(reversed(captures.values()))['git'] if captures else data['baseline']
 current = snapshot(root)
 if current != baseline: flags.append({'type':'git_drift', 'baseline':baseline, 'current':current})
 for i,c in captures.items():
  if reviews.get(i,{}).get('verdict') != 'accept': flags.append({'type':'unreviewed_capture', 'id':i})
 return flags

def markdown(data, root, include_text=False):
 items, reviews, sessions, captures = view(data)
 lines = ['# Human–AI Research Disclosure', '', 'Generated: '+stamp(),
  'Mode: '+data['mode'], 'Tracking started: '+data['created'], '',
  'Coverage: explicit local records only. Imported history and AI attribution are self-reported.',
  'No automatic capture of third-party conversations. Human approval does not establish empirical truth.',
  'Reviewer names are local assertions, not authenticated signatures.', '',
  '## Research state']
 for i,p in items.items():
  r = reviews.get(i,{})
  text = p['text'].replace('\n',' ') if include_text and p['visibility']=='shareable' else '[content withheld]'
  lines.append(f"- {i} | {p['kind']} | {r.get('verdict','pending')} | active={i in active(items,reviews)} | validation={p['validation']} | supersedes={p.get('supersedes')} | evidence={','.join(p['evidence'])} | {text}")
 lines += ['', '## AI sessions (self-reported)', f'Count: {len(sessions)}']
 for i,s in sessions.items():
  lines.append(f"- {i}: provider={s['provider'] if include_text else '[withheld]'}; model={s['model'] if include_text else '[withheld]'}; origin={s['origin']}")
 lines += ['', '## Git provenance']
 for i,c in captures.items():
  lines.append(f"- {i}: session={c['session']}; commit={c['git'].get('head')}; diff_sha256={c['git'].get('diff_sha256')}; status_sha256={c['git'].get('status_sha256')}; items={','.join(c['items'])}; reviewed={reviews.get(i,{}).get('verdict','pending')}; attribution=self-reported")
 lines += ['', '## Review and drift checks', '```json', json.dumps(report(data, root),indent=2), '```', '',
  'Privacy: default export withholds research text and provider/model names. IDs, timestamps, Git hashes and counts remain linkable metadata.',
  'This report is a review aid; it does not certify completeness, authorship, research validity, or policy compliance.']
 return '\n'.join(lines)+'\n'

def main(argv=None):
 parser = argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--root', default='.')
 sub = parser.add_subparsers(dest='cmd',required=True)
 p=sub.add_parser('init'); p.add_argument('--mode', choices=['new','existing'],default='new')
 sub.add_parser('questions'); sub.add_parser('status'); sub.add_parser('resume'); sub.add_parser('check')
 sub.add_parser('interview')
 p=sub.add_parser('diff'); p.add_argument('target')
 p=sub.add_parser('propose'); p.add_argument('kind',choices=KINDS); p.add_argument('text'); p.add_argument('--source',required=True); p.add_argument('--evidence',nargs='*',default=[]); p.add_argument('--supersedes'); p.add_argument('--validation',choices=['unverified','preliminary','verified','contradicted'],default='unverified'); p.add_argument('--visibility',choices=['private','shareable'],default='private')
 p=sub.add_parser('review'); p.add_argument('target'); p.add_argument('--verdict',choices=['accept','reject'],required=True); p.add_argument('--reviewer',required=True); p.add_argument('--reason',required=True); p.add_argument('--confirm',action='store_true')
 p=sub.add_parser('session'); p.add_argument('--provider',required=True); p.add_argument('--model',required=True); p.add_argument('--origin',choices=['manual','imported'],default='manual'); p.add_argument('--summary',required=True)
 p=sub.add_parser('capture'); p.add_argument('--session',required=True); p.add_argument('--items',nargs='*',default=[])
 p=sub.add_parser('export'); p.add_argument('--include-shareable',action='store_true'); p.add_argument('--output',required=True)
 args=parser.parse_args(argv)
 store=Store(args.root)
 try:
  if args.cmd=='init':
   if store.path.exists(): raise ValueError('Already initialized; use resume')
   store.root.mkdir(parents=True,exist_ok=True)
   ignore=store.root/'.gitignore'
   existing=ignore.read_text() if ignore.exists() else ''
   if '.ai-research/' not in existing.splitlines(): ignore.write_text(existing+ ('\n' if existing and not existing.endswith('\n') else '')+'.ai-research/\n')
   data={'schema_version':1,'created':stamp(),'mode':args.mode,'baseline':snapshot(store.root),'events':[]}
   store.save(data)
   result={'initialized':args.mode,'history':'pre-tracking history is unverified; no backfilled attribution','questions':questions(data)}
  else:
   data=store.load(); items,reviews,sessions,captures=view(data)
   if args.cmd=='propose':
    if not args.text.strip() or not args.source.strip(): raise ValueError('Text and source cannot be empty')
    if args.supersedes and (args.supersedes not in active(items,reviews) or items[args.supersedes]['kind']!=args.kind): raise ValueError('Supersedes must name an active approved item of the same kind')
    for ref in args.evidence:
     if ref not in items or items[ref]['kind']!='evidence': raise ValueError('Evidence ID must refer to an evidence item')
    if args.validation=='verified' and args.kind=='findings' and (not args.evidence or any(i not in active(items,reviews) for i in args.evidence)):
     raise ValueError('Verified findings require reviewed evidence; validation remains a human assertion')
    result={'id':store.append(data,'proposal',{'kind':args.kind,'text':args.text,'source':args.source,'evidence':args.evidence,'supersedes':args.supersedes,'validation':args.validation,'visibility':args.visibility})}
   elif args.cmd=='review':
    if not args.confirm: raise ValueError('Review requires explicit --confirm after a human reviews the exact record')
    if args.target not in items and args.target not in captures: raise ValueError('Unknown review target')
    if not args.reviewer.strip() or not args.reason.strip(): raise ValueError('Reviewer and reason cannot be empty')
    if args.target in items and args.verdict=='accept':
     p=items[args.target]
     if p.get('supersedes') and p['supersedes'] not in active(items,reviews): raise ValueError('Stale replacement; propose against current state')
    result={'id':store.append(data,'review',{'target':args.target,'verdict':args.verdict,'reviewer':args.reviewer,'reason':args.reason})}
   elif args.cmd=='session':
    result={'id':store.append(data,'session',{'provider':args.provider,'model':args.model,'summary':args.summary,'origin':args.origin,'attribution':'self-reported'})}
   elif args.cmd=='capture':
    if args.session not in sessions: raise ValueError('Unknown session')
    if any(i not in items for i in args.items): raise ValueError('Unknown research item')
    snap=snapshot(store.root)
    if not snap['available']: raise ValueError('Capture requires a Git repository')
    result={'id':store.append(data,'capture',{'session':args.session,'items':args.items,'git':snap})}
   elif args.cmd=='interview':
    # Structured extraction is deliberately transparent: no undisclosed model call.
    created=[]
    for q in questions(data):
     if 'kind' not in q: continue
     answer=input(q['kind']+': '+q['question']+' [empty=defer]\n> ').strip()
     if not answer: continue
     print('Proposed '+q['kind']+': '+answer,file=sys.stderr)
     item=store.append(data,'proposal',{'kind':q['kind'],'text':answer,'source':'human interview','evidence':[],'supersedes':None,'validation':'unverified','visibility':'private'})
     created.append(item)
     if input('Accept this exact proposal? [yes/NO] ').strip().lower()=='yes':
      reviewer=input('Reviewer name: ').strip()
      if reviewer:
       store.append(data,'review',{'target':item,'verdict':'accept','reviewer':reviewer,'reason':'Confirmed exact interview answer'})
    result={'created':created,'questions':questions(data)}
   elif args.cmd=='diff':
    if args.target not in items: raise ValueError('Unknown proposal')
    item=items[args.target]
    old=items[item['supersedes']]['text'] if item.get('supersedes') else ''
    result={'target':args.target,'diff':''.join(difflib.unified_diff(old.splitlines(True),item['text'].splitlines(True),fromfile='approved',tofile='proposal')),'before':old,'after':item['text']}
   elif args.cmd=='questions': result=questions(data)
   elif args.cmd=='check': result={'flags':report(data,store.root)}
   elif args.cmd=='resume': result={'active':[items[i] for i in sorted(active(items,reviews))],'questions':questions(data),'flags':report(data,store.root)}
   elif args.cmd=='status': result={'items':items,'reviews':reviews,'sessions':sessions,'captures':captures}
   elif args.cmd=='export':
    target=Path(args.output).resolve()
    if target==store.path or target.exists(): raise ValueError('Export will not overwrite an existing file')
    target.write_text(markdown(data,store.root,args.include_shareable)); result={'exported':str(target)}
  print(json.dumps(result,ensure_ascii=False,indent=2))
  return 0
 except (ValueError,OSError,json.JSONDecodeError) as e:
  print('Error: '+str(e),file=sys.stderr); return 2

if __name__=='__main__': sys.exit(main())
