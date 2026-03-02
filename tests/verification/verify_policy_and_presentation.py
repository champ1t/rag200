import sys
import os
import logging
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from chat_engine import ChatEngine
from rag.article_cleaner import smart_truncate, strip_navigation_text
from rag.article_interpreter import ArticleInterpreter

# Setup basic logging to capture the debug prints we added
logging.basicConfig(level=logging.INFO)

def test_safety_check():
    print("\n--- Testing Web Knowledge Safety Check ---")
    try:
        engine = ChatEngine()
        
        # Test 1: Internal Topic (Should trigger override)
        # We need to simulate a state where vector_store returns a high score.
        # Since we can't easily populate the real vector store for this test without dependencies,
        # we might need to mock the vector_store.hybrid_query method if we can't rely on existing data.
        # However, let's try to see if we can just mock the self.vector_store on the engine instance.
        
        mock_hit = MagicMock()
        mock_hit.score = 0.85 # Above 0.65 threshold
        engine.vector_store.hybrid_query = MagicMock(return_value=[mock_hit])
        
        # Force intent to WEB_KNOWLEDGE initially to test the override
        # Use a subclass or mock the router? 
        # Actually, the safety check happens INSIDE process() when intent is WEB_KNOWLEDGE.
        # We need to mock the router to return WEB_KNOWLEDGE first.
        
        engine.router.route = MagicMock(return_value="WEB_KNOWLEDGE")
        engine.web_handler.handle = MagicMock(return_value="Web Handler Called")
        
        print("Query: 'config vlan cisco' (Simulated Internal High Score)")
        # We expect it NOT to call web_handler.handle, or if it falls through to GENERAL_QA, 
        # it will hit the internal RAG logic. Use a mock for internal logic if needed.
        # But wait, looking at the code:
        # if safety_hits[0].score > policy_threshold:
        #    intent = "GENERAL_QA"
        #    # Falls through to: if intent == "GENERAL_QA": ...
        
        # So we should see if it falls through.
        # Let's mock the general_qa handler part or just see what happens.
        # "GENERAL_QA" block calls self._handle_general_qa(q)
        engine._handle_general_qa = MagicMock(return_value="Internal QA Handler Called")
        
        response = engine.process("config vlan cisco")
        
        if response == "Internal QA Handler Called":
            print("✅ SUCCESS: Web Knowledge intent was overridden to Internal QA.")
        elif response == "Web Handler Called":
            print("❌ FAILURE: Web Knowledge intent was NOT overridden.")
        else:
            print(f"⚠️ UNEXPECTED: Got response: {response}")

        # Test 2: External Topic (Should NOT trigger override)
        mock_hit_low = MagicMock()
        mock_hit_low.score = 0.2 # Below 0.65 threshold
        engine.vector_store.hybrid_query = MagicMock(return_value=[mock_hit_low])
        engine.router.route = MagicMock(return_value="WEB_KNOWLEDGE")
        
        print("\nQuery: 'Chiang Rai floods' (Simulated Internal Low Score)")
        response = engine.process("Chiang Rai floods")
        
        if response == "Web Handler Called":
            print("✅ SUCCESS: Web Knowledge intent was preserved for low internal score.")
        else:
            print(f"❌ FAILURE: Expected Web Handler, got: {response}")

    except Exception as e:
        print(f"Error during safety check test: {e}")

def test_article_presentation():
    print("\n--- Testing Article Presentation Enhancements ---")
    
    # 1. Test Navigation Strip
    dirty_html_text = """
    Home > Tech > Networking
    Menu
    Skip to content
    
    This is the actual article content. It talks about things.
    
    Related Articles:
    - Item 1
    - Item 2
    
    Copyright 2024
    """
    cleaned = strip_navigation_text(dirty_html_text)
    print(f"Original length: {len(dirty_html_text)}, Cleaned length: {len(cleaned)}")
    if "Menu" not in cleaned and "Copyright" not in cleaned:
        print("✅ SUCCESS: Navigation noise removed.")
    else:
        print("❌ FAILURE: Navigation noise still present.")
        print(f"Cleaned text snippet: {cleaned[:100]}...")

    # 2. Test Smart Truncate with Read More
    long_text = "Content " * 100
    footer_url = "https://example.com/article"
    truncated = smart_truncate(long_text, max_length=50, footer_url=footer_url)
    
    if footer_url in truncated and "อ่านต่อฉบับเต็ม" in truncated:
        print("✅ SUCCESS: 'Read More' footer appended.")
    else:
        print("❌ FAILURE: 'Read More' footer missing.")
        print(f"Result: {truncated}")

if __name__ == "__main__":
    test_safety_check()
    test_article_presentation()
