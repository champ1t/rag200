
import sys
import unittest
from src.chat_engine import ChatEngine

# Mock Config
cfg = {
    "llm": {"model": "test", "base_url": "http://localhost"},
    "retrieval": {"top_k": 3},
    "chat": {"show_context": True},
    "rag": {"use_cache": False}
}

class TestChatEngineIntegration(unittest.TestCase):
    def test_init(self):
        try:
            engine = ChatEngine(cfg)
            print("ChatEngine initialized.")
            self.assertTrue(hasattr(engine, "directory_handler"), "DirectoryHandler not initialized")
            self.assertTrue(engine.directory_handler is not None)
            # Check if internal maps are working
            # engine.directory_handler.pos_norm_map should be populated if data exists
            print(f"Handler Map Size: {len(engine.directory_handler.pos_norm_map)}")
        except Exception as e:
            self.fail(f"ChatEngine Init Failed: {e}")

if __name__ == "__main__":
    unittest.main()
