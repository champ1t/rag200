
import sys
import os
import re
from bs4 import BeautifulSoup

# Mock content based on User Requirements
html_content = """
<html>
<body>
    <div id="header">Header</div>
    
    <!-- Widget Block (Should be removed) -->
    <div class="moduletable">
        <h3>Visitors Counter</h3>
        <div>Today | 20</div>
        <div>Yesterday | 15</div>
        <div>We have: 1 guests online</div>
        <div>Your IP: 10.192.133.253</div>
    </div>
    
    <!-- Main Content (Priority 1: articleBody) -->
    <div itemprop="articleBody">
        <h1>Correct Article Title</h1>
        <p>This is the correct content about SIP Proxy.</p>
        <p>Config sbc command...</p>
        <p>IP Address: INTERNAL_TEST_IP (Should be masked)</p>
    </div>
    
    <!-- Fallback Content (Should be ignored if Priority 1 exists) -->
    <div class="main-both">
        <p>This is fallback content that should NOT be picked if articleBody serves.</p>
    </div>
    
</body>
</html>
"""

def test_extraction_safety():
    from src.rag.article_cleaner import clean_article_html
    
    print("=== Testing Advanced Extraction & Safety ===")
    
    # 1. Test Selector Fallback
    # Should select 'articleBody' content, NOT 'main-both' content
    cleaned_text, _, _ = clean_article_html(html_content)
    
    print(f"\n[Extracted Text]:\n{cleaned_text[:500]}...\n")
    
    # Assertions
    if "Correct Article Title" in cleaned_text:
        print("[PASS] Selector Priority: 'articleBody' selected.")
    else:
        print("[FAIL] Selector Priority: Failed to select 'articleBody'.")
        
    if "fallback content" not in cleaned_text:
        print("[PASS] Fallback Logic: Fallback content ignored.")
    else:
        print("[FAIL] Fallback Logic: Fallback content leaked (Aggregation issue).")
        
    if "Your IP" not in cleaned_text and "INTERNAL_TEST_IP" in cleaned_text:
        print("[PASS] Widget/Safety Policy: Widget removed, but Internal IP INTERNAL_TEST_IP preserved (Correct for Internal RAG).")
    elif "Your IP" in cleaned_text:
        print("[FAIL] Widget Removal: 'Your IP' widget leaked.")
    elif "INTERNAL_TEST_IP" not in cleaned_text:
         print("[FAIL] Policy Error: IP INTERNAL_TEST_IP was masked! (Should be visible for Internal Staff).") 

if __name__ == "__main__":
    # We will run this against the actual module once we modify it
    test_extraction_safety()
