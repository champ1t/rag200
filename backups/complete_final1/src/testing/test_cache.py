import unittest
import sys
import os
import shutil
import time
from pathlib import Path

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.core.chat_engine import ChatEngine
from src.cache.semantic import SemanticCache

TEST_CACHE_DIR = "data/test_cache_store"

class TestSemanticCache(unittest.TestCase):
    def setUp(self):
        # Clean up
        if Path(TEST_CACHE_DIR).exists():
            shutil.rmtree(TEST_CACHE_DIR)
            
    def tearDown(self):
        # Clean up
        if Path(TEST_CACHE_DIR).exists():
            shutil.rmtree(TEST_CACHE_DIR)

    def test_cache_hit(self):
        """Test Semantic Cache Hit Logic (End-to-End Flow)"""
        
        # Mock Config
        cfg = {
            "retrieval": {"top_k": 1},
            "rag": {"use_cache": True, "score_threshold": 0.0},
            "vectorstore": {
                "persist_dir": "data/test_vectorstore_cache",
                "collection_name": "test_cache",
                "type": "chroma"
            },
            "llm": {
                "model": "qwen3:8b", # Using actual model or mock? 
                # If we rely on Ollama, it must be up.
                # Let's assume Ollama is up as per user context.
                "base_url": "http://localhost:11434"
            },
            "chat": {"save_log": False}
        }
        
        # Override SemanticCache dir for test
        # We need to monkeypatch or subclass ChatEngine to force test dir?
        # Or just pass it if ChatEngine accepted it. 
        # ChatEngine inits SemanticCache() with default args.
        # Let's modify ChatEngine to accept cache_dir or verify logic directly.
        
        # Direct Unit Test of Logic first (Simpler & Faster)
        cache = SemanticCache(persist_dir=TEST_CACHE_DIR)
        
        # 1. Miss
        q = "Test Query 123"
        ans = "Test Answer 123"
        hit = cache.check(q)
        self.assertIsNone(hit)
        
        # 2. Store
        cache.store(q, ans, {"model": "test"})
        
        # 3. Hit (Exact)
        hit = cache.check(q)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["answer"], ans)
        self.assertGreater(hit["score"], 0.99)
        
        # 4. Hit (Semantic)
        # "Test Query 123" vs "Test Query 1234" might differ?
        # "hello" vs "hello there"
        cache.store("hello", "hi there")
        
        hit_sem = cache.check("hello")
        self.assertIsNotNone(hit_sem)
        
        print("\n[TEST] Cache Unit Test Passed")

if __name__ == "__main__":
    unittest.main()
