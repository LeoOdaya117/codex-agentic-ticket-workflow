import tempfile, unittest, json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import tickets, detail, find_ticket_dir, local_request_allowed, active_ticket_count
class TestTicketReading(unittest.TestCase):
    def test_active_ticket_count_uses_ticket_status_not_dashboard_runs(self):
        self.assertEqual(active_ticket_count([
            {'status':'Implementing'}, {'status':'QA Testing'},
            {'status':'Ready for Human Verification'}, {'status':'Blocked'},
        ]), 2)
    def test_read_and_progress(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'tickets'/'TKT-0001';p.mkdir(parents=True)
            (p/'ticket.md').write_text('# TKT-0001 — Fix login\n**Status:** Planning\n**Priority:** High\n- [x] first\n- [ ] next',encoding='utf-8')
            (p/'qa-report.md').write_text('Not run',encoding='utf-8')
            self.assertEqual(tickets(Path(t))[0]['checked'],1)
            self.assertEqual(tickets(Path(t))[0]['total'],2)
            self.assertEqual(tickets(Path(t))[0]['priority'],'High')
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
if __name__=='__main__':unittest.main()
