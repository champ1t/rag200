
import json
from src.core.chat_engine import ChatEngine

def run_role_test():
    print("🚀 Initializing Role Policy Test...")
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
        "ผจ",
        "ใครคือ ผอ",
        "ผจ ยโสธร",
        "หัวหน้า",
        "ผจก.เขต"
    ]

    print("\n--- Role Ambiguity Policy Results ---")
    for q in test_queries:
        print(f"\nQ: {q}")
        try:
            res = engine.process(q)
            print(f"A: {res.get('answer')}")
            print(f"Route: {res.get('route')}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_role_test()
