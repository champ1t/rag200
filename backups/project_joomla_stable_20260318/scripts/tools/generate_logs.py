
import sys
import os
import random
import time
sys.path.append(os.getcwd())
from src.core.chat_engine import ChatEngine

def get_config():
    return {
        "model": "llama3.2:3b",
        "base_url": "http://localhost:11434",
        "use_cache": False,
        "retrieval": {"top_k": 3, "score_threshold": 0.3},
        "llm": {"model": "llama3.2:3b", "base_url": "http://localhost:11434", "temperature": 0.2},
        "chat": {"save_log": True}, # Enable logging
        "knowledge_pack": {"enabled": True},
        "cache": {"enabled": False}
    }

def main():
    print("--- Generating Telemetry Data ---")
    engine = ChatEngine(get_config())
    engine.warmup()
    
    queries = [
        "DNS", "DNS NT1", "DNS HYI", "DNS BKK", 
        "SMTP", "SMTP NT1", 
        "Bras IP", "Bras IP ขอแค่เบอร์", "Bras IP ขอแค่ IP",
        "NOC", "NOC เบอร์",
        "วิธีแก้ไขเน็ตเสีย", "เปลี่ยนรหัส wifi", # Procedural / RAG
        "InvalidScopeTest", "NT3", # Noise
        "Test" # Quick reply
    ]
    
    # Run loop
    for _ in range(30):
        q = random.choice(queries)
        print(f"> {q}")
        try:
            # Simulate latency variation
            time.sleep(random.uniform(0.1, 0.5))
            engine.process(q)
        except Exception as e:
            print(f"Error: {e}")
            
    print("Done generating logs.")

if __name__ == "__main__":
    main()
