#!/usr/bin/env python3
"""Read-only inventory of existing skills/agents; no hardcoded project stack."""
import argparse, json, re
from pathlib import Path

try:
 import tomllib
except ModuleNotFoundError:  # Python 3.9/3.10: use the parser bundled with pip.
 from pip._vendor import tomli as tomllib

ROLES={
 'investigator':['investigat','diagnos','debug','triage','repro'],
 'architect':['architect','design','system','tech-lead'],
 'backend':['backend','api','server','laravel','yii','django'],
 'frontend':['frontend','ui','ux','react','next','ionic'],
 'database':['database','sql','migration','postgres','mysql'],
 'security':['security','audit','pentest','owasp'],
 'devops':['devops','infra','deployment','ci-cd','sre'],
 'reviewer':['review','code-review','quality-review'],
 'qa':['qa','test','verification','playwright','testing'],
 'docs':['documentation','writer','docs','technical-writing']}
SKILL_DIRS=['.agents/skills','.codex/skills']
AGENT_DIRS=['.codex/agents','.agents/agents']
IGNORE={'create-ticket','process-ticket','verify-ticket','project-init'}

def inspect(root):
 root=Path(root).resolve();items=[]
 def entry(kind,path,name,description='',registered=False):
  relative=str(path.relative_to(root)).replace('\\','/')
  target=(name+' '+description).lower()
  scores={role:sum(len(term) for term in keys if term in target) for role,keys in ROLES.items()}
  roles=[role for role,score in sorted(scores.items(),key=lambda t:-t[1]) if score and score==max(scores.values())]
  items.append({'kind':kind,'name':name,'path':relative,'description':description[:300],'roles':roles,'registered':registered})
 for folder in SKILL_DIRS:
  base=root/folder
  if base.is_dir():
   for md in sorted(base.glob('*/SKILL.md')):
    contents=md.read_text(encoding='utf-8',errors='replace');match=re.search(r'^description:\s*(.+)$',contents,re.M)
    entry('skill',md,md.parent.name,match.group(1).strip('"\'') if match else '')
 for folder in AGENT_DIRS:
  base=root/folder
  if base.is_dir():
   for file in sorted(base.glob('*.toml')):
    try: data=tomllib.loads(file.read_text(encoding='utf-8'));description=str(data.get('description',''))
    except (ValueError,OSError): description='Unparsed TOML: inspect manually'
    entry('agent',file,file.stem,description)
   for file in sorted(base.glob('*.md')):
    entry('agent-instructions',file,file.stem,file.read_text(encoding='utf-8',errors='replace')[:250])
 config=root/'.codex/config.toml'
 registered=[]
 if config.exists():
  try:
   data=tomllib.loads(config.read_text(encoding='utf-8'))
   # [agents] contains runtime settings; named registrations are the local
   # agent definition files discovered above, not keys such as `enabled`.
   if isinstance(data.get('agents'),dict):
    registered.extend(name for name,value in data['agents'].items() if isinstance(value,dict))
  except (ValueError,OSError): pass
 agent_files=root/'.codex/agents'
 if agent_files.is_dir():
  registered.extend(path.stem for path in sorted(agent_files.glob('*.toml')) if path.stem not in registered)
 for item in items:
  if item['kind']=='agent' and item['name'] in registered:item['registered']=True
 return {'root':str(root),'registered_agent_names':registered,'items':items,
         'by_role':{role:[x for x in items if role in x['roles'] and x['name'] not in IGNORE] for role in ROLES},
         'note':'Inventory is heuristic. Read candidate instructions before delegation. Skills are not automatically subagents.'}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--root',default='.');parser.add_argument('--out');a=parser.parse_args()
 result=json.dumps(inspect(a.root),indent=2)
 if a.out:
  p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(result+'\n',encoding='utf-8');print(p)
 else: print(result)
