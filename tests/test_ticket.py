import sys, unittest
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
 def test_template(self):
  content=(ticket.TEMPLATES/'ticket.md').read_text()
  self.assertIn('{id}',content)
if __name__=='__main__': unittest.main()
