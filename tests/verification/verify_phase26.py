
import sys
import os
sys.path.append(os.getcwd())
from src.core.chat_engine import ChatEngine

def get_config():
    return {
        "model": "llama3.2:3b",
        "base_url": "http://localhost:11434",
        "use_cache": False,
        "retrieval": {
            "top_k": 5,
            "score_threshold": 0.3
        },
        "llm": {
             "model": "llama3.2:3b",
             "base_url": "http://localhost:11434",
             "temperature": 0.2
        },
        "cache": {
             "enabled": False
        },
        "knowledge_pack": {
             "enabled": True
        }
    }

def main():
    print("--- Phase 26 UX Verification ---")
    cfg = get_config()
    engine = ChatEngine(cfg)
    engine.warmup()
    
    # 1. Test Answer Mode Empty
    print("\n[Test 1] Answer Mode Empty (Bras IP -> PHONE ONLY)")
    # Bras IP usually returns IPs, no phones.
    q1 = "Bras IP ขอแค่เบอร์" 
    res1 = engine.process(q1)
    print(f"Q: {q1}")
    print(f"A: {res1['answer']}")
    print(f"Route: {res1.get('route')}")
    
    # 2. Test Invalid Scope
    print("\n[Test 2] Invalid Scope (DNS -> NT3)")
    # First query to set state
    print("Sending 'DNS'...")
    engine.process("DNS") 
    
    # Second query invalid
    q2 = "NT3"
    print(f"Sending '{q2}'...")
    res2 = engine.process(q2)
    print(f"A: {res2['answer']}")
    print(f"Route: {res2.get('route')}")
    
    # 3. Test Valid Scope
    print("\n[Test 3] Valid Scope (DNS -> NT1)")
    # Reset (Technically state cleared, so need to ask DNS again)
    engine.process("DNS")
    q3 = "NT1"
    print(f"Sending '{q3}'...")
    res3 = engine.process(q3)
    print(f"A: {res3['answer']}") # Should match
    print(f"Route: {res3.get('route')}")

if __name__ == "__main__":
    main()
