
import sys
import os
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.chat_engine import ChatEngine
from src.vectorstore import VectorStore
# Mock classes to avoid full initialization if possible, or just use real ones if lightweight.
# ChatEngine requires a lot of config. Let's try to mock the dependencies or use a simplified setup.
# Actually, since we want to test the *logic* in ChatEngine.process specifically the lines 1425+, 
# we need a ChatEngine instance with a mocked vector_store and routing_policy.

class MockVectorStore:
    def __init__(self, internal_score=0.0):
        self.internal_score = internal_score

    def hybrid_query(self, query, top_k=1):
        class MockHit:
            def __init__(self, score):
                self.score = score
        # Return a hit with the configured score
        return [MockHit(self.internal_score)]

class MockWebHandler:
    def handle(self, q):
        return f"WEB_HANDLER_CALLED:{q}"

class MockContextManager:
    def get_context(self, session_id):
        return []
    def add_interaction(self, session_id, q, a, intent):
        pass

# We need to subclass ChatEngine or monkeypatch because __init__ might be heavy
# Let's try to instantiate a minimal version or subclass for testing.

class TestChatEngine(ChatEngine):
    def __init__(self, vector_store, web_handler):
        # Skip super().__init__ to avoid loading everything
        self.vector_store = vector_store
        self.web_handler = web_handler
        self.routing_policy = {"web_knowledge": {"internal_override_threshold": 0.65}}
        self.context_manager = MockContextManager()
        self.llm = None # Not needed for this specific routing check if we stop before intent classification? 
        # Wait, the logic is inside `process` AFTER intent detection.
        # We need to mock the intent detection part or force the intent to be WEB_KNOWLEDGE to test the check.
        # The logic is:
        # intent = self._detect_intent(...)
        # ...
        # if intent == "WEB_KNOWLEDGE": ...
        
        # We can override _detect_intent to return "WEB_KNOWLEDGE"
    
    def _detect_intent(self, query):
        return "WEB_KNOWLEDGE"
        
    def _is_intent_correction_needed(self, *args):
        return False, None

    # We also need to mock _handle_general_qa because if it falls through, it calls that.
    def _handle_general_qa(self, query):
        return "INTERNAL_RAG_CALLED"

def test_safety_check_high_score():
    print("\n--- Testing Safety Check: High Internal Score (Should Override) ---")
    # Setup mock vector store with high score
    mock_vs = MockVectorStore(internal_score=0.90)
    mock_web = MockWebHandler()
    engine = TestChatEngine(mock_vs, mock_web)
    
    # Run process
    # We expect it to print the debug logs and return "INTERNAL_RAG_CALLED"
    result = engine.process("config vlan cisco", "test_session")
    print(f"Result: {result}")
    
    if result == "INTERNAL_RAG_CALLED":
        print("PASS: Correctly overrode to Internal RAG")
    else:
        print(f"FAIL: Expected INTERNAL_RAG_CALLED, got {result}")

def test_safety_check_low_score():
    print("\n--- Testing Safety Check: Low Internal Score (Should Go to Web) ---")
    # Setup mock vector store with low score
    mock_vs = MockVectorStore(internal_score=0.10)
    mock_web = MockWebHandler()
    engine = TestChatEngine(mock_vs, mock_web)
    
    # Run process
    # We expect it to return "WEB_HANDLER_CALLED:..."
    result = engine.process("news about floods", "test_session")
    print(f"Result: {result}")
    
    if "WEB_HANDLER_CALLED" in result:
        print("PASS: Correctly routed to Web Handler")
    else:
        print(f"FAIL: Expected WEB_HANDLER_CALLED, got {result}")

if __name__ == "__main__":
    test_safety_check_high_score()
    test_safety_check_low_score()
