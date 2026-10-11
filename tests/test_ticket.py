import argparse, json, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.codex'/'ticketing'))
import ticket
class TestTicket(unittest.TestCase):
 def test_transitions(self):
  self.assertIn('Planning',ticket.NEXT['Investigating'])
  self.assertNotIn('Done',ticket.NEXT['Open'])
 def test_id_validation(self):
  with self.assertRaises(ValueError):ticket.directory('../../etc')
 def test_explicit_ticket_directory_is_supported_for_worktrees(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as temp:
   folder=Path(temp)/'TKT-0007';folder.mkdir()
   (folder/'state.json').write_text(json.dumps({'id':'TKT-0007','status':'Open','history':[]}),encoding='utf-8')
   self.assertEqual(ticket.load('TKT-0007',str(folder))[0],folder.resolve())
   with self.assertRaisesRegex(ValueError,'must point to the TKT-0007 directory'):
    ticket.ticket_directory('TKT-0007',str(Path(temp)/'wrong'))
 def test_ready_for_human_verification_requires_commit_branch_worktree_and_pr(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as temp:
   folder=Path(temp)/'TKT-0007';folder.mkdir()
   (folder/'state.json').write_text(json.dumps({'id':'TKT-0007','status':'QA Testing','history':[]}),encoding='utf-8')
   (folder/'ticket.md').write_text('# TKT-0007\n',encoding='utf-8')
   (folder/'qa-report.md').write_text('Result: PASS\n\n## Executed commands\n\n`python -m unittest` exited 0. This test fixture contains enough recorded command, exit-code, environment, and outcome detail to satisfy the lifecycle metadata guard. The test does not execute or assert any project QA result.\n',encoding='utf-8')
   args=argparse.Namespace(id='TKT-0007',status='Ready for Human Verification',ticket_dir=str(folder),qa_pass=True,human_approved=False)
   with self.assertRaisesRegex(ValueError,'branch, worktree, commit SHA, pull request URL'):
    ticket.status(args)
   (folder/'ticket.md').write_text(
    '# TKT-0007\n\n## Delivery\n- Branch: codex/TKT-0007\n- Worktree: D:/repo-worktrees/TKT-0007\n- Commit SHA: 1234567890abcdef\n- Pull request: https://github.com/example/repo/pull/7\n',encoding='utf-8')
   ticket.status(args)
   self.assertEqual(json.loads((folder/'state.json').read_text(encoding='utf-8'))['status'],'Ready for Human Verification')
 def test_template(self):
  content=(ticket.TEMPLATES/'ticket.md').read_text()
  self.assertIn('{id}',content)
if __name__=='__main__': unittest.main()
