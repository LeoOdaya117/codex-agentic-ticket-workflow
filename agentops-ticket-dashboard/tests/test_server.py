import tempfile, unittest, json, shutil, subprocess
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server as dashboard_server
from server import ROOT, tickets, detail, find_ticket_dir, local_request_allowed, active_ticket_count, complete_ticket, reject_ticket, public_asset, add_repository, REPOSITORIES, repository_id, runs_for_repository, stage_create_uploads, ensure_ticket_worktree, acquire_process_lock, release_process_lock, MAX_FEEDBACK_UPLOAD, MAX_FEEDBACK_FILES
class TestTicketReading(unittest.TestCase):
    def test_process_lock_prevents_duplicate_ticket_runs(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'.locks'/'TKT-0001.lock'
            held=acquire_process_lock(path)
            try:
                with self.assertRaisesRegex(ValueError,'already active'):
                    acquire_process_lock(path)
            finally:
                release_process_lock(held)
            released=acquire_process_lock(path)
            release_process_lock(released)

    @unittest.skipUnless(shutil.which('git'),'Git is required for worktree tests')
    def test_ticket_worktrees_isolate_concurrent_tickets_and_resume_by_ticket(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as t:
            repo=Path(t)/'sample repo';repo.mkdir()
            def git(*args):
                return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,
                                      text=True,encoding='utf-8',errors='replace').stdout.strip()
            git('init')
            git('config','user.name','AgentOps Test')
            git('config','user.email','agentops-test@example.invalid')
            (repo/'tracked.txt').write_text('baseline\n',encoding='utf-8')
            git('add','tracked.txt');git('commit','-m','baseline');git('checkout','-b','main')
            first=ensure_ticket_worktree(repo,'TKT-0001')
            second=ensure_ticket_worktree(repo,'TKT-0002')
            self.assertNotEqual(first['path'],second['path'])
            self.assertNotEqual(first['branch'],second['branch'])
            self.assertEqual(first['branch'],'codex/TKT-0001')
            self.assertEqual(second['branch'],'codex/TKT-0002')
            self.assertEqual(first['head_commit'],second['head_commit'])
            (first['path']/'ticket-change.txt').write_text('one ticket only\n',encoding='utf-8')
            resumed=ensure_ticket_worktree(repo,'TKT-0001')
            self.assertTrue(resumed['resumed'])
            self.assertEqual(resumed['path'],first['path'])
            self.assertTrue((resumed['path']/'ticket-change.txt').is_file())
            self.assertFalse((second['path']/'ticket-change.txt').exists())

    def test_create_uploads_are_staged_inside_repo_with_safe_unique_names(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t)
            staging,paths=stage_create_uploads(repo,[
                ('../screen shot.png',b'first'),
                ('screen shot.png',b'second'),
            ])
            self.assertTrue(staging.is_relative_to(repo.resolve()))
            self.assertEqual([Path(path).name for path in paths],['screen_shot.png','screen_shot-2.png'])
            self.assertEqual([Path(path).read_bytes() for path in paths],[b'first',b'second'])
            import shutil
            shutil.rmtree(staging)
    def test_create_upload_limits_are_enforced(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError,'no more than 10'):
                stage_create_uploads(t,[(f'{i}.txt',b'x') for i in range(MAX_FEEDBACK_FILES+1)])
            with self.assertRaisesRegex(ValueError,'20 MB or less'):
                stage_create_uploads(t,[('large.bin',b'x'*(MAX_FEEDBACK_UPLOAD+1))])
            self.assertEqual(list(Path(t).iterdir()),[])
    def test_repositories_can_be_registered_and_have_stable_ids(self):
        original=REPOSITORIES.copy()
        with tempfile.TemporaryDirectory() as t:
            try:
                repo=Path(t)
                item=add_repository(repo)
                self.assertEqual(item['id'],repository_id(repo))
                self.assertEqual(Path(item['path']),repo.resolve())
                self.assertEqual(REPOSITORIES[item['id']],repo.resolve())
                with self.assertRaisesRegex(ValueError,'Enter a repository folder path'):
                    add_repository(' ')
                with self.assertRaisesRegex(ValueError,'Folder does not exist'):
                    add_repository(repo/'missing')
            finally:
                REPOSITORIES.clear()
                REPOSITORIES.update(original)
    def test_ticket_and_run_scoping_follow_repository(self):
        original=REPOSITORIES.copy()
        with tempfile.TemporaryDirectory() as t:
            try:
                repos=[]
                for name in ('alpha','beta'):
                    repo=Path(t)/name;ticket=repo/'tickets'/'TKT-0001';ticket.mkdir(parents=True)
                    (ticket/'ticket.md').write_text(f'# {name}',encoding='utf-8')
                    repos.append(add_repository(repo))
                with dashboard_server.LOCK:
                    dashboard_server.RUNS['test-run-alpha']={'id':'test-run-alpha','repo_id':repos[0]['id'],'events':[],'process':None}
                    dashboard_server.RUNS['test-run-beta']={'id':'test-run-beta','repo_id':repos[1]['id'],'events':[],'process':None}
                for repo,name,run_id in zip(repos,('alpha','beta'),('test-run-alpha','test-run-beta')):
                    self.assertEqual(tickets(Path(repo['path']))[0]['title'],name)
                    self.assertEqual([run['id'] for run in runs_for_repository(repo['id'])],[run_id])
                    self.assertNotIn('events',runs_for_repository(repo['id'])[0])
            finally:
                with dashboard_server.LOCK:
                    dashboard_server.RUNS.pop('test-run-alpha',None)
                    dashboard_server.RUNS.pop('test-run-beta',None)
                REPOSITORIES.clear();REPOSITORIES.update(original)
    def test_active_ticket_count_uses_ticket_status_not_dashboard_runs(self):
        self.assertEqual(active_ticket_count([
            {'status':'Implementing'}, {'status':'QA Testing'},
            {'status':'Ready for Human Verification'}, {'status':'Blocked'},
        ]), 2)
    def test_read_and_progress(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'tickets'/'TKT-0001';p.mkdir(parents=True)
            (p/'ticket.md').write_text('# TKT-0001 — Fix login\n**Status:** Planning\n**Priority:** High\n- [x] first\n- [ ] next\n\n## Delivery\n- Pull request: https://github.com/example/repo/pull/1',encoding='utf-8')
            (p/'qa-report.md').write_text('Not run',encoding='utf-8')
            self.assertEqual(tickets(Path(t))[0]['checked'],1)
            self.assertEqual(tickets(Path(t))[0]['total'],2)
            self.assertEqual(tickets(Path(t))[0]['priority'],'High')
            self.assertEqual(tickets(Path(t))[0]['pull_request'],'https://github.com/example/repo/pull/1')
            self.assertEqual(detail(Path(t),'TKT-0001')['files']['qa-report.md'],'Not run')
    def test_priority_in_markdown_list_item(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'tickets'/'TKT-0003';p.mkdir(parents=True)
            (p/'ticket.md').write_text('# Three\n- Priority: P2 (proposed; triage required)',encoding='utf-8')
            self.assertEqual(tickets(Path(t))[0]['priority'],'P2 (proposed; triage required)')
    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as t:self.assertIsNone(find_ticket_dir(Path(t),'../secret'))
    def test_codex_folder_supported(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'.codex'/'tickets'/'TKT-0002';p.mkdir(parents=True)
            (p/'ticket.md').write_text('# Two',encoding='utf-8')
            self.assertEqual(tickets(Path(t))[0]['id'],'TKT-0002')
    def test_local_request_policy(self):
        self.assertTrue(local_request_allowed({'Host':'127.0.0.1:8765','Origin':'http://127.0.0.1:8765'},8765))
        self.assertTrue(local_request_allowed({'Host':'localhost:8765'},8765))
        self.assertFalse(local_request_allowed({'Host':'127.0.0.1:8765','Origin':'https://example.com'},8765))
        self.assertFalse(local_request_allowed({'Host':'attacker.example:8765'},8765))
    def test_public_assets_are_allowlisted_and_stay_in_dashboard_public_dir(self):
        for path, filename in [('/styles.css', 'styles.css'), ('/theme.js', 'theme.js'), ('/app.js', 'app.js')]:
            asset = public_asset(path)
            self.assertIsNotNone(asset)
            self.assertEqual(asset[0].name, filename)
            self.assertTrue(asset[0].is_file())
            self.assertTrue(asset[0].is_relative_to(ROOT/'public'))
        self.assertIsNone(public_asset('/../server.py'))
        self.assertIsNone(public_asset('/unknown.js'))
    def test_complete_requires_human_verification_status(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t);ticket=repo/'tickets'/'TKT-0001';ticket.mkdir(parents=True)
            (ticket/'ticket.md').write_text('# Test',encoding='utf-8')
            (ticket/'state.json').write_text(json.dumps({'status':'Implementing'}),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'not Ready for Human Verification'):
                complete_ticket(repo,'TKT-0001')
            self.assertFalse((ticket/'verification.md').exists())
    def test_complete_records_explicit_approval_and_uses_state_tool(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t);ticket=repo/'tickets'/'TKT-0001';ticket.mkdir(parents=True)
            (ticket/'ticket.md').write_text('# Test',encoding='utf-8')
            (ticket/'state.json').write_text(json.dumps({'status':'Ready for Human Verification'}),encoding='utf-8')
            tool=repo/'.codex'/'ticketing'/'ticket.py';tool.parent.mkdir(parents=True)
            tool.write_text("import json,sys\nfrom pathlib import Path\np=Path('tickets/TKT-0001/state.json')\ns=json.loads(p.read_text())\nassert sys.argv[1:]==['set-status','TKT-0001','Done','--human-approved']\ns['status']='Done'\np.write_text(json.dumps(s))\nprint('TKT-0001: Ready for Human Verification -> Done')\n",encoding='utf-8')
            result=complete_ticket(repo,'TKT-0001')
            self.assertIn('-> Done',result['message'])
            self.assertIn('Approved via the AgentOps dashboard',(ticket/'verification.md').read_text(encoding='utf-8'))
            self.assertEqual(json.loads((ticket/'state.json').read_text(encoding='utf-8'))['status'],'Done')
            self.assertIn('verification.md',detail(repo,'TKT-0001')['files'])
    def test_reject_requires_human_verification_and_feedback(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t);ticket=repo/'tickets'/'TKT-0001';ticket.mkdir(parents=True)
            (ticket/'ticket.md').write_text('# Test',encoding='utf-8')
            (ticket/'state.json').write_text(json.dumps({'status':'Implementing'}),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'not Ready for Human Verification'):
                reject_ticket(repo,'TKT-0001','Needs polish')
            (ticket/'state.json').write_text(json.dumps({'status':'Ready for Human Verification'}),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Describe what needs correction'):
                reject_ticket(repo,'TKT-0001','  ')
            self.assertFalse((ticket/'verification.md').exists())
    def test_reject_records_feedback_saves_files_and_reopens_ticket(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t);ticket=repo/'tickets'/'TKT-0001';ticket.mkdir(parents=True)
            (ticket/'ticket.md').write_text('# Test',encoding='utf-8')
            (ticket/'state.json').write_text(json.dumps({'status':'Ready for Human Verification'}),encoding='utf-8')
            tool=repo/'.codex'/'ticketing'/'ticket.py';tool.parent.mkdir(parents=True)
            tool.write_text("import json,sys\nfrom pathlib import Path\nassert sys.argv[1:]==['set-status','TKT-0001','Implementing']\np=Path('tickets/TKT-0001/state.json')\ns=json.loads(p.read_text())\ns['status']='Implementing'\np.write_text(json.dumps(s))\nprint('TKT-0001: Ready for Human Verification -> Implementing')\n",encoding='utf-8')
            result=reject_ticket(repo,'TKT-0001','The layout still clips the label.',[
                ('../label screenshot.png',b'image-evidence'),
            ])
            self.assertIn('-> Implementing',result['message'])
            self.assertEqual(result['attachments'],['attachments/label_screenshot.png'])
            self.assertEqual((ticket/'attachments'/'label_screenshot.png').read_bytes(),b'image-evidence')
            verification=(ticket/'verification.md').read_text(encoding='utf-8')
            self.assertIn('Decision: Rejected',verification)
            self.assertIn('The layout still clips the label.',verification)
            self.assertIn('attachments/label_screenshot.png',verification)
            self.assertEqual(json.loads((ticket/'state.json').read_text(encoding='utf-8'))['status'],'Implementing')
if __name__=='__main__':unittest.main()
