
import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.getcwd())
try:
    from src.chat_engine import ChatEngine
    from src.ai.router import IntentRouter
except ImportError:
    pass

CONFIG = {
    "model": "mock",
    "base_url": "mock",
    "retrieval": {"top_k": 1, "score_threshold": 0.5},
    "llm": {"model": "mock", "base_url": "mock"},
    "chat": {"save_log": False},
    "knowledge_pack": {"enabled": False},
    "cache": {"enabled": False}
}

class TestPhase34Part2(unittest.TestCase):
    def setUp(self):
        self.engine = ChatEngine(CONFIG)
        self.engine.warmup()
        # Mock Position Index (Role -> List of People)
        self.engine.position_index = {
            "งาน FTTx": [
                {"role": "งาน FTTx", "name": "นาย ก.", "source": "test"},
                {"role": "งาน FTTx", "name": "นาย ข.", "source": "test"}
            ],
            "admin": [
                {"role": "admin", "name": "Admin User", "source": "test"}
            ]
        }
        
    def test_router_member_keyword(self):
        print("\n--- Test: Router Member Keywords ---")
        router = IntentRouter()
        
        # Test "สมาชิก"
        res = router.route("สมาชิกงาน FTTx")
        self.assertEqual(res["intent"], "PERSON_LOOKUP")
        
        # Test "ทีม"
        res = router.route("ทีมงาน FTTx")
        self.assertEqual(res["intent"], "PERSON_LOOKUP")
        
        # Test "เจ้าหน้าที่"
        res = router.route("ขอเบอร์เจ้าหน้าที่ admin")
        self.assertEqual(res["intent"], "PERSON_LOOKUP")

    def test_chat_engine_fttx_lookup(self):
        print("\n--- Test: Chat Engine FTTx Lookup ---")
        # "สมาชิกงาน FTTx" shoud trigger PERSON_LOOKUP -> Position Index Lookup
        
        res = self.engine.process("สมาชิกงาน FTTx")
        print(f"Route: {res.get('route')}")
        print(f"Answer: {res.get('answer')}")
        
        self.assertEqual(res.get("route"), "position_lookup")
        self.assertIn("นาย ก.", res.get("answer"))
        self.assertIn("นาย ข.", res.get("answer"))

if __name__ == "__main__":
    unittest.main()
