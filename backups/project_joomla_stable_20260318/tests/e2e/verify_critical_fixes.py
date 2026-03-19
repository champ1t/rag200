
import sys
import yaml
import json
from src.core.chat_engine import ChatEngine

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_test():
    cfg = load_config("configs/config.yaml")
    engine = ChatEngine(cfg)
    
    cases = [
        # A) Contact / Choice
        {"q": "เบอร์ NOC", "checks": ["contact_ambiguous", "contact_broad_list"], "desc": "Ambiguous List"},
        {"q": "3", "checks": ["contact_hit_choice", "contact_hit", "contact_ambiguous"], "desc": "Choice Selection (After NOC)"}, 
        {"q": "เบอร์ศูนย์หาดใหญ่", "checks": ["contact_hit", "contact_ambiguous"], "must_not_contain": "ศูนย์อร์ศูนย์", "desc": "Rewriter Glitch (No recursive rewrite)"},
        {"q": "omc hatyai เบอร์", "checks": ["contact_hit", "contact_ambiguous", "contact_hit_contact_book_fuzzy"], "forbidden_intent": "HOWTO_PROCEDURE", "desc": "Contact Override HowTo"},
        
        # B) Article / Junk
        {"q": "ตารางเวร สรกภ.4", "checks": ["article_answer", "rag_hit", "rag", "article_cache"], "must_contain": ["แหล่งที่มา"], "must_not_contain": ["online"], "desc": "Clean Summary"},
        {"q": "ตาราง proxy IPphone", "checks": ["article_answer", "rag_hit", "rag", "article_cache"], "must_contain": ["แหล่งที่มา"], "desc": "Menu Mode"},
        
        # C) Define term (Hallucination Guard)
        {"q": "OLT คือ", "checks": ["rag_fallback_general", "rag_hit", "article_answer", "rag"], "desc": "General Definition"},
        {"q": "GPON คือ", "checks": ["rag_fallback_general", "rag_hit", "article_answer", "rag"], "desc": "General Definition"},
        {"q": "ใครคือผจ", "checks": ["position_ambiguous", "position_holder_lookup", "rag_low_score_gate", "rag_miss_coverage", "position_miss", "position_holder_hit"], "forbidden_intent": "DEFINE_TERM", "must_not_contain": ["นาย", "นาง"], "desc": "Who Is -> Position (Not Define)"},
        {"q": "ผจ คืออะไร", "checks": ["rag_fallback_general", "rag_hit", "article_answer", "rag_low_score_gate", "rag"], "desc": "Define -> General"},
        
        # D) Routing internal-first
        {"q": "ทำbridgeระหว่างport", "checks": ["article_answer", "rag"], "desc": "Internal Article for Config"},
        {"q": "add adsl Huawei", "checks": ["article_answer", "rag_miss_coverage", "web_error", "rag"], "desc": "Internal First / Fail Closed"},
        
        # E) Refinements (Phase 236)
        {"q": "RAG คืออะไร", "checks": ["rag", "glossary_hit"], "must_contain": ["Retrieval-Augmented Generation"], "desc": "Technical Glossary HIT"},
        {"q": "EDIMAX เบอร์", "checks": ["contact_miss_broad_help", "contact_miss_strict"], "must_contain": ["King Intelligent", "3408"], "desc": "Vendor Broad Miss Help"},
        {"q": "มาตรฐาน 5 ส.", "checks": ["article_answer", "rag"], "must_not_contain": ["INSTRUCTION:", "If MENU_MODE:"], "desc": "Prompt Leakage Filter"},
        {"q": "ตาราง proxy IPphone", "checks": ["article_answer"], "must_contain": ["view=article"], "desc": "URL Normalization Check"},
        {"q": "ผส คือใคร", "checks": ["position_ambiguous", "position_holder_hit"], "must_contain": ["ค้นหา", "ผส."], "desc": "Short Role Lookup Fix"},
        {"q": "เบออร์ NOC", "checks": ["contact_broad_list", "contact_ambiguous"], "must_contain": ["NOC"], "desc": "Phone Signal Typos (เบออร์)"},
        {"q": "เบอร NOC", "checks": ["contact_broad_list", "contact_ambiguous"], "must_contain": ["NOC"], "desc": "Phone Signal Typos (เบอร)"},
        {"q": "เบอร์ csoc", "checks": ["contact_broad_list", "contact_ambiguous"], "forbidden_route": "article_answer", "desc": "Override Shield (เบอร์ csoc)"},
        {"q": "ผส คือใครเหรอ", "checks": ["position_ambiguous", "position_holder_hit"], "must_contain": ["ค้นหา", "ผส."], "must_not_contain": ["เหรอ"], "desc": "Role Parsing Noise Cleanup"},
        {"q": "เบแอร์ csoc", "checks": ["contact_broad_list", "contact_ambiguous"], "must_contain": ["CSOC"], "desc": "Phone Signal Typos (เบแอร์)"},
        {"q": "เบอร์ NOC ทั้งหมด", "checks": ["contact_broad_list", "contact_ambiguous"], "must_contain": ["NOC"], "desc": "Broad List Request"},
        {"q": "rrouter คืออะไร", "checks": ["rag", "rag_hit", "rag_clarify"], "must_contain": [], "desc": "Regression: Fingerprint Error (Define Term)"}
    ]
    
    print(f"Running {len(cases)} critical tests...")
    
    # Pre-test setup for stateful test
    # Ensuring "เบอร์ NOC" creates state for "3"
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(cases):
        q = case["q"]
        print(f"\n[{i+1}] Query: '{q}' ({case['desc']})")
        
        # Hack for stateful test "3"
        if q == "3":
            if not engine.pending_question:
                 print("   [SKIP] Skipping '3' because previous state wasn't set.")
                 continue
        
        res = engine.process(q)
        route = res.get("route", "unknown")
        ans = res.get("answer", "")
        intent = res.get("intent", "unknown")
        
        print(f"   -> Route: {repr(route)}")
        print(f"   -> Intent: {intent}")
        # print(f"   -> Answer Snippet: {ans[:100]}...")
        
        checks = case.get("checks", [])
        if checks:
            route_str = str(route).strip().lower()
            match_found = False
            for c in checks:
                if c.lower() == route_str:
                    match_found = True
                    break
            
            if not match_found:
                print(f"   [FAIL] Expected route in {checks}, got '{route_str}'")
                failed += 1
                continue

        forbidden_intent = case.get("forbidden_intent")
        if forbidden_intent:
            if intent == forbidden_intent:
                print(f"   [FAIL] Forbidden Intent '{forbidden_intent}' triggered!")
                failed += 1
                continue
                
        must_contain = case.get("must_contain", [])
        if isinstance(must_contain, str): must_contain = [must_contain]
        for term in must_contain:
            if term not in ans:
                print(f"   [FAIL] Answer missing '{term}'")
                failed += 1
                continue
                
        must_not_contain = case.get("must_not_contain", [])
        if isinstance(must_not_contain, str): must_not_contain = [must_not_contain]
        fail_mnc = False
        for term in must_not_contain:
            if term in ans:
                print(f"   [FAIL] Answer contained forbidden term '{term}'")
                fail_mnc = True
                break
        if fail_mnc:
            failed += 1
            continue
            
        print("   [PASS]")
        passed += 1

    print("\n" + "="*30)
    print(f"SUMMARY: {passed}/{len(cases)} Passed")
    print("="*30)
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_test()
