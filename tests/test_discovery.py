import sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.codex'/'ticketing'))
import discover
class TestDiscovery(unittest.TestCase):
 def test_existing_agent_and_skill(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'.agents/skills/team-qa').mkdir(parents=True)
   (root/'.agents/skills/team-qa/SKILL.md').write_text('description: QA regression testing\n')
   (root/'.codex/agents').mkdir(parents=True)
   (root/'.codex/agents/frontend.toml').write_text('description = "React frontend components"\n')
   (root/'.codex/config.toml').write_text('[agents.frontend]\ndescription="frontend"\n')
   result=discover.inspect(root)
   self.assertTrue(any(x['name']=='team-qa' for x in result['by_role']['qa']))
   self.assertTrue(any(x['name']=='frontend' and x['registered'] for x in result['by_role']['frontend']))
if __name__=='__main__':unittest.main()
