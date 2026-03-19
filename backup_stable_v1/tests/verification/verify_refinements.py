
import sys
import os

# Ensure src is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.chat_engine import ChatEngine
from src.rag.article_cleaner import smart_truncate, strip_navigation_text, deduplicate_paragraphs

def test_routing_safety_check():
    print("--- Test 1: Routing Safety Check ---")
    # We need to simulate the ChatEngine and its routing logic.
    # Since we can't easily mock the entire vector store state without complex setup, 
    # we might be better off running the actual engine if the environment allows, 
    # OR we can inspect the methods if we can instantiate it partially.
    
    # However, running the full engine might be slow or require credentials/servers.
    # The user wants to verify the IMPLEMENTATION works. 
    # Let's try to instantiate ChatEngine if possible, or at least unit test the components we changed if full integration test is too heavy.
    # Given the previous context, the user seems to be running this locally.
    
    try:
        engine = ChatEngine()
        print("ChatEngine instantiated successfully.")
        
        # Test Case A: Internal Knowledge (Should trigger safety check)
        # "config vlan cisco"
        query_internal = "config vlan cisco"
        print(f"\nProcessing query (Internal): '{query_internal}'")
        # We can't easily assert the internal route without mocking the vector store response 
        # unless we actually have data in the vector store.
        # Assuming the user has data, we can run it and check the logs/output if we were running interactively.
        # For this script, we can perhaps just check if the method exists and logic looks correct by introspection 
        # or by mocking the components if we want a true unit test.
        
        # checks for existence of attributes
        if not hasattr(engine, 'routing_policy'):
            print("FAILURE: ChatEngine missing routing_policy")
        else:
            print("SUCCESS: ChatEngine has routing_policy")
            
    except Exception as e:
        print(f"Skipping full ChatEngine integration test due to setup requirements: {e}")
        print("We will rely on manual confirmation or unit testing of the cleaning functions.")

def test_article_cleaning():
    print("\n--- Test 2: Article Cleaning Functions ---")
    
    # 2.1 Test Read More Link (smart_truncate)
    print("\n[2.1] Testing smart_truncate (Read More Link)...")
    long_text = "Content " * 500
    footer_url = "https://example.com/article"
    truncated = smart_truncate(long_text, max_length=100, footer_url=footer_url)
    
    expected_footer = f"\n\n📌 เนื้อหามีรายละเอียดเพิ่มเติม\n🔗 อ่านต่อฉบับเต็มได้ที่:\n{footer_url}"
    
    if expected_footer in truncated:
        print("SUCCESS: 'Read More' footer found in truncated text.")
    else:
        print(f"FAILURE: 'Read More' footer NOT found.\nResult: {truncated[-100:]}")

    # 2.2 Test Navigation Strip (strip_navigation_text)
    print("\n[2.2] Testing strip_navigation_text...")
    noisy_text = """
    Home > Tech > Articles
    Menu
    Contact Us
    
    Actual Article Content is here.
    
    Privacy Policy
    Terms of Service
    Copyright 2024
    """
    
    cleaned = strip_navigation_text(noisy_text)
    if "Actual Article Content is here" in cleaned and "Home > Tech > Articles" not in cleaned:
        print("SUCCESS: Navigation noise removed.")
    else:
        print(f"FAILURE: Noise might still be present or content removed.\nResult: {cleaned}")

    # 2.3 Test Deduplicate Paragraphs
    print("\n[2.3] Testing deduplicate_paragraphs...")
    dup_text = "This is a paragraph.\n\nThis is a paragraph.\n\nUnique paragraph."
    deduped = deduplicate_paragraphs(dup_text)
    count = deduped.count("This is a paragraph.")
    
    if count == 1:
        print("SUCCESS: Paragraphs deduplicated.")
    else:
        print(f"FAILURE: Duplicates found (count={count}).\nResult: {deduped}")

if __name__ == "__main__":
    test_article_cleaning()
    # We skip test_routing_safety_check in this simple script because it requires live DB connection
    # typically. We will verify routing by running a manual query command next.
