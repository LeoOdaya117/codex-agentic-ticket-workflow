#!/usr/bin/env python3
"""Local ticket lifecycle. No external packages, network or credentials."""
import argparse, datetime, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TICKETS = ROOT / 'tickets'
TEMPLATES = Path(__file__).resolve().parent / 'templates'
STAGES = ['Open','Investigating','Planning','Implementing','Code Review','QA Testing','Ready for Human Verification','Done','Blocked']
NEXT = {
 'Open': {'Investigating','Blocked'}, 'Investigating': {'Planning','Blocked'},
 'Planning': {'Implementing','Blocked'},'Implementing': {'Code Review','Blocked'},
 'Code Review': {'Implementing','QA Testing','Blocked'},
 'QA Testing': {'Implementing','Ready for Human Verification','Blocked'},
 'Ready for Human Verification': {'Implementing','Done'},'Blocked': {'Investigating','Planning','Implementing'}, 'Done':set()
}
def directory(id):
 if not re.fullmatch(r'TKT-\d{4,}',id): raise ValueError('Expected ticket ID TKT-0001')
 return TICKETS/id

def ticket_directory(id, ticket_dir=None):
 if not re.fullmatch(r'TKT-\d{4,}',id): raise ValueError('Expected ticket ID TKT-0001')
 if ticket_dir:
  path=Path(ticket_dir).expanduser().resolve()
  if path.name != id: raise ValueError(f'--ticket-dir must point to the {id} directory')
  return path
 for path in [TICKETS/id, ROOT/'.codex'/'tickets'/id]:
  if path.is_dir(): return path
 return TICKETS/id

def new(args):
 if not args.title.strip(): raise ValueError('Title cannot be empty')
 TICKETS.mkdir(exist_ok=True)
 ids=[int(p.name[4:]) for p in TICKETS.iterdir() if p.is_dir() and re.fullmatch(r'TKT-\d{4,}',p.name)]
 idx=max(ids,default=0)+1
 while True:
  id=f'TKT-{idx:04d}'; d=directory(id)
  try: d.mkdir(); break
  except FileExistsError: idx+=1
 (d/'attachments').mkdir();(d/'agent-reports').mkdir()
 template=(TEMPLATES/'ticket.md').read_text(encoding='utf-8')
 (d/'ticket.md').write_text(template.format(id=id,title=args.title.strip(),type=args.type,created=datetime.date.today().isoformat()),encoding='utf-8')
 for template_file in ['investigation.md','plan.md','qa-report.md']:
  (d/template_file).write_text((TEMPLATES/template_file).read_text(encoding='utf-8'),encoding='utf-8')
 state={'id':id,'title':args.title.strip(),'type':args.type,'status':'Open','history':[{'status':'Open','at':datetime.datetime.now(datetime.timezone.utc).isoformat()}],'repair_cycles':0}
 save(d,state); print(f'{id}\n{d}')

def load(id, ticket_dir=None):
 d=ticket_directory(id,ticket_dir)
 if not (d/'state.json').is_file():raise ValueError('Ticket not found')
 return d,json.loads((d/'state.json').read_text(encoding='utf-8'))
def save(d,s):
 temp=d/'state.json.tmp';temp.write_text(json.dumps(s,indent=2)+'\n',encoding='utf-8');temp.replace(d/'state.json')
def status(args):
 d,s=load(args.id,args.ticket_dir); old=s['status']; target=args.status
 if target not in NEXT.get(old,set()):raise ValueError(f'Invalid transition: {old} -> {target}')
 if target in ('Ready for Human Verification','Done'):
  if target=='Ready for Human Verification':
   qa=(d/'qa-report.md').read_text(encoding='utf-8')
   if not args.qa_pass or not re.search(r'(?im)^Result:\s*PASS\s*$',qa):raise ValueError('Requires --qa-pass and qa-report.md containing Result: PASS; lead must verify real test evidence')
   if not ('## Executed commands' in qa and len(qa.strip())>240):raise ValueError('QA report incomplete')
  missing=delivery_gaps(d)
  if missing:raise ValueError('Requires committed and pushed delivery details before human verification: '+', '.join(missing))
 if target=='Done':
  if not args.human_approved or not (d/'verification.md').is_file():raise ValueError('Requires --human-approved and verification.md')
 if old=='QA Testing' and target=='Implementing':
  s['repair_cycles']+=1
  if s['repair_cycles']>3:raise ValueError('Repair cycle limit exceeded; set status Blocked')
 s['status']=target
 s['history'].append({'status':target,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 save(d,s);print(f'{args.id}: {old} -> {target}')
def check(args):
 d,s=load(args.id,args.ticket_dir);missing=[]
 for f in ['ticket.md','state.json','plan.md','investigation.md','qa-report.md']:
  if not (d/f).exists():missing.append(f)
 content=(d/'ticket.md').read_text(encoding='utf-8')
 if '[Describe observed issue' in content:missing.append('ticket.md content still placeholder')
 if s['status'] in ('Ready for Human Verification','Done') and delivery_gaps(d):
  missing.append('delivery details: '+', '.join(delivery_gaps(d)))
 print(json.dumps({'ticket':s['id'],'status':s['status'],'missing':missing},indent=2));return int(bool(missing))

def delivery_gaps(d):
 content=(d/'ticket.md').read_text(encoding='utf-8') if (d/'ticket.md').is_file() else ''
 def value(name):
  match=re.search(r'^\s*(?:[-*]\s+)?(?:\*\*)?'+re.escape(name)+r'(?:\*\*)?\s*:\s*(.*?)\s*$',content,re.I|re.M)
  return match.group(1).strip() if match else ''
 missing=[]
 if not value('Branch') or value('Branch').startswith('['): missing.append('branch')
 if not value('Worktree') or value('Worktree').startswith('['): missing.append('worktree')
 if not re.fullmatch(r'[0-9a-fA-F]{7,40}',value('Commit SHA') or value('Commit')): missing.append('commit SHA')
 if not re.match(r'https?://\S+',value('Pull request'),re.I): missing.append('pull request URL')
 return missing
def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
 n=sub.add_parser('new');n.add_argument('--title',required=True);n.add_argument('--type',choices=['bug','feature','enhancement','refactor','task'],default='bug');n.set_defaults(func=new)
 sh=sub.add_parser('show');sh.add_argument('id');sh.add_argument('--ticket-dir');sh.set_defaults(func=lambda a:print(json.dumps(load(a.id,a.ticket_dir)[1],indent=2)))
 st=sub.add_parser('set-status');st.add_argument('id');st.add_argument('status',choices=STAGES);st.add_argument('--ticket-dir');st.add_argument('--qa-pass',action='store_true');st.add_argument('--human-approved',action='store_true');st.set_defaults(func=status)
 ch=sub.add_parser('check');ch.add_argument('id');ch.add_argument('--ticket-dir');ch.set_defaults(func=check)
 a=p.parse_args()
 try: return a.func(a) or 0
 except (ValueError, OSError, json.JSONDecodeError) as exc: print(f'ERROR: {exc}',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
