import sys
import os
import yaml
from src.core.chat_engine import ChatEngine

# Ensure src is in path
sys.path.append(os.getcwd())

def run_test(engine, query, expected_snippet, test_name, expected_in_answer=None, not_expected_in_answer=None):
    print(f"\n[TEST] {test_name}")
    print(f"Query: '{query}'")
    
    res = engine.process(query, session_id="test_rule_h")
    ans = res.get("answer", "")
    route = res.get("route")
    hits = res.get("hits") or []
    
    print(f"Route: {route}")
    print(f"Answer snippet: {ans[:100]}...")

    if expected_in_answer:
        for x in expected_in_answer:
            if x not in ans:
                print(f"[FAIL] Missing expected phrase '{x}'")
                return
    
    if not_expected_in_answer:
        for x in not_expected_in_answer:
            if x in ans:
                print(f"[FAIL] Found unexpected phrase '{x}'")
                return
    
    if expected_snippet in ans or any(expected_snippet in h.get("name", "") for h in hits):
        print(f"[PASS] Found '{expected_snippet}'")
    else:
        print(f"[FAIL] Missing '{expected_snippet}'")

def main():
    cfg = yaml.safe_load(open("configs/config.yaml"))
    engine = ChatEngine(cfg)
    
    # Rule H: Abbrev Expansion
    run_test(engine, "สื่อสารข้อมูล พัท", "พัทลุง", "Abbrev Expansion (Prefix Match)")
    run_test(engine, "ศูนย์สื่อสารข้อมูล นรา", "นราธิวาส", "Abbrev Expansion (Map)")
    run_test(engine, "สื่อสารข้อมูล ภูเก", "ภูเก็ต", "Abbrev Expansion (Map)")
    
    # Rule I: Broad Query Policy
    # "noc" -> Should list all (e.g. 50 items) without asking "which one".
    # Check if answer contains list but not ambiguity prompt.
    run_test(engine, "noc", "RNOC", "Broad Query (NOC)", 
             expected_in_answer=["1. ", "5. "], 
             not_expected_in_answer=["ขอทราบว่า", "ต้องการติดต่อหน่วยงานใด"])
             
    # Normal case
    run_test(engine, "สื่อสารข้อมูล ภูเก็ต", "ภูเก็ต", "Normal Full Name")

if __name__ == "__main__":
    main()
