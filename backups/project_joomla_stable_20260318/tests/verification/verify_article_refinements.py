
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from rag.article_cleaner import smart_truncate, strip_navigation_text

def test_smart_truncate():
    print("Testing smart_truncate...")
    text = "This is a long article content. " * 50
    footer_url = "https://example.com/full-article"
    
    # Test with length limit that forces truncation
    truncated = smart_truncate(text, length=100, footer_url=footer_url)
    
    print(f"Original length: {len(text)}")
    print(f"Truncated length: {len(truncated)}")
    
    expected_footer = f"\n\n📌 เนื้อหามีรายละเอียดเพิ่มเติม\n🔗 อ่านต่อฉบับเต็มได้ที่:\n{footer_url}"
    
    if expected_footer in truncated:
        print("✅ PASS: Footer URL is present in truncated text.")
    else:
        print("❌ FAIL: Footer URL is missing from truncated text.")
        print(f"Output ending: ...{truncated[-100:]}")

def test_strip_navigation_text():
    print("\nTesting strip_navigation_text...")
    
    # Simulate content with navigation noise
    noisy_content = """
    Home > category > news
    Menu
    Skip to content
    
    This is the actual article content that matters.
    It has multiple paragraphs.
    
    Copyright 2024
    Contact Us
    Privacy Policy
    """
    
    cleaned = strip_navigation_text(noisy_content)
    
    print("--- Original ---")
    print(noisy_content)
    print("--- Cleaned ---")
    print(cleaned)
    
    if "Skip to content" not in cleaned and "Home > category" not in cleaned:
        print("✅ PASS: Navigation noise removed.")
    else:
        print("❌ FAIL: Navigation noise still present.")

    if "This is the actual article content that matters." in cleaned:
        print("✅ PASS: Main content preserved.")
    else:
        print("❌ FAIL: Main content removed.")

if __name__ == "__main__":
    test_smart_truncate()
    test_strip_navigation_text()
