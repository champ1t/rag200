
import json
import re
from pathlib import Path
from src.rag.handlers.dispatch_mapper import DispatchMapper

def debug_real_satun():
    processed_dir = Path("data/processed")
    target_text = None
    target_file = None
    
    # 1. Find the article
    for p in processed_dir.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            text = data.get("text", "")
            if "การจ่ายงานเลขหมายวงจรเช่า" in text:
                target_text = text
                target_file = p
                break
        except Exception:
            continue
            
    if not target_text:
        print("[ERROR] Dispatch Article not found in data/processed/")
        return

    print(f"[INFO] Found Article in: {target_file}")
    
    # 2. Extract Raw Satun Section
    # Find "สตูล" and print 20 lines after it
    idx = target_text.find("สตูล")
    if idx != -1:
        print("\n=== RAW SATUN SECTION (First 500 chars) ===")
        print(target_text[idx:idx+500])
        print("===========================================\n")
    else:
        print("[ERROR] 'สตูล' not found in text!")
        
    # 3. Test DispatchMapper Parsing
    print("[INFO] Running DispatchMapper._parse_dispatch_article...")
    data_map = DispatchMapper._parse_dispatch_article(target_text)
    
    if "สตูล" in data_map:
        print(f"\n[RESULT] Parsed 'สตูล' Content:")
        print(f"'{data_map['สตูล']}'")
        
        # Check why it might be empty
        lines = data_map['สตูล'].split('\n')
        print(f"\nLine Count: {len(lines)}")
    else:
        print("[ERROR] 'สตูล' key missing from parsed map!")

if __name__ == "__main__":
    debug_real_satun()
