
import sys
import os
import time
import yaml
from pprint import pprint

# Setup paths
sys.path.append(os.getcwd())

from src.chat_engine import ChatEngine

def run_suite():
    print("--- Starting Comprehensive QA Test Suite ---")
    
    # Load Config
    with open("configs/config.yaml", "r") as f:
        cfg = yaml.safe_load(f)
    
    # Init Engine
    engine = ChatEngine(cfg)
    
    test_cases = [
        # Set 1: Internal Knowledge
        {"q": "มาตรฐาน5ส", "type": "Internal (Strict 5S)"},
        {"q": "ขอเบอร์ noc", "type": "Directory (Broad)"},
        {"q": "วิธีตั้งค่า ONU Huawei", "type": "Internal HowTo"},
        
        # Set 2: External / News (WebHandler)
        {"q": "สรุปข่าว AI ปี 2024", "type": "Web News"},
        {"q": "ราคา Bitcoin ล่าสุด", "type": "Web Realtime"},
        {"q": "Windows 11 requirements", "type": "Web Tech"},
        
        # Set 3: Out of Scope / General
        {"q": "สวัสดีครับ", "type": "General Greeting"},
        {"q": "ขอสูตรต้มยำกุ้ง", "type": "Out of Scope (Cooking)"},
        {"q": "เล่านิทานให้ฟังหน่อย", "type": "Out of Scope (Creative)"}
    ]
    
    results = []
    
    for case in test_cases:
        print(f"\n>> Testing: {case['q']} [{case['type']}]")
        t0 = time.time()
        res = engine.process(case['q'], session_id="test_suite_1")
        dt = time.time() - t0
        
        print(f"   Route: {res.get('route')}")
        print(f"   Answer: {res.get('answer')[:200]}...") # Preview
        
        results.append({
            "query": case['q'],
            "type": case['type'],
            "route": res.get("route"),
            "latency": f"{dt:.2f}s",
            "full_answer": res.get("answer")
        })
        
    print("\n\n=== SUMMARY REPORT ===")
    for r in results:
        print(f"[{r['type']}] '{r['query']}' -> {r['route']} ({r['latency']})")
        print(f"Answer snippet: {r['full_answer'][:100].replace(chr(10), ' ')}")
        print("-" * 50)

if __name__ == "__main__":
    run_suite()
