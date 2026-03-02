
import unittest
from src.rag.article_cleaner import is_navigation_dominated, extract_topic_anchored_facts, clean_article_content

class TestNavFilter(unittest.TestCase):
    def test_nav_detection(self):
        print("\n--- Test 1: Navigation Detection ---")
        nav_content = """หน้าหลัก (Home)
ลงทะเบียน (Register)
ลืมรหัสผ่าน (Forgot Password)
ข่าวสาร SMC (SMC News)
ความรู้ (Knowledge)
Template by Joomlashack
"""
        is_nav = is_navigation_dominated(nav_content)
        print(f"Content:\n{nav_content}")
        print(f"Is Nav Dominated: {is_nav}")
        self.assertTrue(is_nav)
        
    def test_topic_anchored_extraction(self):
        print("\n--- Test 2: Topic Anchored Extraction ---")
        content = """
1. หน้าหลัก
2. ข่าวสาร
3. DNS Server: 1.1.1.1
4. SMTP Server: mail.tot.co.th
5. ลงทะเบียน
"""
        query = "DNS SMTP"
        facts = extract_topic_anchored_facts(content, query)
        print(f"Query: {query}")
        print("Facts:")
        for f in facts: print(f"- {f}")
        
        # Should contain DNS and SMTP
        self.assertTrue(any("DNS" in f for f in facts))
        self.assertTrue(any("SMTP" in f for f in facts))
        # Should NOT contain "หน้าหลัก" or "ลงทะเบียน"
        self.assertFalse(any("หน้าหลัก" in f for f in facts))
        self.assertFalse(any("ลงทะเบียน" in f for f in facts))
        
    def test_huawei_bras_mixed(self):
        print("\n--- Test 3: Huawei Bras (Mixed) ---")
        content = """
หน้าหลัก
ข่าวสาร SMC
Huawei Bras IPPGW Command
1. display vrrp
   - Shows VRRP status
2. ping 8.8.8.8
   - Check connectivity
3. Template Wrapper
"""
        query = "Huawei command"
        facts = extract_topic_anchored_facts(content, query)
        print("Facts:")
        for f in facts: print(f"- {f}")
        
        self.assertTrue(len(facts) >= 2)
        self.assertTrue(any("display" in f for f in facts))
        self.assertFalse(any("หน้าหลัก" in f for f in facts))


if __name__ == '__main__':
    unittest.main()
