
import unittest
from src.rag.article_cleaner import clean_article_content, deduplicate_paragraphs
from src.rag.synonyms import expand_synonyms

class TestPhase174(unittest.TestCase):
    
    def test_synonyms(self):
        print("\n=== Testing Synonyms ===")
        cases = [
            ("วิธีแก้ tr069", "howto TR069 CWMP"),
            ("เข้าเว็บ edoc", "link Edocument"),
            ("ipphone โทรไม่ออก", "ipphone โทรไม่ออก"),
            ("วิธีทำ config", "howto setting"),
        ]
        for inp, expected in cases:
            res = expand_synonyms(inp)
            print(f"'{inp}' -> '{res}'")
            self.assertEqual(res, expected)
            
    def test_cleanup_garbage(self):
        print("\n=== Testing Garbage Cleanup ===")
        dirty = """
        WDM (แนะนำIE)
        Content Line 1
        Your IP: 10.121.1.1
        Content Line 2
        Username: admin Password: 123
        Login Box
        """
        cleaned = clean_article_content(dirty)
        print("--- Cleaned Output ---")
        print(cleaned)
        
        self.assertNotIn("WDM (แนะนำIE)", cleaned)
        self.assertNotIn("Your IP:", cleaned)
        self.assertNotIn("Username:", cleaned)
        self.assertIn("Content Line 1", cleaned)
        
    def test_deduplication(self):
        print("\n=== Testing Deduplication ===")
        text = """
        This is a unique paragraph.
        
        This is a repeated paragraph that should be removed independently.
        It has enough length to be significant.
        
        This is a unique paragraph.
        
        This is a repeated paragraph that should be removed independently.
        It has enough length to be significant.
        """
        deduped = deduplicate_paragraphs(text.strip())
        print("--- Deduped Output ---")
        print(deduped)
        
        self.assertEqual(deduped.count("repeated paragraph"), 1)
        self.assertEqual(deduped.count("unique paragraph"), 1) # Wait, "unique paragraph" appeared twice in input too?
        # Ah, logic: "This is a unique paragraph." appeared twice above.
        # My logic dedups based on content signature.
        # So "This is a unique paragraph." should ALSO be deduped to 1 instance.
        
if __name__ == '__main__':
    unittest.main()
