
import sys
from src.core.chat_engine import ChatEngine
import yaml

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_governance_check():
    try:
        cfg = load_config("configs/config.yaml")
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)
        
    engine = ChatEngine(cfg)
    print("✅ ChatEngine initialized")
    
    test_cases = [
        # Thai Query
        {
            "query": "ทำไมสายไฟเบอร์ถึงห้ามงอ",
            "required_concept": "แสง",
            "forbidden_intent": "CONTACT_LOOKUP"
        },
        # English Query
        {
            "query": "Why fiber optic cannot bend", 
            "required_concept": "แสง", # Expect Thai concept in answer even if query is English mix
            "forbidden_intent": "CONTACT_LOOKUP"
        }
    ]
    
    all_pass = True
    
    for tc in test_cases:
        q = tc["query"]
        print(f"\n========================================\nTesting: {q}")
        
        # We need to simulate the pipeline or just check the output
        # Since logic is internal, we'll run full process_query
        resp = engine.process(q)
        answer = resp["answer"]
        intent = resp.get("intent", "UNKNOWN")
        route = resp.get("route", "UNKNOWN")
        
        print(f"Intent: {intent}")
        print(f"Route: {route}")
        print(f"Answer Preview: {answer[:50]}...")
        
        # Check Forbidden Intent (Privacy/ Safety)
        if intent == tc["forbidden_intent"]:
            print(f"❌ FAILED: Triggered forbidden intent {intent}")
            all_pass = False
            continue
            
        # Check Required Concept (correctness)
        if tc["required_concept"] not in answer and "light" not in answer.lower():
             print(f"❌ FAILED: Missing concept '{tc['required_concept']}'")
             all_pass = False
             continue
             
        print("✅ PASS")

    if all_pass:
        print("\n🎉 GOVERNANCE CHECK PASSED: System Consistency Verified")
        sys.exit(0)
    else:
        print("\n❌ GOVERNANCE CHECK FAILED")
        sys.exit(1)

if __name__ == "__main__":
    run_governance_check()
