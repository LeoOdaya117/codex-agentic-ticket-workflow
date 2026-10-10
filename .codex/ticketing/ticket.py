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

def load(id):
 d=directory(id)
 if not (d/'state.json').is_file():raise ValueError('Ticket not found')
 return d,json.loads((d/'state.json').read_text(encoding='utf-8'))
def save(d,s):
 temp=d/'state.json.tmp';temp.write_text(json.dumps(s,indent=2)+'\n',encoding='utf-8');temp.replace(d/'state.json')
def status(args):
 d,s=load(args.id); old=s['status']; target=args.status
 if target not in NEXT.get(old,set()):raise ValueError(f'Invalid transition: {old} -> {target}')
 if target=='Ready for Human Verification':
  qa=(d/'qa-report.md').read_text(encoding='utf-8')
  if not args.qa_pass or not re.search(r'(?im)^Result:\s*PASS\s*$',qa):raise ValueError('Requires --qa-pass and qa-report.md containing Result: PASS; lead must verify real test evidence')
  if not ('## Executed commands' in qa and len(qa.strip())>240):raise ValueError('QA report incomplete')
 if target=='Done':
  if not args.human_approved or not (d/'verification.md').is_file():raise ValueError('Requires --human-approved and verification.md')
 if old=='QA Testing' and target=='Implementing':
  s['repair_cycles']+=1
  if s['repair_cycles']>3:raise ValueError('Repair cycle limit exceeded; set status Blocked')
 s['status']=target
 s['history'].append({'status':target,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 save(d,s);print(f'{args.id}: {old} -> {target}')
def check(args):
 d,s=load(args.id);missing=[]
 for f in ['ticket.md','state.json','plan.md','investigation.md','qa-report.md']:
  if not (d/f).exists():missing.append(f)
 content=(d/'ticket.md').read_text(encoding='utf-8')
 if '[Describe observed issue' in content:missing.append('ticket.md content still placeholder')
 print(json.dumps({'ticket':s['id'],'status':s['status'],'missing':missing},indent=2));return int(bool(missing))
def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
 n=sub.add_parser('new');n.add_argument('--title',required=True);n.add_argument('--type',choices=['bug','feature','enhancement','refactor','task'],default='bug');n.set_defaults(func=new)
 sh=sub.add_parser('show');sh.add_argument('id');sh.set_defaults(func=lambda a:print(json.dumps(load(a.id)[1],indent=2)))
 st=sub.add_parser('set-status');st.add_argument('id');st.add_argument('status',choices=STAGES);st.add_argument('--qa-pass',action='store_true');st.add_argument('--human-approved',action='store_true');st.set_defaults(func=status)
 ch=sub.add_parser('check');ch.add_argument('id');ch.set_defaults(func=check)
 a=p.parse_args()
 try: return a.func(a) or 0
 except (ValueError, OSError, json.JSONDecodeError) as exc: print(f'ERROR: {exc}',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
