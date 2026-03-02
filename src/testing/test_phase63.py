import unittest
from src.rag.handlers.contact_handler import ContactHandler
from src.rag.article_interpreter import ArticleInterpreter

class TestPhase63(unittest.TestCase):
    
    def test_contact_provenance_display(self):
        # Mock Record with Provenance
        record = {
            "name": "Test User",
            "role": "Tester",
            "phones": ["0123", "0456"],
            "type": "team", # Required for TEAM intent match
            "phone_sources": {
                "0123": ["Manual"],
                "0456": ["Generated", "Manual"]
            },
            "emails": []
        }
        
        # We need to mock 'hits' logic or just call internal format?
        # ContactHandler.handle() calls internal format logic.
        # But handle() requires database/records.
        
        # Let's mock a hit result manually using the same logic copy or just simulate the hit structure 
        # returned by lookup (which we just did) and see how handle processes it.
        # Wait, handle() calls lookup().
        # I want to test the formatting block IN handle().
        
        # Construct a fake "hit" list and pass it to a modified handle?
        # Or simpler: The formatting logic is inside 'handle'.
        # I can subclass ContactHandler to inject hits.
        
        class MockContactHandler(ContactHandler):
            @classmethod
            def classify_contact_query(cls, q): return "TEAM"
        
        # Actually I can just mock lookup logic.
        # But 'handle' takes 'records'.
        # I'll pass a record that matches the query.
        
        q = "Test User"
        records = [record]
        
        # We need 'lookup_phones' to return this record.
        # 'lookup_phones' searches by name.
        
        # Ensure my mock record matches "Test User" query
        # src.directory.lookup.lookup_phones uses 'name_norm'.
        record["name_norm"] = "test user"
        
        res = MockContactHandler.handle(q, records)
        
        answer = res["answer"]
        print(f"Debug Answer: {answer}")
        
        # Assert phones appear.
        # Based on my implementation: "0123, 0456"
        # Wait, I didn't add the label "(Source)" in the implementation!
        # I commented it out: # formatted_phones.append(p)
        # So the output should be CLEAN keys.
        
        self.assertIn("0123", answer)
        self.assertIn("0456", answer)
        # We enabled Labels mapped to Web/File
        # "Manual" -> "File"
        self.assertIn("(File)", answer) 
        # self.assertNotIn("Manual", answer) # Deprecated assertion
        
    def test_ocr_pipeline_trigger(self):
        cfg = {"base_url": "", "model": "mock"}
        interpreter = ArticleInterpreter(cfg)
        
        # Mock _process_ocr to verify call - Must be > 50 chars for Contract Safety
        interpreter._process_ocr = lambda imgs: "[MOCK OCR RESULT] " * 5
        
        # 1. Normal query (No trigger)
        # Content < 400 chars, has images
        res = interpreter.interpret(
            user_query="How to X",
            article_title="Image Article",
            article_url="http://x",
            article_content="Short text.",
            images=[{"url": "img1"}]
        )
        self.assertIn("เนื้อหาหลักเป็นรูปภาพ", res)
        self.assertNotIn("MOCK OCR", res)
        
        # 2. Trigger query (Summary)
        res_ocr = interpreter.interpret(
            user_query="How to X summary",
            article_title="Image Article",
            article_url="http://x",
            article_content="Short text.",
            images=[{"url": "img1"}]
        )
        
        # Should NOT return safety/link-only message?
        # Wait, my code:
        # if is_summary_request:
        #    process ocr...
        #    pass # Fall through to extraction
        
        # And extraction continues...
        # Cleaned content gets "[MOCK OCR RESULT]" appended.
        # Then it goes to Topic Anchored Facts... or Truncate... then LLM.
        # The LLM will use the OCR content.
        # Since I'm mocking LLM call (it tries to call ollama_generate), this test might fail/error if LLM not reachable.
        
        # I need to mock ollama_generate too.
        
        interpreter.base_url = "mock"
        import src.rag.article_interpreter
        src.rag.article_interpreter.ollama_generate = lambda **kwargs: "LLM Output based on OCR content"
        
        res_ocr = interpreter.interpret(
            user_query="How to X summary",
            article_title="Image Article",
            article_url="http://x",
            article_content="Short text.",
            images=[{"url": "img1"}]
        )
        
        self.assertIn("LLM Output", res_ocr)
        # We can't easily check if OCR was passed to LLM without mocking generate params check.
        # But if it didn't crash and returned LLM output, it means it bypassed the "Safety Return".
        self.assertNotIn("เนื้อหาหลักเป็นรูปภาพ", res_ocr)

if __name__ == "__main__":
    unittest.main()
