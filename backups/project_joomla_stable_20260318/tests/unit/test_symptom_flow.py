
import sys
import unittest
# We need to test the logic flow, but ChatEngine has many dependencies.
# We will use the same approach as test_procedural_logic.py:
# Instantiate ChatEngine (with mocks if possible or real load) and trace context.

# Since instantiation takes time and resources, let's try to verify the LOGIC blocks via careful unit testing if possible,
# or run a script that patches the parts we don't need.
# Actually, the user has a running ChatEngine in 'main'.
# Let's write a script that imports 'main' or 'ChatEngine' and runs a minimal session.

from src.core.chat_engine import ChatEngine
import shutil

class TestSymptomFollowup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We assume data is present.
        # Minimal config
        cfg = {
            "retrieval": {"top_k": 3},
            "llm": {"model": "placeholder", "base_url": "http://localhost:11434"},
            "chat": {"show_context": False, "save_log": False},
            "rag": {"use_cache": False} # Disable cache to avoid creating files
        }
        # This might fail if vectorstore / redis are hard requirements in init
        # But let's try.
        try:
            cls.engine = ChatEngine(cfg)
            # Mock complex components?
            # We only need 'process' and 'proc_ctx' logic.
            # But process calls everything.
            # We can mock `_decide_route` or internal calls if needed.
        except Exception as e:
            print(f"Engine init failed: {e}")
            cls.engine = None

    def test_internet_flow(self):
        if not self.engine:
            self.skipTest("Engine not initialized")
            
        print("\n--- Test 1. Trigger Internet Context ---")
        # 1. Trigger Internet Issue
        q1 = "เน็ตเสียครับ"
        res1 = self.engine.process(q1)
        print(f"Q: {q1}")
        print(f"A: {res1['answer']}")
        print(f"Route: {res1['route']}")
        
        self.assertIn("rag_clarify", res1['route'])
        self.assertIsNotNone(self.engine.proc_ctx)
        self.assertEqual(self.engine.proc_ctx['topic'], "internet")
        
        print("\n--- Test 2. Partial Answer (Symptom only) ---")
        # 2. Answer with symptom only
        q2 = "หลุดบ่อยมาก"
        res2 = self.engine.process(q2)
        print(f"Q: {q2}")
        print(f"A: {res2['answer']}")
        print(f"Route: {res2['route']}")
        
        # Should ask for Access Type (WiFi/LAN)
        self.assertIn("Wi-Fi หรือสาย LAN", res2['answer'])
        self.assertEqual(self.engine.proc_ctx['slots']['symptom'], "disconnnect")
        
        print("\n--- Test 3. Complete Answer (Access Type) ---")
        # 3. Answer with access type
        q3 = "ใช้ wifi ครับ"
        # This should trigger full resolution logic inside process()
        # It updates context, sees slots are full, auto-generates query, and falls through.
        # Likely it will hit RAG or Article Answer.
        # Since we use placeholder model, RAG might return something generic or 'ไม่พบข้อมูล'.
        # But let's check the trace or just the fact that it didn't stay in 'rag_clarify_followup'.
        
        # NOTE: Since we don't have a real LLM connected in this env maybe, 
        # or the mocks are limited, it might fail inside RAG.
        # But we care about the LOGIC flow.
        
        res3 = self.engine.process(q3)
        print(f"Q: {q3}")
        print(f"Route: {res3['route']}")
        
        # Route should NOT be rag_clarify_followup anymore
        self.assertNotEqual(res3['route'], "rag_clarify_followup")
        # Context should be cleared
        self.assertIsNone(self.engine.proc_ctx) 
        
        print("\n✅ Flow Verified Successfully")

if __name__ == '__main__':
    unittest.main()
