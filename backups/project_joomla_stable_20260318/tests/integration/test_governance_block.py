import sys
import os
import unittest
import json
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine

MOCK_CFG = {
    "llm": {"model": "mock", "base_url": "mock"},
    "chat": {"show_context": False},
    "rag": {"use_cache": False},
    "retrieval": {"top_k": 3}
}

class TestStrictGovernance(unittest.TestCase):
    def setUp(self):
        # Initialize ChatEngine with mock config
        # We need to mock build_vectorstore to avoid heavy loading
        # And mock load_records etc.
        # However, ChatEngine init calls `self.processed_cache = ProcessedCache(...)` which is what we need.
        # So we can let init run, but mock heavy dependencies if possible.
        # Actually simplest is to partial mock where we patch global imports, but for now let's just run it.
        # If build_vectorstore fails or takes too long, we might need to patch it.
        
        # Patch build_vectorstore globally before init
        # But since we already imported ChatEngine, we need to patch the imported name in chat_engine module
        pass

    def test_missing_corpus_block(self):
        """Test: 'Cisco ASR920' should trigger strict block (No RAG fallback)"""
        # Patch dependencies to run fast
        with unittest.mock.patch('src.chat_engine.build_vectorstore', return_value=MagicMock()):
            with unittest.mock.patch('src.chat_engine.load_records', return_value=[]):
                 self.engine = ChatEngine(MOCK_CFG)
                 # Mock other components
                 self.engine.vector_store = MagicMock()
                 self.engine.llm = MagicMock()
                 self.engine.controller = MagicMock()
                 
                 query = "ขอวิธี config Cisco ASR920 หน่อยครับ"
                 print(f"\nTesting Query: '{query}'")
                 
                 # Act
                 response = self.engine.process(query)
                 
                 # Assert
                 print(f"Response Route: {response.get('route')}")
                 print(f"Response Answer: {response.get('answer')}")
                 
                 self.assertEqual(response.get("route"), "rag_missing_corpus")
                 self.assertIn("MISSING_CORPUS", response.get("answer"))
                 # Check for topic presence (lowercase normalized)
                 self.assertIn("cisco asr920", response.get("answer").lower()) 

if __name__ == "__main__":
    unittest.main()
