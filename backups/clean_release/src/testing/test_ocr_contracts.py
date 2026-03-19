import unittest
from src.rag.article_interpreter import ArticleInterpreter

class TestOCRContracts(unittest.TestCase):
    
    def setUp(self):
        cfg = {"base_url": "mock", "model": "mock"}
        self.interpreter = ArticleInterpreter(cfg)
        # Mock LLM to avoid network, return "LLM Answer"
        import src.rag.article_interpreter
        src.rag.article_interpreter.ollama_generate = lambda **kwargs: "LLM Answer"
        
    def test_ocr_gating_negative(self):
        """Contract: OCR must NOT run if not requested."""
        # 1. Image Heavy but NO Summary Request
        self.interpreter._process_ocr = lambda imgs: "SHOULD_NOT_RUN"
        
        res = self.interpreter.interpret(
            user_query="Just browsing",
            article_title="Image Heavy",
            article_url="http://x",
            article_content="Short content but valid.",
            images=[{"url": "img1"}]
        )
        
        self.assertNotIn("SHOULD_NOT_RUN", res)
        # Should return the "Content is images... Safety" message
        self.assertIn("เนื้อหาหลักเป็นรูปภาพ", res)

    def test_ocr_safety_fallback(self):
        """Contract: If OCR returns sparse/garbage text, fallback to Link-Only (don't hallucinate)."""
        # User asks Summary -> Enters OCR path
        # OCR returns garbage (Short, no thai)
        
        self.interpreter._process_ocr = lambda imgs: "xy" # Very short garbage
        
        # We need to spy on the "cleaned_content" passed to logic?
        # Or checking final result.
        # If garbage is appended, LLM sees "Short\nxy".
        # If "Short" < 10 chars -> returns "Content too short".
        # If "Short\nxy" -> maybe passes length check?
        # But we want explicit filtering of bad OCR.
        
        # If I mock LLM to echo input, I can check valid prompt.
        # But easier: Valid behavior from interpreter should be "Content too short" if OCR failed to provide substance.
        
        res = self.interpreter.interpret(
            user_query="Summary",
            article_title="Image Heavy",
            article_url="http://x",
            article_content="Short content but longer than 10 chars.",
            images=[{"url": "img1"}]
        )
        
        # If OCR text "xy" is accepted:
        # content = "...\nxy" (len > 10).
        
        # 1. Short Garbage (Should be Rejected)
        self.interpreter._process_ocr = lambda imgs: "xy" * 10 # 20 chars
        res_short = self.interpreter.interpret(
            user_query="summary",
            article_title="Image Heavy",
            article_url="http://x",
            article_content="Short content but longer than 10 chars.",
            images=[{"url": "img1"}]
        )
        self.assertIn("ไม่พบข้อมูลที่ชัดเจน", res_short)
        
        # 2. Long Content (Should be Accepted)
        # Note: "x"*100 is medically garbage but structurally valid per our simple contract
        self.interpreter._process_ocr = lambda imgs: "Valid content " * 10 # > 50 chars
        res_long = self.interpreter.interpret(
            user_query="summary",
            article_title="Image Heavy",
            article_url="http://x",
            article_content="Short content but longer than 10 chars.",
            images=[{"url": "img1"}]
        )
        self.assertEqual(res_long, "LLM Answer")

if __name__ == "__main__":
    unittest.main()
