
import sys
import os
import re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.rag.article_cleaner import extract_topic_anchored_facts

def test_huawei_noise_removal():
    # Exact string from Phase 113 Test Log:
    # "1. | 67 | 522 | 958 ... (และอีก 3 รายการ ดูเพิ่มเติมในลิงก์ต้นฉบับ) WDM (แนะนำIE) เข้า ONU ZTE ไม่ได้..."
    # Note: "1. " is added by interpreter. The cleaner sees the raw lines.
    
    raw_content_with_noise_2 = """
    | 67 | 522 | 958 WDM (แนะนำIE) เข้า ONU ZTE ไม่ได้ กรณี Login เข้าหน้าแรก
    """
    
    print("Testing Generic Noise Removal...")
    # Simulate what happens inside cleaner
    # It likely sees "| 67 | 522 | 958" as one line.
    
    facts = extract_topic_anchored_facts(raw_content_with_noise_2, "ONU ZTE")
    
    print(f"Extracted {len(facts)} facts.")
    found_noise = False
    for f in facts:
        print(f"Fact: {f}")
        if "| 67 |" in f or "| 522 |" in f:
            found_noise = True
            
    if found_noise:
        print("[FAIL] Noise artifacts found!")
        sys.exit(1)
    else:
        print("[PASS] No noise artifacts found.")

if __name__ == "__main__":
    test_huawei_noise_removal()
