
import json
from src.chat_engine import ChatEngine

def run_production_fixes_verify():
    print("🚀 Initializing Production Fixes Verification...")
    engine = ChatEngine({
        "llm": {
            "model": "llama3.2:3b",
            "temperature": 0.0,
            "base_url": "http://localhost:11434"
        },
        "chat": {"log_level": "INFO"},
        "rag": {"enabled": True},
        "retrieval": {"top_k": 3}
    })

    test_queries = [
        # FIX 1: Ambiguous Role
        "ผจ ชื่ออะไร",
        "ใครคือ ผจ",
        
        # FIX 3: General Ambiguity
        "SBC",
        
        # FIX 4 & 5: LOS Hardening + HOWTO Conceptual Refusal
        "config ONU ยังไง",
        "หลังอัปเดตระบบ LOS ขึ้นทำยังไง"
    ]

    print("\n--- Production Hardening Verification Results ---")
    for q in test_queries:
        print(f"\nQ: {q}")
        try:
            res = engine.process(q)
            print(f"A: {res.get('answer')}")
            print(f"Route: {res.get('route')}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_production_fixes_verify()
