import sys
import os
import re
from collections import defaultdict

sys.path.append(os.getcwd())

from src.rag.handlers.directory_handler import DirectoryHandler
from src.utils.normalization import normalize_for_matching

def test_lookup():
    print("--- Debug Position Lookup ---")
    
    # Mock Index
    position_index = {
        "ผส.บลตน.": [{"role": "ผส.บลตน.", "name": "Test Person", "phones": ["123"]}]
    }
    records = []
    dh = DirectoryHandler(position_index, records)
    
    query = "เบอร์ผส.บลตน"
    print(f"Query: '{query}'")
    
    # 1. Simulate handle_position_holder logic manually first to see cleaning
    q_clean = query
    patterns = [
            r"(?:ใคร|คร)\s*ตำแหน่ง", r"ตำแหน่ง\s*(?:ใคร|คร)", r"ผู้ดำรงตำแหน่ง", r"(?:ใคร|คร)\s*รับผิดชอบ", 
            r"(?:ใคร|คร)\s*คือ", r"(?:ใคร|คร)\s*เป็น", r"who\s*is", r"who\s*holds", r"ตำแหน่ง", r"คนไหน", r"คือใคร",
            r"เบอร์", r"โทร", r"ติดต่อ", r"email", r"อีเมล", r"fax", r"ที่อยู่"
    ]
    for p in patterns:
        q_clean = re.sub(p, "", q_clean, flags=re.IGNORECASE)
    
    print(f"Cleaned Query: '{q_clean}'") # Should be "ผส.บลตน"
    q_clean = q_clean.strip(" .?,")
    print(f"Stripped Query: '{q_clean}'")
    
    q_norm = normalize_for_matching(q_clean)
    print(f"Normalized Query: '{q_norm}'")
    
    # Check Index Keys Norm
    keys_norm = [normalize_for_matching(k) for k in position_index.keys()]
    print(f"Index Keys Norm: {keys_norm}")
    
    if q_norm in keys_norm:
        print("✅ Match found in norm keys!")
    else:
        print("❌ No match in norm keys!")
        
    # Run Actual Handler
    res = dh.handle_position_holder(query)
    print(f"Handler Answer: {res['answer']}")
    print(f"Handler Route: {res['route']}")

if __name__ == "__main__":
    test_lookup()
