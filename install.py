#!/usr/bin/env python3
"""Non-destructive installer; refuses overwrites and preserves existing Codex registrations."""
import argparse, shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('target');p.add_argument('--force',action='store_true',help='Replace matching kit files only (not config.toml)');args=p.parse_args()
source=Path(__file__).resolve().parent;target=Path(args.target).expanduser().resolve();target.mkdir(parents=True,exist_ok=True)
count=0;skipped=[]
for folder in ['.agents','.codex']:
 for file in (source/folder).rglob('*'):
  if not file.is_file() or file.name=='team-inventory.json':continue
  rel=file.relative_to(source);dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True)
  if rel.as_posix()=='.codex/config.toml':skipped.append(str(rel));continue
  if dest.exists() and not args.force:skipped.append(str(rel));continue
  shutil.copy2(file,dest);count+=1
addon=source/'AGENTS.ticket-addon.md'
if (target/'AGENTS.md').exists():
 dest=target/'AGENTS.ticket-addon.md'
 if not dest.exists() or args.force:shutil.copy2(addon,dest);count+=1
 print('Existing AGENTS.md preserved. See AGENTS.ticket-addon.md and merge if appropriate.')
else:shutil.copy2(addon,target/'AGENTS.md');count+=1
(target/'tickets').mkdir(exist_ok=True)
print(f'Installed {count} files into {target}. Skipped {len(skipped)} existing files.')
if skipped: print('Skipped:\n'+'\n'.join(skipped))
