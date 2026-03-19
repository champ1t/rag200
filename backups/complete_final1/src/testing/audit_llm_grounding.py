
import sys
import os
import yaml
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.core.chat_engine import ChatEngine

def load_config(path: str):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def test_strict_grounding():
    print("Loading Config...")
    cfg = load_config("configs/config.yaml")
    print("Initializing ChatEngine...")
    engine = ChatEngine(cfg)
    
    # Queries that SHOULD NOT be answered (Out of Domain)
    # The system should answer with "Not found" or similar, NOT generic knowledge.
    out_of_domain_queries = [
        "What is the capital of France?",
        "เขียน Python ให้ดูหน่อย", 
        "สูตรทำกะเพราไก่",
        "Elon Musk คือใคร"
    ]
    
    print("\n=== Testing Strict Grounding (Anti-Hallucination) ===\n")
    
    failures = 0
    
    for q in out_of_domain_queries:
        print(f"Q: {q}")
        res = engine.process(q)
        ans = res.get("answer", "")
        print(f"A: {ans}")
        
        # Check output
        # We expect a refusal or "Not Found"
        refusal_keywords = ["ไม่พบข้อมูล", "No information", "not found", "ไม่มีข้อมูล"]
        is_refusal = any(k in ans for k in refusal_keywords)
        
        if not is_refusal:
            print("[FAIL] System answered an out-of-domain query!")
            failures += 1
        else:
            print("[PASS] System correctly refused.")
            
        print("-" * 30)
        
    if failures > 0:
        print(f"\n[FAIL] Strict Grounding Verification Failed ({failures} failures). System is too chatty.")
        sys.exit(1)
    else:
        print("\n[PASS] Strict Grounding Verification Passed. System only knows what is in the Context.")

if __name__ == "__main__":
    test_strict_grounding()
