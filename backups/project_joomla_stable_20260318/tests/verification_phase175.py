
import sys
import os
import time

# Add src to path
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine
from src.vectorstore.chroma import ChromaVectorStore

def test_safety_check():
    print("\n=== Testing Web Knowledge Safety Check ===")
    
    # Initialize basic components (Mocking processed_cache if needed, but integration test is better)
    # We'll try to instantiate ChatEngine real
    try:
        import yaml
        if os.path.exists("configs/config.yaml"):
            config_path = "configs/config.yaml"
        elif os.path.exists("config/config.yaml"):
            config_path = "config/config.yaml"
        else:
            print("ERROR: No config found.")
            return

        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)

        chat = ChatEngine(cfg)
        print("[Setup] ChatEngine initialized.")
        
        # Test Case 1: Internal Knowledge
        print("\n--- Case 1: Internal Knowledge Query ('config vlan cisco') ---")
        q1 = "config vlan cisco" 
        res1 = chat.process(q1)
        print(f"Query: '{q1}'")
        print(f"Result Route: {res1.get('route')}")
        # print(f"Result Answer: {res1.get('answer')[:100]}...")
        
        if res1.get('route') in ["howto_procedure", "general_qa", "knowledge_pack"]:
            print("✅ PASS: Internal query stayed internal.")
        elif res1.get('route') == "web_knowledge":
            print("❌ FAIL: Internal query leaked to Web!")
        else:
            print(f"⚠️ NOTE: Route was {res1.get('route')}")

        # Test Case 2: External Knowledge
        print("\n--- Case 2: External Knowledge Query ('ข่าวน้ำท่วมเชียงราย 2568') ---")
        q2 = "ข่าวน้ำท่วมเชียงราย 2568"
        res2 = chat.process(q2)
        print(f"Query: '{q2}'")
        print(f"Result Route: {res2.get('route')}")
        
        if res2.get('route') == "web_knowledge":
            print("✅ PASS: External query went to Web.")
        else:
            print(f"❌ FAIL: External query did NOT go to Web. Route: {res2.get('route')}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

def test_article_cleaning():
    print("\n=== Testing Article Formatting ===")
    from src.rag.article_cleaner import smart_truncate, strip_navigation_text
    
    msg = """
    Home | About Us | Contact
    Menu
    
    Actual Title
    
    This is the real content of the article. It should be preserved.
    It talks about FTTx configuration.
    
    This section is repeated to ensure length exceeds the limit for truncation testing.
    This section is repeated to ensure length exceeds the limit for truncation testing.
    This section is repeated to ensure length exceeds the limit for truncation testing.
    This section is repeated to ensure length exceeds the limit for truncation testing.
    This section is repeated to ensure length exceeds the limit for truncation testing.
    
    user: admin password: 123
    
    Footer | Privacy Policy
    All rights reserved.
    """
    
    # 1. Test strip_navigation_text
    cleaned = strip_navigation_text(msg)
    if "Home | About Us" not in cleaned:
        print("✅ PASS: strip_navigation_text")
    else:
        print("❌ FAIL: strip_navigation_text")

    # 2. Test smart_truncate footer
    res = smart_truncate(cleaned, max_length=100, footer_url="http://test.com")
    if "อ่านต่อฉบับเต็ม" in res:
        print("✅ PASS: smart_truncate footer")
    else:
        print("❌ FAIL: smart_truncate footer")

if __name__ == "__main__":
    test_article_cleaning()
    test_safety_check()
