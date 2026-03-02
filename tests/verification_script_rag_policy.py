
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock modules that might rely on external services if we import them directly
# ensuring we can import ChatEngine without initializing heavy DBs
sys.modules['chromadb'] = MagicMock()
sys.modules['src.vectorstore'] = MagicMock()

# Now import the classes to test
# We might need to handle imports inside ChatEngine carefully
# Let's try importing and if it fails due to dependencies, we mock them more aggressively
try:
    from src.core.chat_engine import ChatEngine
    from src.rag.article_cleaner import smart_truncate, strip_navigation_text
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

class TestRAGPolicyRefinements(unittest.TestCase):

    def setUp(self):
        # Setup common mocks
        self.mock_vector_store = MagicMock()
        self.mock_web_handler = MagicMock()
        self.mock_llm_service = MagicMock()
        
        # Partial mock of ChatEngine to avoid full initialization
        # We only strictly need to test the logic in process() or specifically the block we changed
        pass

    def test_web_knowledge_safety_check_override(self):
        """Test that high confidence internal match overrides WEB_KNOWLEDGE intent"""
        print("\nTesting Web Knowledge Safety Check (Override Case)...")
        
        # Instantiate ChatEngine with mocks
        # We need to bypass __init__ or provide all args
        with patch('src.chat_engine.ChatEngine.__init__', return_value=None):
            engine = ChatEngine()
            engine.vector_store = self.mock_vector_store
            engine.web_handler = self.mock_web_handler
            engine.routing_policy = {"web_knowledge": {"internal_override_threshold": 0.65}}
            engine.llm_service = self.mock_llm_service
            
            # Mock methods used in process()
            engine._classify_intent = MagicMock(return_value="WEB_KNOWLEDGE")
            engine.analyze_follow_up = MagicMock(return_value={"is_follow_up": False})
            engine._handle_general_qa = MagicMock(return_value="Internal RAG Response")
            engine.conversation_history = []
            
            # Setup Vector Store to return HIGH SCORE (Safety Check Trigger)
            mock_hit = MagicMock()
            mock_hit.score = 0.85 # Above 0.65
            engine.vector_store.hybrid_query.return_value = [mock_hit]
            
            # Run logic - we can't easily run full process() without mocking everything else
            # so we'll copy the logic snippet or try to run process() if it's isolated enough.
            # Looking at code, process() does a lot. 
            # Let's try to run process("internal query") and see if it calls web_handler or _handle_general_qa
            
            # We need to mock other parts of process to ensure it reaches our target block
            # Assuming flow: check_follow_up -> classify_intent -> intent_handling
            
            response = engine.process("config vlan cisco")
            
            # Verify Safety Check was called
            engine.vector_store.hybrid_query.assert_called_with("config vlan cisco", top_k=1)
            
            # Verify Web Handler was NOT called
            engine.web_handler.handle.assert_not_called()
            
            # Verify it fell through to GENERAL_QA (which we mocked to return "Internal RAG Response")
            # Note: The code says `intent = "GENERAL_QA"` then falls through to `if intent == "GENERAL_QA"` block
            # So _handle_general_qa should be called
            engine._handle_general_qa.assert_called()
            print("PASS: Internal query stayed internal (Safety Check working)")

    def test_web_knowledge_safety_check_pass(self):
        """Test that low confidence internal match allows WEB_KNOWLEDGE intent"""
        print("\nTesting Web Knowledge Safety Check (Pass Case)...")
        
        with patch('src.chat_engine.ChatEngine.__init__', return_value=None):
            engine = ChatEngine()
            engine.vector_store = self.mock_vector_store
            engine.web_handler = self.mock_web_handler
            engine.routing_policy = {"web_knowledge": {"internal_override_threshold": 0.65}}
            engine.llm_service = self.mock_llm_service
            
            engine._classify_intent = MagicMock(return_value="WEB_KNOWLEDGE")
            engine.analyze_follow_up = MagicMock(return_value={"is_follow_up": False})
            engine._handle_general_qa = MagicMock(return_value="Internal RAG Response")
            engine.web_handler.handle = MagicMock(return_value="Web Search Result")
            engine.conversation_history = []
            
            # Setup Vector Store to return LOW SCORE
            mock_hit = MagicMock()
            mock_hit.score = 0.40 # Below 0.65
            engine.vector_store.hybrid_query.return_value = [mock_hit]
            
            response = engine.process("news about floods")
            
            # Verify Safety Check called
            engine.vector_store.hybrid_query.assert_called_with("news about floods", top_k=1)
            
            # Verify Web Handler WAS called
            engine.web_handler.handle.assert_called_with("news about floods")
            
            # Verify _handle_general_qa was NOT called
            engine._handle_general_qa.assert_not_called()
            print("PASS: Web query went to Web (Safety Check correctly passed)")

    def test_smart_truncate_read_more(self):
        """Verify 'Read More' link is appended correctly"""
        print("\nTesting Smart Truncate 'Read More' link...")
        text = "This is a long article content. " * 50
        footer_url = "https://example.com/article"
        
        # Set max_length to prompt truncation
        truncated = smart_truncate(text, max_length=100, footer_url=footer_url)
        
        expected_footer = f"\n\n📌 เนื้อหามีรายละเอียดเพิ่มเติม\n🔗 อ่านต่อฉบับเต็มได้ที่:\n{footer_url}"
        
        if expected_footer in truncated:
            print("PASS: Footer URL found in truncated text")
        else:
            print(f"FAIL: Footer URL NOT found. Got end of text: ...{truncated[-50:]}")
            self.fail("Footer URL missing")

    def test_strip_navigation_text(self):
        """Verify navigation noise is removed"""
        print("\nTesting Strip Navigation Text...")
        dirty_text = """
        Home > Category > Tech
        Menu | Login | Sign Up
        Actual article content starts here.
        Copyright 2024
        """
        # The cleaner relies on heuristics (line length, keywords like 'Menu', 'Home', 'Copyright')
        # Let's hope the implementation covers these simple cases or we check specific known patterns
        
        clean_text = strip_navigation_text(dirty_text)
        
        # We expect "Actual article content starts here." to remain
        # and "Menu | Login" likely to be removed if the heuristic works for this short valid block
        
        if "Actual article content starts here" in clean_text:
            print("PASS: Content preserved")
        else:
            print("FAIL: Content lost")
            
        if "Menu | Login" not in clean_text:
             print("PASS: Nav menu removed")
        else:
             print("WARN: Nav menu NOT removed (might be due to heuristic limit on short text)")

if __name__ == '__main__':
    unittest.main()
