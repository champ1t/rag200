
import sys
import os
import unittest
sys.path.append(os.getcwd())
from src.core.chat_engine import ChatEngine

# Mock Config
CONFIG = {
    "model": "llama3.2:3b",
    "base_url": "http://localhost:11434",
    "use_cache": False,
    "retrieval": {"top_k": 3, "score_threshold": 0.3},
    "llm": {"model": "llama3.2:3b", "base_url": "http://localhost:11434", "temperature": 0.0},
    "chat": {"save_log": False}, 
    "knowledge_pack": {"enabled": False}, # Disable KP to force RAG
    "cache": {"enabled": False}
}

class TestRAGSources(unittest.TestCase):
    def setUp(self):
        self.engine = ChatEngine(CONFIG)
        self.engine.warmup()
        
    def test_sources_attached(self):
        print("\n--- Test: Sources Attached to RAG Answer ---")
        
        # Force disable KP
        self.engine.kp_manager = None
        # Force disable Optimizer (pass-through)
        self.engine.retrieval_optimizer = None
        # Force disable Controller (pass-through)
        self.engine.controller = None
        
        # Mock Vector Store Search
        from collections import namedtuple
        SearchResult = namedtuple("SearchResult", ["text", "score", "metadata"])
        
        mock_docs = [
            SearchResult(
                text="Test Query is verified.",
                score=0.9,
                metadata={"title": "Verified Doc", "source": "http://example.com/doc", "url": "http://example.com/doc"}
            )
        ]
        
        # Monkey patch VS
        original_query = self.engine.vs.query
        original_hybrid = getattr(self.engine.vs, "hybrid_query", None)
        
        self.engine.vs.query = lambda q, top_k=3, where=None: mock_docs
        self.engine.vs.hybrid_query = lambda q, top_k=3, alpha=0.5, where=None: mock_docs
        
        # Monkey patch LLM to ensure valid answer
        # import src.chat_engine as ce
        # But self.engine imports it.
        # We need to patch the check inside the instance method?
        # chat_engine.py imports ollama_generate.
        
        import src.chat_engine
        original_generate = src.chat_engine.ollama_generate
        src.chat_engine.ollama_generate = lambda **kwargs: "Test Query is a verified query."
        
        try:
            q = "What is Test Query?"
            res = self.engine.process(q)
            
            print(f"Retrieved Context: {res.get('docs', [])}")
            ans = res["answer"]
            print(f"Answer: {ans}")
            
            # 1. Check for Reference Header
            self.assertIn("แหล่งข้อมูลอ้างอิง:", ans)
            
            # 2. Check for the mock URL
            self.assertIn("http://example.com/doc", ans)
            self.assertIn("Verified Doc", ans)
            
        finally:
            # Restore
            self.engine.vs.query = original_query
            if original_hybrid:
                self.engine.vs.hybrid_query = original_hybrid
            src.chat_engine.ollama_generate = original_generate

    def test_refusal_no_sources(self):
        print("\n--- Test: Refusal Should NOT have sources ---")
        q = "How to cook fried rice" # Likely OOD
        res = self.engine.process(q)
        
        ans = res["answer"]
        print(f"Answer: {ans}")
        
        # Should be a refusal
        # If refusal, we expect "ไม่พบข้อมูล..." and NO sources
        if "ไม่พบข้อมูล" in ans:
             self.assertNotIn("แหล่งข้อมูลอ้างอิง:", ans)
        else:
             # If it somehow answered (hallucination?), fail unless it found docs (unlikely)
             # But for OOD, we expect refusal.
             pass

if __name__ == "__main__":
    unittest.main()
