import yaml
import sys
import os
import re
from src.core.chat_engine import ChatEngine

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_tests():
    print("Loading config...")
    cfg = load_config("configs/config.yaml")
    
    print("Initializing ChatEngine...")
    engine = ChatEngine(cfg)
    engine.warmup() 
    
    test_cases = [
        # 1. New UX Policy Tests
        ("add adsl Huawei", "Tutorial (Cap 40, Command-only)"),
        ("แก้ไข ปัญหาโมเด็ม EDIMAX โดน Hack เปลี่ยน PPPoe,DNS", "Nav Rank (PDF First)"),
        ("การทำ Bridge ระหว่างพอร์ตใน Cisco Router", "Directory Mode (Curated Links)"),
        
        # 2. Regression Tests (Old Functionality)
        ("ขอเบอร์ศูนย์ CSOC", "Phone Lookup (Should return numbers)"),
        ("ผส.บลตน. อยู่ที่ไหน", "Location Lookup (Should return location)"),
        ("ASR920", "Metadata Dedup Check")
    ]
    
    for q, desc in test_cases:
        print(f"\n\n\n=== TEST: {desc} ===")
        print(f"Query: {q}")
        
        resp = engine.process(q)
        ans = resp.get("answer", "")
        
        print("\n[ANSWER START]")
        print(ans)
        print("[ANSWER END]")
        
        # Auto-Validation Logic
        passed = True
        notes = []
        
        if q == "add adsl Huawei":
            line_count = len(ans.splitlines())
            if line_count > 60: # 40 content + intro + footer
                 passed = False
                 notes.append(f"FAIL: Too long ({line_count} lines)")
            if "| add adsl" in ans:
                 passed = False
                 notes.append("FAIL: Table row persisted")
            if "เนื้อหาตัดตอน" in ans:
                 notes.append("Info: Truncation applied")
                 
        if "EDIMAX" in q:
             if "Template" in ans or "Convert ASR" in ans:
                  passed = False
                  notes.append("FAIL: Junk links found")
             if "เมนูรวมลิงก์/ไฟล์" not in ans:
                  passed = False
                  notes.append("FAIL: Not in Menu Mode format")
                 
        if "CSOC" in q:
            if "02" not in ans:
                 passed = False
                 notes.append("FAIL: No phone number found")
                 
        status = "PASS" if passed else "FAIL"
        print(f"[RESULT]: {status} {notes}")

if __name__ == "__main__":
    run_tests()
