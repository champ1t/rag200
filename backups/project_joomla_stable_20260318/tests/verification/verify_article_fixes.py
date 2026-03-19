
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from rag.article_cleaner import smart_truncate, strip_navigation_text

def test_smart_truncate():
    print("Testing smart_truncate...")
    text = "This is a long article content. " * 50
    footer_url = "https://example.com/full-article"
    
    truncated = smart_truncate(text, length=100, footer_url=footer_url)
    
    print(f"Original Length: {len(text)}")
    print(f"Truncated Length: {len(truncated)}")
    
    expected_footer = f"\n\n📌 เนื้อหามีรายละเอียดเพิ่มเติม\n🔗 อ่านต่อฉบับเต็มได้ที่:\n{footer_url}"
    
    if expected_footer in truncated:
        print("PASS: Footer URL found in truncated text.")
    else:
        print("FAIL: Footer URL NOT found in truncated text.")
        print(f"Output end: {truncated[-100:]}")

def test_strip_navigation_text():
    print("\nTesting strip_navigation_text...")
    # Simulate content with navigation noise
    noisy_content = """
    Home > Category > Tech
    Menu
    About Us | Contact
    
    This is the actual article content that we want to keep.
    It contains important information about the RAG system.
    
    Copyright 2024
    Privacy Policy
    """
    
    cleaned = strip_navigation_text(noisy_content)
    
    print(f"Original Content:\n{noisy_content}")
    print("-" * 20)
    print(f"Cleaned Content:\n{cleaned}")
    print("-" * 20)
    
    if "About Us | Contact" not in cleaned and "Home > Category > Tech" not in cleaned:
        print("PASS: Navigation noise removed.")
    else:
        print("FAIL: Navigation noise still present.")

if __name__ == "__main__":
    test_smart_truncate()
    test_strip_navigation_text()
