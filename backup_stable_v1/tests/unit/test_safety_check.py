
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from chat_engine import ChatEngine

def test_safety_check_override():
    print("--- Testing Web Knowledge Safety Check (Override Scenario) ---")
    
    # Mock dependencies
    mock_vector_store = MagicMock()
    mock_llm = MagicMock()
    mock_web_handler = MagicMock()
    
    # Setup ChatEngine with mocks
    engine = ChatEngine(vector_store=mock_vector_store, llm=mock_llm)
    engine.web_handler = mock_web_handler
    engine.routing_policy = {"web_knowledge": {"internal_override_threshold": 0.65}}

    # Mock vector store to return a high score match
    mock_match = MagicMock()
    mock_match.score = 0.85 # Above 0.65 threshold
    mock_vector_store.hybrid_query.return_value = [mock_match]

    # Mock web_handler to see if it gets called (it should NOT be called if overriden, 
    # BUT the code says: if intent == "GENERAL_QA" it falls through.
    # We need to verify that 'intent' changes or the flow changes.
    # In the code: 
    # if safety_hits[0].score > policy_threshold:
    #    intent = "GENERAL_QA"
    #    # falls through to standard RAG
    
    # Use a side_effect on hybrid_query to print what's happening or just check calls
    
    # We need to hit the specific block in process()
    # The process method is complex, let's mock the intent detection parts if possible.
    # Assume 'determine_intent' or similar logic returns "WEB_KNOWLEDGE"
    
    # It seems hard to mock the *internal* variable 'intent' inside process().
    # However, we can mock `self.web_handler.handle(q)` to see if it is called.
    
    # IMPORTANT: The code logic does:
    # if intent == "WEB_KNOWLEDGE":
    #    ... check safety ...
    #    if unsafe:
    #       intent = "GENERAL_QA"
    #    else:
    #       return self.web_handler.handle(q)
    
    # So if we mock web_handler.handle to raise an exception or return a specific string, 
    # we can know if it was called.
    
    mock_web_handler.handle.return_value = "WEB_HANDLER_CALLED"
    
    # We also need to mock the intent detection to return "WEB_KNOWLEDGE"
    # Looking at the code is required to know how intent is determined.
    # Assuming there's a reliable way to force WEB_KNOWLEDGE intent via query or mocking.
    # Since I don't have the full code for `detect_intent` visible right now, 
    # I will rely on the query "news about Chiang Rai" likely triggering it, 
    # BUT I need to force the Safety Check.
    
    # Actually, allow me to just patch the `detect_intent` mechanism?
    # Or I can just instantiate ChatEngine and try to rely on its internal logic?
    # Let's try to "inject" the intent if possible, or just subclass/mock the intent detection.
    
    with patch.object(ChatEngine, '_check_intent_patterns', return_value="WEB_KNOWLEDGE"):
         # Case 1: High Score (Should Override)
         mock_match.score = 0.85
         # We need to mock the rest of the standard RAG flow to avoid errors since it falls through
         # The fall-through goes to `self.vector_store.hybrid_query` again and then `self.llm.chat`
         
         # Mock the second vector store call (standard rag)
         mock_vector_store.hybrid_query.return_value = [mock_match] # Same match
         
         mock_llm.chat.return_value = "INTERNAL_RAG_RESPONSE"
         
         response = engine.process("config vlan cisco")
         
         if response == "INTERNAL_RAG_RESPONSE":
             print("PASS: High confidence internal match routed to Internal RAG (Override successful).")
         elif response == "WEB_HANDLER_CALLED":
             print("FAIL: High confidence internal match incorrectly routed to Web Handler.")
         else:
             print(f"UNKNOWN: {response}")

         
    print("\n--- Testing Web Knowledge Safety Check (Pass-through Scenario) ---")
    with patch.object(ChatEngine, '_check_intent_patterns', return_value="WEB_KNOWLEDGE"):
         # Case 2: Low Score (Should NOT override)
         mock_match.score = 0.40 # Below 0.65
         mock_vector_store.hybrid_query.return_value = [mock_match]
         
         response = engine.process("latest news flooding")
         
         if response == "WEB_HANDLER_CALLED":
             print("PASS: Low confidence internal match routed to Web Handler.")
         else:
             print(f"FAIL: Low confidence internal match NOT routed to Web Handler. Got: {response}")

if __name__ == "__main__":
    test_safety_check_override()
