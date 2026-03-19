
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
    "knowledge_pack": {"enabled": True},
    "cache": {"enabled": False}
}

class TestPhase34(unittest.TestCase):
    def setUp(self):
        self.engine = ChatEngine(CONFIG)
        self.engine.warmup()
        # Mock KP logic to avoid calls/errors
        self.engine.kp_manager = MagicMock()
        self.engine.kp_manager.lookup.return_value = None
        
    def test_router_classification(self):
        print("\n--- Test: Intent Classification ---")
        router = IntentRouter()
        
        # Test Person
        res = router.route("ขอเบอร์ Somchai")
        self.assertEqual(res["intent"], "PERSON_LOOKUP")
        
        # Test Status
        res = router.route("ระบบล่มไหม")
        self.assertEqual(res["intent"], "STATUS_CHECK")
        
        # Test HowTo
        res = router.route("ตั้งค่า DNS อย่างไร")
        self.assertEqual(res["intent"], "HOWTO_PROCEDURE")
        
        # Test Ref
        res = router.route("ขอลิงก์แบบฟอร์ม")
        self.assertEqual(res["intent"], "REFERENCE_LOOKUP")
        
    def test_status_gate(self):
        print("\n--- Test: Status Check Gating ---")
        # Should return immediate "No Realtime Data" msg without doing lookup
        res = self.engine.process("ระบบล่มไหม")
        print(f"Status Ans: {res['answer']}")
        self.assertIn("ไม่พบข้อมูลสถานะ", res['answer'])
        self.assertEqual(res["route"], "status_check_mock")
        
    def test_position_gate(self):
        print("\n--- Test: Position Lookup Gating ---")
        # Mock position index
        self.engine.position_index = {"tester": [{"role": "tester", "name": "Test Man", "source": "test"}]}
        
        # 1. Query matching intent PERSON -> Should find
        res1 = self.engine.process("ติดต่อ tester")
        self.assertEqual(res1.get("route"), "position_lookup")
        
        # 2. Query matching intent HOWTO -> Should NOT find even if 'tester' is in text
        # "วิธี config tester" -> HowTo
        res2 = self.engine.process("วิธี config tester")
        self.assertNotEqual(res2.get("route"), "position_lookup")
        
if __name__ == "__main__":
    unittest.main()
