from pathlib import Path
import json

def check_coverage():
    processed_dir = Path("data/processed")
    if not processed_dir.exists():
        print("[ERROR] data/processed not found")
        return

    files = list(processed_dir.glob("*.json"))
    print(f"[INFO] Total processed files: {len(files)}")
    
    # Analyze by Itemid (as proxy for section) or URL path
    sections = {}
    for p in files:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            url = data.get("url", "")
            title = data.get("title", "")
            
            # Simple clustering
            if "Itemid" in url:
                # Extract Itemid
                import re
                m = re.search(r"Itemid=(\d+)", url)
                if m:
                    iid = m.group(1)
                    if iid not in sections: sections[iid] = 0
                    sections[iid] += 1
            else:
                if "other" not in sections: sections["other"] = 0
                sections["other"] += 1
                
        except Exception:
            pass
            
    print("\n[INFO] Coverage by Itemid (approx sections):")
    for sec, count in sorted(sections.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 9999):
        print(f"  Itemid={sec}: {count} pages")
        
    # Check important Itemids from knowledge
    # 60=Director, 56=Manager, 64=Personnel List
    required = ["60", "56", "64"]
    missing = [r for r in required if r not in sections]
    
    if missing:
        print(f"\n[WARN] Missing critical Itemids: {missing}")
    else:
        print("\n[PASS] Critical sections (Director/Manager/Personnel) present.")

if __name__ == "__main__":
    check_coverage()
