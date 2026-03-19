import yaml
import json
import unittest
from src.core.chat_engine import ChatEngine
from src.rag.handlers.directory_handler import DirectoryHandler
from src.utils.normalization import normalize_for_matching

class TestTeamLookup(unittest.TestCase):
    def test_lookup_supervisor(self):
        print("\n=== DEBUG: Test Team Lookup ===")
        # 1. Load Teams
        teams = []
        with open("data/records/teams.jsonl", "r") as f:
            for line in f:
                if line.strip():
                    teams.append(json.loads(line))
        
        team_index = {}
        for t in teams:
            team_index[t["team"]] = t
            
        print(f"Loaded {len(team_index)} teams.")
        
        # 2. Init Handler
        handler = DirectoryHandler({}, [], team_index)
        
        # 3. Check Norm Map
        print("Team Norm Map Keys:", handler.team_norm_map.keys())
        
        # 4. Check Normalization
        q = "Supervisor Agent"
        q_norm = normalize_for_matching(q)
        print(f"Query: '{q}' -> Norm: '{q_norm}'")
        
        # 5. Perform Lookup
        res = handler.handle_team_lookup(q)
        print("Result Route:", res.get("route"))
        print("Result Hits:", len(res.get("hits", [])))
        
        if not res.get("hits"):
            print("Answer:", res.get("answer"))

if __name__ == "__main__":
    unittest.main()
