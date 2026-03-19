
import sys
import os
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rag.article_cleaner import smart_truncate, strip_navigation_text, deduplicate_paragraphs
from src.chat_engine import ChatEngine
from unittest.mock import MagicMock

def test_cleaning_functions():
    print("=== Testing Article Cleaning Functions ===")
    
    # Test 1: smart_truncate with footer
    print("\n[Test 1] smart_truncate with footer_url")
    text = "This is a long article content that needs truncation." * 10
    footer_url = "https://example.com/article"
    truncated = smart_truncate(text, max_length=50, footer_url=footer_url)
    
    if footer_url in truncated and "อ่านต่อฉบับเต็มได้ที่" in truncated:
        print("PASS: Footer URL found in truncated text.")
    else:
        print("FAIL: Footer URL NOT found in truncated text.")
        print(f"Output: {truncated}")

    # Test 2: strip_navigation_text
    print("\n[Test 2] strip_navigation_text")
    noisy_text = """
    Home > Category > Tech
    Menu
    About Us
    Contact
    
    The actual article content starts here.
    
    Footer stuff
    Copyright 2024
    """
    clean_text = strip_navigation_text(noisy_text)
    
    if "Menu" not in clean_text and "The actual article content starts here" in clean_text:
         print("PASS: Navigation noise removed.")
    else:
         print("FAIL: Navigation noise NOT correctly removed.")
         print(f"Output: {clean_text}")

def test_routing_policy():
    print("\n=== Testing Routing Policy (Simulation) ===")
    
    # Mocking ChatEngine dependencies to avoid full initialization overhead if possible,
    # but for integration test, partial real init is better. 
    # However, to strictly control the 'internal score', we should mock the vector_store.
    
    # Instantiate ChatEngine with mocked vector_store
    
    # We need to minimally init ChatEngine just to access .process logic or similar
    # But ChatEngine puts everything in __init__.
    # Let's try to load it and patch the vector_store on the instance.
    
    try:
        chat_engine = ChatEngine()
        
        # MOCK the vector_store.hybrid_query
        chat_engine.vector_store = MagicMock()
        
        # CASE 1: High Internal Score -> Should Override Web
        print("\n[Test 3] Routing Policy: High Internal Score (Should Override)")
        
        # Setup mock return: High score
        mock_hit = MagicMock()
        mock_hit.score = 0.95 # Higher than default 0.65
        chat_engine.vector_store.hybrid_query.return_value = [mock_hit]
        
        # Mock web_handler to see if it gets called (it shouldn't if overridden)
        chat_engine.web_handler = MagicMock()
        chat_engine.web_handler.handle.return_value = "Web Search Result"
        
        # Mock _handle_generic (General QA) to capture the fall-through
        # But _handle_generic is a method.
        # Check logic: if intent becomes GENERAL_QA, it falls through to standard RAG logic.
        # We can detect this by seeing if web_handler.handle is called (Should NOT be)
        # and checking if intent was changed if we can inspect logs or side effects.
        # Actually, if it falls through, it will eventually hit self.vector_store.hybrid_query AGAIN in generic path
        # or do other things.
        
        # Easier way: Capture stdout to see specific DEBUG logs.
        
        # We will assume that if code works, we see "Safety Check: Found internal match" in output
        # prevented by the mock? No, we want to run the real .process() method up to a point.
        
        # Let's just run it passing a signal.
        # The safety check is inside `process(q)`.
        
        # IMPORTANT: 'intent' detection is inside process(). 
        # We need to force intent="WEB_KNOWLEDGE".
        # We can mock `self.router.route` to return "WEB_KNOWLEDGE"
        chat_engine.router = MagicMock()
        chat_engine.router.route.return_value = "WEB_KNOWLEDGE"
        
        # Mock history check to return False for follow-up to ensure we hit intent routing
        # chat_engine._is_followup_question = MagicMock(return_value=(False, None)) 
        # Actually _analyze_intent_or_context might need mocking if it's complex.
        # But assuming default behavior for "config vlan" is fine.
        
        # Let's rely on print capturing for simplified verification without complex mocks of internal logic flow
        # We set vector_store to return high score.
        
        q = "config vlan cisco"
        print(f"Query: {q}")
        
        # We need to catch the exception or return because we didn't mock everything for GENERAL_QA flow
        # The flow is:
        # 1. safety check -> overrides to GENERAL_QA
        # 2. falls through to `responses = ...`
        # 3. eventually calls `self.vector_store.hybrid_query` again (mocked)
        # 4. calls `self.llm_client.chat` (not mocked yet) -> will fail or lag.
        
        # Let's mock llm_client too.
        chat_engine.llm_client = MagicMock()
        chat_engine.llm_client.chat.return_value = "Internal Answer"
        
        result = chat_engine.process(q)
        
        # Check if web_handler was called
        if chat_engine.web_handler.handle.called:
             print("FAIL: Web Handler was called despite high internal score.")
        else:
             print("PASS: Web Handler was skipped (Safety Override worked).")

        
        # CASE 2: Low Internal Score -> Should go to Web
        print("\n[Test 4] Routing Policy: Low Internal Score (Should go to Web)")
        
        mock_hit.score = 0.1 # Lower than 0.65
        chat_engine.vector_store.hybrid_query.return_value = [mock_hit]
        chat_engine.web_handler.handle.reset_mock()
        
        q_web = "news about floods"
        print(f"Query: {q_web}")
        
        chat_engine.process(q_web)
        
        if chat_engine.web_handler.handle.called:
             print("PASS: Web Handler was called for low internal score.")
        else:
             print("FAIL: Web Handler was NOT called for low internal score.")

    except Exception as e:
        print(f"An error occurred during ChatEngine testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cleaning_functions()
    test_routing_policy()
