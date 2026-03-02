import yaml
import sys
import os
from src.core.chat_engine import ChatEngine

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    print("Loading config...")
    cfg = load_config("configs/config.yaml")
    
    print("Initializing ChatEngine (this usually takes 5-10s)...")
    engine = ChatEngine(cfg)
    engine.warmup() # Load models/resources
    
    queries = [
        "add adsl Huawei",
        "แก้ไข ปัญหาโมเด็ม EDIMAX โดน Hack เปลี่ยน PPPoe,DNS",
        "การทำ Bridge ระหว่างพอร์ตใน Cisco Router"
    ]
    
    for q in queries:
        print(f"\n\n\n=== TEST QUERY: {q} ===")
        # Use engine.process(q) which mimics main.py logic (returns dict with answer)
        resp = engine.process(q)
        
        print("\n[ANSWER START]")
        print(resp.get("answer", "No answer field"))
        print("[ANSWER END]")
        
        # Debug info
        rt = resp.get("route", "unknown")
        print(f"[DEBUG] Route: {rt}")

if __name__ == "__main__":
    main()
