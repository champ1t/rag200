
import sys
import unittest
from unittest.mock import MagicMock, patch
import sys
from unittest.mock import MagicMock

# Mock chromadb and its submodules BEFORE importing other modules
chromadb = MagicMock()
sys.modules["chromadb"] = chromadb

chromadb_utils = MagicMock()
sys.modules["chromadb.utils"] = chromadb_utils

chromadb_utils_embedding_functions = MagicMock()
sys.modules["chromadb.utils.embedding_functions"] = chromadb_utils_embedding_functions

# Also mock sentence_transformers inside the embedding function if needed, 
# although the import that failed was `from chromadb.utils.embedding_functions`
# which we just mocked.

# Now we can safely import
from src.core.chat_engine import ChatEngine
from src.rag.article_cleaner import smart_truncate

# Mock classes to simulate behavior
class MockHit:
    def __init__(self, score, document):
        self.score = score
        self.document = document

class MockWebHandler:
    def handle(self, query):
        if "flood" in query:
             return "Web Result: Major flooding reported in Chiang Rai..."
        return "Web Result: Some generic content"

class TestPolicyRefinements(unittest.TestCase):

    def setUp(self):
        # Initialize ChatEngine with mocked components
        # We assume ChatEngine can be instantiated without full DB connection if we patch things right
        # But realistically, ChatEngine __init__ does a lot. 
        # So we might need to mock the dependencies passed to it or patch it after creation.
        
        # Using patch to prevent actual initialization of heavy components
        with patch('src.chat_engine.VectorStore'), \
             patch('src.chat_engine.WebHandler'), \
             patch('src.chat_engine.LLMClient'):
             
            self.chat_engine = ChatEngine()
            
            # Manually attach mocks that we want to control
            self.chat_engine.vector_store = MagicMock()
            self.chat_engine.web_handler = MockWebHandler()
            
            # Set default policy
            self.chat_engine.routing_policy = {
                "web_knowledge": {
                    "internal_override_threshold": 0.65
                }
            }

    def test_safety_check_override(self):
        """
        Test that a query with high internal score overrides WEB_KNOWLEDGE intent.
        """
        q = "web search cisco ios commands"
        
        # Mock Vector Store to return a high score
        self.chat_engine.vector_store.hybrid_query.return_value = [
            MockHit(score=0.95, document="Internal Cisco Doc")
        ]
        
        # We need to access the specific logic block. 
        # Since the logic is inside 'process' method which is complex, 
        # we might want to extract the safety check logic or run 'process' with mocked intent detection.
        
        # Let's try to run 'process' but we need to control the intent detecting part.
        # The 'process' method calls 'self.determine_intent'. We should mock that.
        
        self.chat_engine.determine_intent = MagicMock(return_value="WEB_KNOWLEDGE")
        
        # Mock LLM generation for the final answer (since it falls through to GENERAL_QA)
        self.chat_engine.llm = MagicMock()
        self.chat_engine.llm.chat.return_value = "Internal RAG Answer"
        # Also need to mock _handle_general_qa or similar if it's called
        self.chat_engine._handle_general_qa = MagicMock(return_value="Internal RAG Answer")

        # Run process
        response = self.chat_engine.process(q)
        
        # Check if hybrid_query was called
        self.chat_engine.vector_store.hybrid_query.assert_called_with(q, top_k=1)
        
        # Check that it did NOT call web_handler.handle (because it should override)
        # Wait, if override happens, it goes to GENERAL_QA.
        # The code is:
        # if intent == "WEB_KNOWLEDGE":
        #    check safety
        #    if unsafe: intent = "GENERAL_QA"
        #    else: return web_handler.handle(q)
        
        # So if it was overridden, web_handler.handle should NOT be called.
        # And the response should come from the fall-through logic (GENERAL_QA).
        
        # Since we didn't fully mock the fall-through, let's just check the side effects.
        # We can spy on the web_handler.handle (it's a real method on our mock object, but we want to assert not called)
        # Let's replace it with a Mock to assert.
        self.chat_engine.web_handler.handle = MagicMock(return_value="Web Answer")
        
        response = self.chat_engine.process(q)
        
        self.chat_engine.web_handler.handle.assert_not_called()
        self.assertEqual(response, "Internal RAG Answer")
        print("\n[PASS] Safety Check Override Test")

    def test_legitimate_web_search(self):
        """
        Test that a query with low internal score is allowed to proceed to Web Handler.
        """
        q = "current news chiang rai floods"
        
        # Mock Vector Store to return a LOW score
        self.chat_engine.vector_store.hybrid_query.return_value = [
            MockHit(score=0.1, document="Irrelevant Doc")
        ]
        
        self.chat_engine.determine_intent = MagicMock(return_value="WEB_KNOWLEDGE")
        self.chat_engine.web_handler.handle = MagicMock(return_value="Web Search Result")
        
        response = self.chat_engine.process(q)
        
        # Should call web handler
        self.chat_engine.web_handler.handle.assert_called_once()
        self.assertEqual(response, "Web Search Result")
        print("\n[PASS] Legitimate Web Search Test")

    def test_read_more_link(self):
        """
        Test smart_truncate function for 'Read More' link presence.
        """
        text = "This is a very long article content. " * 50
        footer_url = "https://example.com/full-article"
        
        truncated_text = smart_truncate(text, max_length=100, footer_url=footer_url)
        
        self.assertIn("เนื้อหามีรายละเอียดเพิ่มเติม", truncated_text)
        self.assertIn(footer_url, truncated_text)
        print("\n[PASS] Read More Link Test")

if __name__ == '__main__':
    unittest.main()
