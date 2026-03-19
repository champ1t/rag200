
import sys
import os

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from src.core.chat_engine import ChatEngine

import yaml

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_prompts():
    print("🚀 Initializing ChatEngine for Prompt Validation...")
    cfg = load_config("configs/config.yaml")
    engine = ChatEngine(cfg)
    
    test_cases = [
        {"q": "OLT คืออะไร", "desc": "Definition Check (Expected: DEFINE_TERM logic)"},
        {"q": "ต่อสาย ONU ยังไง", "desc": "Procedure Check (Expected: HOWTO/FACTUAL logic)"},
        {"q": "5ส คืออะไร", "desc": "Org Knowledge Check (Expected: THAI_ORG_KNOWLEDGE)"},
        {"q": "ขอเบอร์ NOC", "desc": "Contact Check (Expected: CONTACT)"},
        {"q": "ไฟ LOS แดง ต้องเช็คยังไง", "desc": "Field Concept Check (Expected: FIELD_CONCEPT_REASONING logic)"}
    ]

    print(f"🔍 Running {len(test_cases)} validation queries...\n")

    for case in test_cases:
        query = case["q"]
        print(f"--------------------------------------------------")
        print(f"🧪 Testing: {query}")
        print(f"ℹ️  Goal: {case['desc']}")
        
        try:
            # Process query
            res = engine.process(query)
            
            # Extract details
            answer = res.get("answer", "")
            route = res.get("route", "unknown")
            intent = res.get("intent", "unknown")
            context = res.get("context", [])
            
            print(f"📍 Route: {route}")
            print(f"🧠 Intent: {intent}")
            print(f"📄 Context Count: {len(context)}")
            print(f"💬 Answer Preview (First 300 chars):")
            print(f"{answer[:300]}...")
            
            # Basic validation checks
            print("\n✅ Internal Checks:")
            
            # Check 1: Hallucination / Source
            if "ที่มา" in answer or "Source" in answer or "ไม่พบข้อมูล" in answer:
                print("   [PASS] Source attribution or Not Found handled.")
            else:
                print("   [WARN] No explicit source attribution found.")
                
            # Check 2: Tone/Language
            if "โดยทั่วไป" in answer or "มักจะ" in answer or "เป็นไปได้" in answer:
                 print("   [INFO] Generality language detected.")
            
            # Specific checks
            if "OLT" in query and "คือ" in query:
                # Check if it didn't just hallucinate a random definition
                pass 
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            
        print("\n")

if __name__ == "__main__":
    test_prompts()
