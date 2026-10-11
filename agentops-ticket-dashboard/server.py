#!/usr/bin/env python3
"""Local-only Codex ticket dashboard; Python standard library."""
import argparse, hashlib, json, os, re, subprocess, threading, time, uuid, shutil, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from email.parser import BytesParser
from email.policy import default as email_policy
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote, parse_qs

ROOT = Path(__file__).resolve().parent
LOCK = threading.RLock()
RUNS = {}
REPOSITORIES = {}
DEFAULT_REPO_ID = None
MAX_EVENTS = 2500
ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$')
ACTIVE_TICKET_STATUSES = {'investigating', 'planning', 'implementing', 'code review', 'qa testing'}
PUBLIC_ASSETS = {
    '/styles.css': ('styles.css', 'text/css; charset=utf-8'),
    '/theme.js': ('theme.js', 'text/javascript; charset=utf-8'),
    '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
}
MAX_FEEDBACK_UPLOAD = 20 * 1024 * 1024
MAX_FEEDBACK_FILES = 10

def now(): return datetime.now(timezone.utc).isoformat()
def repository_id(repo):
    return hashlib.sha256(str(repo.resolve()).casefold().encode('utf-8')).hexdigest()[:12]

def add_repository(path):
    if not str(path or '').strip(): raise ValueError('Enter a repository folder path')
    repo=Path(path).expanduser().resolve()
    if not repo.is_dir(): raise ValueError('Folder does not exist or is not accessible')
    identifier=repository_id(repo)
    with LOCK: REPOSITORIES[identifier]=repo
    return {'id':identifier,'path':str(repo),'name':repo.name or str(repo)}

def selected_repository(handler):
    requested=parse_qs(urlparse(handler.path).query).get('repo',[DEFAULT_REPO_ID])[0]
    with LOCK: repo=REPOSITORIES.get(requested)
    if repo is None: raise ValueError('Select a configured repository')
    return repo,requested

def runs_for_repository(selected_id):
    with LOCK:
        return [{k:v for k,v in run.items() if k not in ('events','process')}
                for run in RUNS.values() if run.get('repo_id')==selected_id]

def choose_repository_folder():
    """Open a native folder chooser when Tk is available; callers may use path entry otherwise."""
    picker=("import tkinter as tk; from tkinter import filedialog; "
            "root=tk.Tk(); root.withdraw(); root.attributes('-topmost',True); "
            "print(filedialog.askdirectory(title='Add a repository folder',mustexist=True)); root.destroy()")
    options={'capture_output':True,'text':True,'encoding':'utf-8','errors':'replace','timeout':300}
    if os.name=='nt': options['creationflags']=getattr(subprocess,'CREATE_NO_WINDOW',0)
    try: result=subprocess.run([sys.executable,'-c',picker],**options)
    except subprocess.TimeoutExpired as exc: raise RuntimeError('Folder picker timed out') from exc
    if result.returncode: raise RuntimeError((result.stderr or 'Folder picker could not start').strip()[:500])
    return result.stdout.strip()

def read_text(p, limit=200000):
    try: return p.read_text(encoding='utf-8', errors='replace')[:limit]
    except OSError: return ''
def find_ticket_dir(repo, ticket_id):
    if not ID_RE.fullmatch(ticket_id): return None
    for base in [repo/'tickets', repo/'.codex'/'tickets']:
        p=base/ticket_id
        if p.is_dir() and p.resolve().is_relative_to(repo.resolve()): return p
    return None

def _git(repo, *args, check=True):
    try:
        result=subprocess.run(['git','-C',str(repo),*map(str,args)],capture_output=True,
                              text=True,encoding='utf-8',errors='replace',timeout=30)
    except FileNotFoundError as exc:
        raise RuntimeError('Git is required to process tickets in isolated worktrees') from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Git timed out while preparing the ticket worktree') from exc
    if check and result.returncode:
        detail=(result.stderr or result.stdout or 'unknown Git error').strip()
        raise RuntimeError(f"Git {' '.join(map(str,args))} failed: {detail[:1200]}")
    return result

def acquire_process_lock(path):
    """Hold an OS-level lock so separate dashboard instances cannot run one ticket twice."""
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    stream=path.open('a+b')
    try:
        if os.name=='nt':
            import msvcrt
            stream.seek(0,os.SEEK_END)
            if stream.tell()==0:
                stream.write(b'0');stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        return stream
    except (OSError,BlockingIOError) as exc:
        stream.close()
        raise ValueError('A processing run is already active for this ticket') from exc

def release_process_lock(stream):
    if not stream:return
    try:
        if os.name=='nt':
            import msvcrt
            stream.seek(0)
            msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
    except OSError:
        pass
    finally:
        stream.close()

def ensure_ticket_worktree(repo, ticket_id):
    """Create or resume the persistent branch and worktree assigned to one ticket."""
    if not ID_RE.fullmatch(ticket_id): raise ValueError('Invalid ticket ID')
    result=_git(repo,'rev-parse','--show-toplevel')
    root=Path(result.stdout.strip()).resolve()
    base_commit=_git(root,'rev-parse','HEAD').stdout.strip()
    branch=f'codex/{ticket_id}'
    worktree_parent=root.parent/f'{root.name}-ticket-worktrees'
    worktree=worktree_parent/ticket_id
    lock_path=worktree_parent/'.locks'/f'{ticket_id}.lock'
    records=[]
    for block in _git(root,'worktree','list','--porcelain').stdout.split('\n\n'):
        entry={}
        for line in block.splitlines():
            key,_,value=line.partition(' ')
            if key in ('worktree','branch'): entry[key]=value
        if entry.get('worktree'): records.append(entry)
    branch_ref=f'refs/heads/{branch}'
    attached=next((entry for entry in records if entry.get('branch')==branch_ref),None)
    def same_path(left,right):
        return os.path.normcase(os.path.abspath(str(left)))==os.path.normcase(os.path.abspath(str(right)))
    if attached:
        if not same_path(attached['worktree'],worktree):
            raise RuntimeError(f"Branch {branch} is already checked out at {attached['worktree']}")
        if not worktree.is_dir():
            raise RuntimeError(f"Git still records {branch} at a missing worktree path: {worktree}")
        worktree_commit=_git(worktree,'rev-parse','HEAD').stdout.strip()
        return {'root':root,'path':worktree.resolve(),'branch':branch,'base_commit':base_commit,'lock_path':lock_path,
                'head_commit':worktree_commit,'resumed':True}
    if worktree.exists():
        raise RuntimeError(f'Ticket worktree path already exists but is not registered with Git: {worktree}')
    worktree_parent.mkdir(parents=True,exist_ok=True)
    branch_exists=_git(root,'show-ref','--verify','--quiet',branch_ref,check=False).returncode==0
    if branch_exists:
        _git(root,'worktree','add',str(worktree),branch)
    elif _git(root,'show-ref','--verify','--quiet',f'refs/remotes/origin/{branch}',check=False).returncode==0:
        _git(root,'worktree','add','-b',branch,str(worktree),f'origin/{branch}')
    else:
        _git(root,'worktree','add','-b',branch,str(worktree),'HEAD')
    head_commit=_git(worktree,'rev-parse','HEAD').stdout.strip()
    return {'root':root,'path':worktree.resolve(),'branch':branch,'base_commit':base_commit,'lock_path':lock_path,
            'head_commit':head_commit,'resumed':False}

def local_request_allowed(headers, port):
    host = urlparse('//' + headers.get('Host', '')).hostname
    if host not in ('127.0.0.1', 'localhost'):
        return False
    origin = headers.get('Origin')
    if origin is None:
        return True  # Local CLI/API clients do not send Origin.
    parsed = urlparse(origin)
    return parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost') and parsed.port == port

def summary(p):
    md=read_text(p/'ticket.md', 50000)
    title=next((x.lstrip('# ').strip() for x in md.splitlines() if x.startswith('# ')),p.name)
    state={}
    try: state=json.loads((p/'state.json').read_text(encoding='utf-8'))
    except (OSError, ValueError): pass
    def field(key):
        m=re.search(r'^\s*(?:[-*]\s+)?(?:\*\*)?'+re.escape(key)+r'(?:\*\*)?\s*:\s*(?:\*\*)?\s*(.*)$',md,re.I|re.M)
        return m.group(1).strip() if m else ''
    return {'id':p.name,'title':title,'status':state.get('status') or field('Status') or 'Open',
       'priority':field('Priority') or state.get('priority','Unspecified'),
       'type':field('Type') or state.get('type','Task'),
       'pull_request':field('Pull request'),
       'updated':max((f.stat().st_mtime for f in p.iterdir() if f.is_file()),default=0),
       'checked':sum(bool(re.match(r'^\s*- \[x\]',x,re.I)) for x in md.splitlines()),
       'total':sum(bool(re.match(r'^\s*- \[[ x]\]',x,re.I)) for x in md.splitlines())}

def tickets(repo):
    out={}
    for base in [repo/'tickets', repo/'.codex'/'tickets']:
        if base.is_dir():
            for p in base.iterdir():
                if p.is_dir() and ID_RE.fullmatch(p.name) and (p/'ticket.md').is_file():
                    out[p.name]=summary(p)
    return sorted(out.values(),key=lambda t:t['updated'],reverse=True)

def active_ticket_count(ticket_summaries):
    """Count workflow-active tickets, including work started outside this dashboard."""
    return sum(str(t.get('status', '')).strip().casefold() in ACTIVE_TICKET_STATUSES for t in ticket_summaries)

def public_asset(path):
    """Resolve only dashboard-owned, explicitly allowlisted static assets."""
    asset = PUBLIC_ASSETS.get(path)
    if not asset: return None
    filename, content_type = asset
    root = (ROOT/'public').resolve()
    target = (root/filename).resolve()
    if not target.is_relative_to(root): return None
    return target, content_type

def detail(repo, tid):
    p=find_ticket_dir(repo,tid)
    if not p: return None
    files={}
    for name in ['ticket.md','investigation.md','reproduction.md','plan.md','qa-report.md','verification.md','state.json','tasks.json']:
        f=p/name
        if f.is_file(): files[name]=read_text(f)
    reports=[]
    folder=p/'agent-reports'
    if folder.is_dir():
        for f in sorted(folder.glob('*.md'))[:50]: reports.append({'name':f.name,'content':read_text(f,50000)})
    return {'summary':summary(p),'files':files,'reports':reports}

def complete_ticket(repo, ticket_id):
    """Record an explicit dashboard approval and use the repository state tool."""
    ticket_dir=find_ticket_dir(repo,ticket_id)
    if not ticket_dir: raise ValueError('Ticket not found')
    if str(summary(ticket_dir)['status']).strip().casefold()!='ready for human verification':
        raise ValueError('Ticket is not Ready for Human Verification')
    state_tool=repo/'.codex'/'ticketing'/'ticket.py'
    if not state_tool.is_file() or not state_tool.resolve().is_relative_to(repo.resolve()):
        raise ValueError('Ticket state tool not found at .codex/ticketing/ticket.py')
    verification=ticket_dir/'verification.md'
    if not verification.resolve().is_relative_to(ticket_dir.resolve()):
        raise ValueError('verification.md must stay inside the ticket directory')
    record=(f"## Human approval — {now()}\n\n"
            'Decision: Approved via the AgentOps dashboard.\n\n')
    try:
        with verification.open('a',encoding='utf-8',newline='') as f:
            f.write(record)
    except OSError as exc:
        raise RuntimeError(f'Could not write verification.md: {exc}') from exc
    try:
        result=subprocess.run([sys.executable,str(state_tool), 'set-status', ticket_id,
                               'Done','--human-approved'],cwd=repo,capture_output=True,
                              text=True,encoding='utf-8',errors='replace',timeout=30)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Ticket state update timed out; check the ticket status before retrying') from exc
    if result.returncode:
        message=(result.stderr or result.stdout or 'Ticket state update failed').strip()
        raise RuntimeError(message[:2000])
    if str(summary(ticket_dir)['status']).strip().casefold()!='done':
        raise RuntimeError('Ticket state tool returned success, but the ticket is not marked Done')
    return {'message':(result.stdout or f'{ticket_id}: marked Done').strip()}

def reject_ticket(repo, ticket_id, description, uploads=None):
    """Save explicit human feedback and reopen a verified ticket for corrections."""
    ticket_dir=find_ticket_dir(repo,ticket_id)
    if not ticket_dir: raise ValueError('Ticket not found')
    if str(summary(ticket_dir)['status']).strip().casefold()!='ready for human verification':
        raise ValueError('Ticket is not Ready for Human Verification')
    description=str(description or '').strip()
    if not description: raise ValueError('Describe what needs correction before reopening the ticket')
    if len(description)>10000: raise ValueError('Feedback must be 10,000 characters or fewer')
    uploads=uploads or []
    if len(uploads)>MAX_FEEDBACK_FILES: raise ValueError(f'Attach no more than {MAX_FEEDBACK_FILES} files')
    if sum(len(content) for _,content in uploads)>MAX_FEEDBACK_UPLOAD:
        raise ValueError('Attachments must total 20 MB or less')

    state_tool=repo/'.codex'/'ticketing'/'ticket.py'
    if not state_tool.is_file() or not state_tool.resolve().is_relative_to(repo.resolve()):
        raise ValueError('Ticket state tool not found at .codex/ticketing/ticket.py')
    verification=ticket_dir/'verification.md'
    if not verification.resolve().is_relative_to(ticket_dir.resolve()):
        raise ValueError('verification.md must stay inside the ticket directory')

    saved=[]
    if uploads:
        attachment_dir=ticket_dir/'attachments'
        attachment_dir.mkdir(parents=True,exist_ok=True)
        if not attachment_dir.resolve().is_relative_to(ticket_dir.resolve()):
            raise ValueError('Ticket attachments must stay inside the ticket directory')
        for original_name,content in uploads:
            filename=str(original_name or 'attachment').replace('\\','/').rsplit('/',1)[-1]
            filename=re.sub(r'[^A-Za-z0-9._-]+','_',filename).strip('._')[:120] or 'attachment'
            stem,suffix=Path(filename).stem,Path(filename).suffix
            target=attachment_dir/filename
            counter=2
            while target.exists():
                target=attachment_dir/f'{stem}-{counter}{suffix}'
                counter+=1
            if not target.resolve().is_relative_to(attachment_dir.resolve()):
                raise ValueError('Attachment must stay inside the ticket attachments directory')
            try:
                with target.open('xb') as f: f.write(content)
            except OSError as exc:
                raise RuntimeError(f'Could not save attachment: {exc}') from exc
            saved.append(target.relative_to(ticket_dir).as_posix())

    attachment_note=''.join(f'- `{path}`\n' for path in saved) or '- None\n'
    record=(f'## Human rejection — {now()}\n\n'
            'Decision: Rejected; corrections requested via the AgentOps dashboard.\n\n'
            f'### Feedback\n\n{description}\n\n'
            f'### Attachments\n\n{attachment_note}\n')
    try:
        with verification.open('a',encoding='utf-8',newline='') as f: f.write(record)
    except OSError as exc:
        raise RuntimeError(f'Could not write verification.md: {exc}') from exc
    try:
        result=subprocess.run([sys.executable,str(state_tool),'set-status',ticket_id,'Implementing'],
                              cwd=repo,capture_output=True,text=True,encoding='utf-8',
                              errors='replace',timeout=30)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Ticket reopen timed out; check the ticket status before retrying') from exc
    if result.returncode:
        message=(result.stderr or result.stdout or 'Ticket reopen failed').strip()
        raise RuntimeError(message[:2000])
    if str(summary(ticket_dir)['status']).strip().casefold()!='implementing':
        raise RuntimeError('Ticket state tool returned success, but the ticket was not reopened')
    return {'message':(result.stdout or f'{ticket_id}: reopened for corrections').strip(),
            'attachments':saved}

def update(run_id, **kwargs):
    with LOCK:
        run=RUNS.get(run_id)
        if run: run.update(kwargs)

def log_event(run_id, data):
    with LOCK:
        run=RUNS.get(run_id)
        if not run:return
        run['events'].append({'time':now(),**data})
        if len(run['events'])>MAX_EVENTS:run['events']=run['events'][-MAX_EVENTS:]

def stage_create_uploads(repo, uploads):
    """Stage browser uploads inside the selected workspace for the lifetime of a create run."""
    uploads=uploads or []
    if len(uploads)>MAX_FEEDBACK_FILES: raise ValueError(f'Attach no more than {MAX_FEEDBACK_FILES} files')
    if sum(len(content) for _,content in uploads)>MAX_FEEDBACK_UPLOAD:
        raise ValueError('Attachments must total 20 MB or less')
    if not uploads: return None,[]
    repo=Path(repo).resolve()
    staging=Path(tempfile.mkdtemp(prefix='.ticket-intake-',dir=repo)).resolve()
    if not staging.is_relative_to(repo):
        shutil.rmtree(staging,ignore_errors=True)
        raise ValueError('Upload staging must stay inside the selected repository')
    staged=[]
    try:
        for original_name,content in uploads:
            filename=str(original_name or 'attachment').replace('\\','/').rsplit('/',1)[-1]
            filename=re.sub(r'[^A-Za-z0-9._-]+','_',filename).strip('._')[:120] or 'attachment'
            stem,suffix=Path(filename).stem,Path(filename).suffix
            target=staging/filename
            counter=2
            while target.exists():
                target=staging/f'{stem}-{counter}{suffix}'
                counter+=1
            if not target.resolve().is_relative_to(staging):
                raise ValueError('Attachment must stay inside the upload staging directory')
            with target.open('xb') as stream: stream.write(content)
            staged.append(str(target))
        return staging,staged
    except OSError as exc:
        shutil.rmtree(staging,ignore_errors=True)
        raise RuntimeError(f'Could not stage attachment: {exc}') from exc
    except Exception:
        shutil.rmtree(staging,ignore_errors=True)
        raise

def spawn_codex(repo, ticket_id, mode, description='', attachments=None, repo_id=None, uploads=None):
    if not shutil.which('codex') and not shutil.which('codex.cmd'): raise RuntimeError('Codex CLI not found on PATH. Install and sign in first.')
    staging=None
    run_id=uuid.uuid4().hex[:12]
    process_worktree=None
    ticket_dir=None
    process_lock_handle=None
    if mode=='process':
        ticket_dir=find_ticket_dir(repo,ticket_id)
        if not ticket_dir: raise ValueError('Ticket not found')
        ticket_dir=ticket_dir.resolve()
        with LOCK:
            selected_id=repo_id or repository_id(repo)
            if any(run.get('repo_id')==selected_id and run.get('ticket_id')==ticket_id
                   and run.get('mode')=='process' and run.get('status') in ('launching','running','cancelling')
                   for run in RUNS.values()):
                raise ValueError(f'A processing run is already active for {ticket_id}')
            process_worktree=ensure_ticket_worktree(repo,ticket_id)
            process_lock_handle=acquire_process_lock(process_worktree['lock_path'])
            RUNS[run_id]={'id':run_id,'repo_id':selected_id,'ticket_id':ticket_id,'mode':'process',
                          'status':'launching','started':now(),'ended':None,'exit_code':None,'events':[],
                          'pid':None,'process':None,'worktree':str(process_worktree['path']),
                          'branch':process_worktree['branch']}
        prompt=(f'Use the installed $process-ticket workflow for {ticket_id}. Read repository AGENTS.md and applicable skill instructions. '
                f"The dashboard assigned branch {process_worktree['branch']} in the isolated worktree {process_worktree['path']}. "
                f"The ticket branch currently starts at {process_worktree['head_commit']}; the configured checkout HEAD is {process_worktree['base_commit']}. "
                f'Keep all code edits, tests, and Git operations in that worktree. '
                f'Canonical ticket records and attachments are in {ticket_dir}; use this absolute directory for all ticket files and pass '
                f'--ticket-dir "{ticket_dir}" to ticket.py show, check, and set-status commands. '
                'If verification.md contains a Human rejection entry, read its feedback and every referenced attachment before planning corrections. '
                'Investigate and reproduce if possible, plan, delegate via available registered agents, implement, review and QA, '
                'record truthful evidence in ticket files. After QA passes, commit the ticket changes, push the assigned branch, and create or update its pull request. '
                'Record branch, worktree, commit SHA, and pull request URL in ticket.md and the QA report before setting Ready for Human Verification. '
                'Leave the pull request open for human testing; never merge, deploy, or close it. '
                'Do not claim test success unless commands actually passed.')
    else:
        if not description.strip():raise ValueError('Description is required')
        staging,uploaded_paths=stage_create_uploads(repo,uploads)
        attachment_lines='\n'.join([*(str(x) for x in (attachments or [])),*uploaded_paths])
        prompt=(f'Use the installed $create-ticket skill. Create a structured ticket from this report and any existing referenced local evidence. '
                f'Do not implement.\n\nIssue description:\n{description[:10000]}\n\nAttachment paths (only inspect if present):\n{attachment_lines}')
    exe=shutil.which('codex') or shutil.which('codex.cmd')
    args=[exe,'exec','--json','--sandbox','workspace-write']
    if process_worktree:
        args.extend(['--add-dir',str(ticket_dir)])
    args.append(prompt)
    if mode!='process':
      with LOCK:
        RUNS[run_id]={'id':run_id,'repo_id':repo_id or repository_id(repo),'ticket_id':ticket_id if mode=='process' else None,'mode':mode,'status':'launching','started':now(),'ended':None,'exit_code':None,'events':[],'pid':None,'process':None,
                      'worktree':None,'branch':None}
    def worker():
        try:
            opts={'cwd':str(process_worktree['path'] if process_worktree else repo),'stdout':subprocess.PIPE,'stderr':subprocess.PIPE,'text':True,'encoding':'utf-8','errors':'replace','bufsize':1}
            if os.name=='nt':opts['creationflags']=subprocess.CREATE_NO_WINDOW
            proc=subprocess.Popen(args,**opts)
            update(run_id,status='running',pid=proc.pid,process=proc)
            def stream(pipe,kind):
                for line in pipe:
                    line=line.strip()
                    if not line:continue
                    if kind=='stdout':
                        try: log_event(run_id,{'kind':'codex','payload':json.loads(line)})
                        except ValueError: log_event(run_id,{'kind':'text','message':line[:5000]})
                    else: log_event(run_id,{'kind':'stderr','message':line[:5000]})
                pipe.close()
            a=threading.Thread(target=stream,args=(proc.stdout,'stdout'),daemon=True);a.start()
            b=threading.Thread(target=stream,args=(proc.stderr,'stderr'),daemon=True);b.start()
            rc=proc.wait();a.join(timeout=3);b.join(timeout=3)
            with LOCK:
                cancelled=RUNS[run_id]['status']=='cancelling'
            update(run_id,status='cancelled' if cancelled else 'finished' if rc==0 else 'failed',exit_code=rc,ended=now(),process=None)
        except Exception as exc:
            log_event(run_id,{'kind':'error','message':str(exc)})
            update(run_id,status='failed',ended=now(),process=None)
        finally:
            release_process_lock(process_lock_handle)
            if staging: shutil.rmtree(staging,ignore_errors=True)
    try:
        threading.Thread(target=worker,daemon=True).start()
    except Exception:
        release_process_lock(process_lock_handle)
        raise
    return run_id

class Handler(BaseHTTPRequestHandler):
    repo=ROOT
    def respond(self, code, obj):
        content=json.dumps(obj,ensure_ascii=False,default=str).encode()
        self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
    def raw_body(self, limit=1024*1024):
        n=int(self.headers.get('Content-Length','0'))
        if n>limit: raise ValueError('Payload too large')
        return self.rfile.read(n)
    def body(self):
        return json.loads(self.raw_body() or b'{}')
    def multipart(self):
        raw=self.raw_body(MAX_FEEDBACK_UPLOAD+1024*1024)
        content_type=self.headers.get('Content-Type','').encode('ascii','strict')
        message=BytesParser(policy=email_policy).parsebytes(
            b'MIME-Version: 1.0\r\nContent-Type: '+content_type+b'\r\n\r\n'+raw)
        if not message.is_multipart(): raise ValueError('Invalid multipart form data')
        fields={};uploads=[]
        for part in message.iter_parts():
            name=part.get_param('name',header='content-disposition')
            if not name: continue
            payload=part.get_payload(decode=True) or b''
            filename=part.get_filename()
            if filename is not None:
                if payload: uploads.append((filename,payload))
            else:
                fields[name]=payload.decode(part.get_content_charset() or 'utf-8','replace')
        return fields,uploads
    def do_GET(self):
        if not local_request_allowed(self.headers, self.server.server_port):
            return self.respond(403, {'error':'Local requests only'})
        path=unquote(urlparse(self.path).path)
        if path=='/api/repos':
            with LOCK:
                repos=[{'id':key,'path':str(value),'name':value.name or str(value)} for key,value in REPOSITORIES.items()]
                requested=parse_qs(urlparse(self.path).query).get('repo',[DEFAULT_REPO_ID])[0]
                selected=requested if requested in REPOSITORIES else DEFAULT_REPO_ID
            return self.respond(200,{'repos':repos,'selected':selected})
        if path=='/api/browse':
            try:
                folder=choose_repository_folder()
                return self.respond(200,{'path':folder})
            except Exception as exc:
                return self.respond(501,{'error':f'Native folder picker is unavailable ({exc}). Enter the folder path instead.'})
        try: repo,selected_id=selected_repository(self)
        except ValueError as exc: return self.respond(400,{'error':str(exc)})
        if path=='/api/overview':
            r=runs_for_repository(selected_id)
            ticket_summaries=tickets(repo)
            return self.respond(200,{'repo':str(repo),'repo_id':selected_id,'tickets':ticket_summaries,'active_tickets':active_ticket_count(ticket_summaries),'runs':r})
        if path.startswith('/api/tickets/'):
            tid=path.split('/')[-1];d=detail(repo,tid)
            return self.respond(200,d) if d else self.respond(404,{'error':'Ticket not found'})
        if path.startswith('/api/runs/'):
            rid=path.split('/')[-1]
            with LOCK:
                r=RUNS.get(rid)
                data={k:v for k,v in r.items() if k!='process'} if r and r.get('repo_id')==selected_id else None
            return self.respond(200,data) if data else self.respond(404,{'error':'Run not found'})
        if path=='/' or path=='/index.html':
            p=ROOT/'public'/'index.html';b=p.read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(b)));self.end_headers();return self.wfile.write(b)
        asset=public_asset(path)
        if asset:
            p,content_type=asset;b=p.read_bytes();self.send_response(200);self.send_header('Content-Type',content_type);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(b)));self.end_headers();return self.wfile.write(b)
        return self.respond(404,{'error':'Not found'})
    def do_POST(self):
        if not local_request_allowed(self.headers, self.server.server_port):
            return self.respond(403, {'error':'Local requests only'})
        path=urlparse(self.path).path
        if path=='/api/repos':
            try:
                data=self.body();item=add_repository(str(data.get('path','')).strip())
                return self.respond(201,item)
            except (ValueError,TypeError,OSError) as exc:return self.respond(400,{'error':str(exc)})
        try: repo,selected_id=selected_repository(self)
        except ValueError as exc: return self.respond(400,{'error':str(exc)})
        if path.startswith('/api/tickets/') and path.endswith('/reject'):
            if not self.headers.get('Content-Type','').lower().startswith('multipart/form-data'):
                return self.respond(415, {'error':'Content-Type must be multipart/form-data'})
            try:
                fields,uploads=self.multipart()
                tid=unquote(path[len('/api/tickets/'):-len('/reject')].strip('/'))
                result=reject_ticket(repo,tid,fields.get('description',''),uploads)
                try:
                    result['run_id']=spawn_codex(repo,tid,'process',repo_id=selected_id)
                    result['message']+=f" · Correction run {result['run_id']} started."
                except (RuntimeError,ValueError) as exc:
                    result['run_id']=None
                    result['message']+=f' · Reopened, but Codex could not start: {exc}'
                return self.respond(202 if result['run_id'] else 200,result)
            except (ValueError,TypeError) as exc:return self.respond(400,{'error':str(exc)})
            except RuntimeError as exc:return self.respond(409,{'error':str(exc)})
        try:
            content_type=self.headers.get('Content-Type','').lower()
            if path=='/api/run' and content_type.startswith('multipart/form-data'):
                fields,uploads=self.multipart()
                mode=fields.get('mode')
                if mode!='create':raise ValueError('Multipart uploads are only supported for ticket creation')
                try: attachment_paths=json.loads(fields.get('attachment_paths','[]'))
                except json.JSONDecodeError as exc:raise ValueError('Invalid local attachment paths') from exc
                if not isinstance(attachment_paths,list) or any(not isinstance(item,str) for item in attachment_paths):
                    raise ValueError('Local attachment paths must be a list of strings')
                rid=spawn_codex(repo,'','create',str(fields.get('description','')),attachment_paths,repo_id=selected_id,uploads=uploads)
                return self.respond(202,{'run_id':rid})
            if not content_type.startswith('application/json'):
                return self.respond(415, {'error':'Content-Type must be application/json'})
            data=self.body()
            if path=='/api/run':
                mode=data.get('mode');tid=str(data.get('ticket_id',''))
                if mode not in ('create','process'):raise ValueError('Invalid mode')
                rid=spawn_codex(repo,tid,mode,str(data.get('description','')),data.get('attachments',[]),repo_id=selected_id)
                return self.respond(202,{'run_id':rid})
            if path.startswith('/api/tickets/') and path.endswith('/complete'):
                tid=unquote(path[len('/api/tickets/'):-len('/complete')].strip('/'))
                return self.respond(200,complete_ticket(repo,tid))
            if path.startswith('/api/stop/'):
                rid=path.split('/')[-1]
                with LOCK:
                    run=RUNS.get(rid)
                    if run and run.get('repo_id')!=selected_id: run=None
                    proc=run.get('process') if run else None
                    if proc and proc.poll() is None: run['status']='cancelling'
                if not proc or proc.poll() is not None:raise ValueError('Run is not active')
                # terminate the CLI process; descendant processes may require manual cleanup
                proc.terminate()
                return self.respond(200,{'message':'Termination requested. Check for child processes.'})
            return self.respond(404,{'error':'Not found'})
        except (ValueError,TypeError) as exc:return self.respond(400,{'error':str(exc)})
        except RuntimeError as exc:return self.respond(409,{'error':str(exc)})
    def log_message(self,*args):pass

def main():
    ap=argparse.ArgumentParser(description='Local Codex ticket dashboard')
    ap.add_argument('--repo',action='append',required=True,help='Repository folder (repeat to connect multiple repositories)')
    ap.add_argument('--port',type=int,default=8765)
    args=ap.parse_args()
    try:
        for path in args.repo: add_repository(path)
    except ValueError as exc: ap.error(str(exc))
    global DEFAULT_REPO_ID
    DEFAULT_REPO_ID=next(iter(REPOSITORIES))
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Dashboard: http://127.0.0.1:{args.port}\nRepositories: {len(REPOSITORIES)}\nLocal only. Ctrl+C to stop.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt: pass
    finally:server.server_close()
if __name__=='__main__':main()
