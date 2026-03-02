
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.chat_engine import ChatEngine
from src.vector_store import VectorStore

class TestWebKnowledgeSafetyCheck(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_config = MagicMock()
        self.mock_vector_store = MagicMock()
        self.mock_llm = MagicMock()
        self.mock_embeddings = MagicMock()
        
        # Setup specific routing policy config
        self.mock_config.routing_policy = {
            "web_knowledge": {
                "internal_override_threshold": 0.65
            }
        }
        
        # Instantiate ChatEngine with mocks
        # We need to patch the internal components that might be initialized in __init__
        with patch('src.chat_engine.VectorStore', return_value=self.mock_vector_store), \
             patch('src.chat_engine.LLMClient', return_value=self.mock_llm), \
             patch('src.chat_engine.Embeddings', return_value=self.mock_embeddings), \
             patch('src.chat_engine.WebHandler', return_value=MagicMock()), \
             patch('src.chat_engine.IntentRouter', return_value=MagicMock()), \
             patch('src.chat_engine.WebSearcher', return_value=MagicMock()):
             
             self.chat_engine = ChatEngine(config=self.mock_config)
             # Manually attach the mock vector store if it wasn't attached correctly by the patch
             self.chat_engine.vector_store = self.mock_vector_store
             self.chat_engine.routing_policy = self.mock_config.routing_policy

    def test_safety_check_overrides_high_confidence_internal(self):
        """Test that a high-confidence internal match overrides WEB_KNOWLEDGE intent."""
        
        # Setup the scenario:
        # 1. Intent matches "WEB_KNOWLEDGE" (we can force this by mocking logic or directly calling the block if extracted, 
        #    but effectively we want to test the block inside 'process'. 
        #    Since 'process' is complex, we might simulate the intent detection return.)
        
        query = "config vlan cisco"
        
        # Mock vector store hybrid query to return a high score
        mock_hit = MagicMock()
        mock_hit.score = 0.85 # Above 0.65 threshold
        self.mock_vector_store.hybrid_query.return_value = [mock_hit]
        
        # We need to access the specific logic block. 
        # Since we can't easily run 'process' fully without mocking everything (intent router etc),
        # let's look at the implementation again. 
        # The logic is inline in `process`. 
        # We will mock `determine_intent` to return "WEB_KNOWLEDGE".
        
        self.chat_engine.router = MagicMock()
        self.chat_engine.router.classify.return_value = "WEB_KNOWLEDGE"
        
        # Mock web_handler and other methods potentially called to avoid side effects
        self.chat_engine.web_handler.handle = MagicMock(return_value="WEB_RESPONSE")
        self.chat_engine._handle_general_qa = MagicMock(return_value="INTERNAL_RESPONSE")
        
        # We need to trap the intent *change*.
        # The code does `intent = "GENERAL_QA"`.
        # Then it falls through to `if intent == "GENERAL_QA" or ...`
        
        # Let's mock `_handle_general_qa` to return a specific marker so we know it was called.
        self.chat_engine._handle_general_qa.return_value = "SAFELY_ROUTED_TO_INTERNAL"
        
        # In `process`, if intent is WEB_KNOWLEDGE and override happens, it sets intent=GENERAL_QA 
        # and then SHOULD satisfy the condition for general QA.
        
        # However, `process` might have a `return` in the WEB_KNOWLEDGE block if NOT overridden.
        # If overridden, it sets intent="GENERAL_QA" and falls through.
        
        # Call process (we might need to mock more things like `analyze_conversation_context` if it exists)
        # Assuming `process(q, history)` structure
        
        with patch.object(self.chat_engine, '_check_followup_need', return_value=False): # Avoid context checks
             response = self.chat_engine.process(query, history=[])
        
        # Assertions
        # 1. Hybrid query was called
        self.mock_vector_store.hybrid_query.assert_called_with(query, top_k=1)
        
        # 2. Response should be from internal handler, NOT web handler
        self.chat_engine.web_handler.handle.assert_not_called()
        self.chat_engine._handle_general_qa.assert_called()
        self.assertEqual(response, "SAFELY_ROUTED_TO_INTERNAL")
        print("Success: High confidence internal query prevented external web search.")

    def test_safety_check_allows_web_for_low_confidence(self):
        """Test that low-confidence internal match allows WEB_KNOWLEDGE intent."""
        
        query = "news about Chiang Rai floods"
        
        # Mock vector store hybrid query to return a low score
        mock_hit = MagicMock()
        mock_hit.score = 0.20 # Below 0.65 threshold
        self.mock_vector_store.hybrid_query.return_value = [mock_hit]
        
        self.chat_engine.router = MagicMock()
        self.chat_engine.router.classify.return_value = "WEB_KNOWLEDGE"
        
        self.chat_engine.web_handler.handle = MagicMock(return_value="WEB_RESPONSE")
        self.chat_engine._handle_general_qa = MagicMock(return_value="INTERNAL_RESPONSE")
        
        with patch.object(self.chat_engine, '_check_followup_need', return_value=False):
             response = self.chat_engine.process(query, history=[])
        
        # Assertions
        self.mock_vector_store.hybrid_query.assert_called_with(query, top_k=1)
        self.chat_engine.web_handler.handle.assert_called_with(query)
        self.chat_engine._handle_general_qa.assert_not_called()
        self.assertEqual(response, "WEB_RESPONSE")
        print("Success: Low confidence internal query correctly routed to Web.")

if __name__ == '__main__':
    unittest.main()
