
import json
from src.core.chat_engine import ChatEngine

def run_refinement_test():
    print("🚀 Initializing Refined RAG Engine...")
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
        "LOS คืออะไร",
        "เบอร์ไฟเบอร์คืออะไร",
        "LOS เกิดจาก software bug ได้ไหม",
        "แก้ LOS ยังไง",
        "หลักการทำงาน"
    ]

    print("\n--- Refinement Verification Results ---")
    for q in test_queries:
        print(f"\nQ: {q}")
        try:
            res = engine.process(q)
            print(f"A: {res.get('answer')}")
            print(f"Route: {res.get('route')}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_refinement_test()
