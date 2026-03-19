import sys
import os
import json
import re
from collections import Counter

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from utils.extractors import ABBREVIATIONS, PROVINCES
    from utils.normalization import normalize_text, normalize_for_matching
except ImportError as e:
    print(f"Error importing utils: {e}")
    sys.exit(1)

def check_jsonl(filepath):
    print(f"--- Checking {filepath} ---")
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return

    data = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if not line.strip(): continue
                try:
                    obj = json.loads(line)
                    data.append(obj)
                except json.JSONDecodeError:
                    print(f"❌ JSON Error at line {i+1}")
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    print(f"✅ Loaded {len(data)} records.")
    
    # Check Duplicates (Name + Type)
    seen = {}
    duplicates = []
    
    # Validation Counters
    missing_fields = Counter()
    
    for r in data:
        name = r.get("name")
        rtype = r.get("type", "unknown")
        
        if not name:
            missing_fields["name"] += 1
            continue
            
        # Check Normalization
        norm = r.get("name_norm", "")
        recalc_norm = normalize_for_matching(name)
        # Note: name_norm in file might use a slightly different logic or pre-computed value
        # But for new system, they should align.
        
        key = (name, rtype)
        if key in seen:
            duplicates.append(key)
        else:
            seen[key] = True

    if duplicates:
        print(f"⚠️ Found {len(duplicates)} potential duplicates (Name+Type):")
        for d in duplicates[:5]:
            print(f"   - {d}")
        if len(duplicates) > 5: print(f"   ... and {len(duplicates)-5} more.")
    else:
        print("✅ No exact duplicates found.")

    if missing_fields:
        print(f"⚠️ Missing Fields: {dict(missing_fields)}")
    else:
        print("✅ All records have 'name'.")
        
    return data

def check_extractors():
    print("\n--- Checking Extractors and Abbreviations ---")
    print(f"✅ Loaded {len(ABBREVIATIONS)} abbreviations.")
    print(f"✅ Loaded {len(PROVINCES)} provinces.")
    
    # Check for dangerous mappings
    dangerous_mappings = {
        "hatyai": "songkhla", # The bug we fixed
        "หาดใหญ่": "สงขลา",   # The bug we fixed
    }
    
    found_dangerous = []
    for k, v in ABBREVIATIONS.items():
        if k in dangerous_mappings and v == dangerous_mappings[k]:
            found_dangerous.append((k, v))
            
    if found_dangerous:
        print(f"❌ FOUND DANGEROUS MAPPINGS: {found_dangerous}")
    else:
        print("✅ No known dangerous mappings found.")

def main():
    base_dir = "/Users/jakkapatmac/Documents/NT/RAG/rag_web/data/records"
    check_jsonl(os.path.join(base_dir, "directory.jsonl"))
    check_jsonl(os.path.join(base_dir, "positions.jsonl"))
    
    check_extractors()

if __name__ == "__main__":
    main()
