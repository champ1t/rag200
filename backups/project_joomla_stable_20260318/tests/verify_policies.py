
import os
import sys
import logging

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.chat_engine import ChatEngine
from src.config import Config

# Setup logging to capture the debug prints we expect
logging.basicConfig(level=logging.INFO)

def test_rag_policy():
    print("Initializing ChatEngine...")
    config = Config()
    # Ensure the policy threshold is as expected (default 0.65)
    print(f"Policy Threshold: {config.routing_policy.get('web_knowledge', {}).get('internal_override_threshold')}")

    chat_engine = ChatEngine()

    print("\nXXX TEST CASE 1: Internal Knowledge Override (Safety Check) XXX")
    # Query likely to be in internal docs (based on user context)
    query_internal = "config vlan cisco" 
    print(f"Query: {query_internal}")
    response_internal = chat_engine.process(query_internal)
    print(f"Response Intent: {response_internal.get('intent')}")
    # We can't easily see stdout capture here from the subprocess calls inside ChatEngine unless we redirect, 
    # but the logs from the chat engine itself should appear in the output of this script.

    print("\nXXX TEST CASE 2: Genuine Web Knowledge XXX")
    # Query likely to NOT be in internal docs
    query_web = "news about Chiang Rai floods current situation"
    print(f"Query: {query_web}")
    response_web = chat_engine.process(query_web)
    print(f"Response Intent: {response_web.get('intent')}")

    print("\nXXX TEST CASE 3: Article Summarization & Read More Link XXX")
    # Use a URL that we might be able to scrape or mock the result if we can't access internet effortlessly, 
    # but let's try a real query that triggers the article flow if possible.
    # If we assume 'query_web' triggers an article, we can inspect 'response_web'.
    # Alternatively, we can test the cleaner function directly if we want to isolate it.
    
    if response_web.get('source_documents'):
        print("Found source documents from web query.")
        print(f"Response Text Length: {len(response_web.get('answer', ''))}")
        print("Checking for 'Read More' link...")
        if "อ่านต่อฉบับเต็มได้ที่" in response_web.get('answer', ''):
            print("SUCCESS: 'Read More' link found.")
        else:
            print("FAILURE: 'Read More' link NOT found.")
            
        print("Preview of Answer (checking for navigation noise):")
        print(response_web.get('answer', '')[:500])
    
    # Let's also unit test the cleaner directly to be sure
    from src.rag.article_cleaner import smart_truncate
    print("\nXXX TEST CASE 4: Unit Test smart_truncate XXX")
    text = "Content " * 100
    footer_url = "http://example.com"
    truncated = smart_truncate(text, length=50, footer_url=footer_url)
    print(f"Truncated Text:\n{truncated}")
    if footer_url in truncated:
         print("SUCCESS: Unit test passed.")
    else:
         print("FAILURE: Unit test failed.")

if __name__ == "__main__":
    test_rag_policy()
