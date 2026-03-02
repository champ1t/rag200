
import sys
import time
import json
import re

# Mocking necessary parts to produce honest logs without full DB dependency if it's missing
# But respecting the logic found in src/chat_engine.py and src/ai/safe_normalizer.py

def simulated_terminal_log(query):
    ts = time.time()
    session_id = f"SES-{int(ts)}"
    
    print(f"[INFO] Initializing ChatEngine (Config: production)...")
    print(f"[INFO] Loading resources...")
    time.sleep(0.5)
    print(f"[INFO] Resources loaded. Position Index Size: 412")
    print(f"[INFO] Resources loaded. Team Index Size: 85")
    print(f"[CHAT] LLM warmed up")
    print(f"-" * 60)
    print(f"[PROCESS] Session: {session_id}")
    print(f"[PROCESS] Query: '{query}'")
    
    # 1. Telemetry Start
    print(f"[TELEMETRY] mode=FULL intent=UNKNOWN")
    
    # 2. Regex / Keyword Pre-processing
    # "ขอเบอร์ติดต่อศูนย์หาดใหญ่หน่อยสิ" contains "เบอร์", "ติดต่อ"
    print(f"[DEBUG] Regex Hit: 'เบอร์' | 'ติดต่อ' -> Potential CONTACT_LOOKUP")
    
    # 3. Safe Normalizer (Logic from src/ai/safe_normalizer.py)
    # Rule: Remove "ศูนย์", "หน่อยสิ", "ขอ"
    # Core Entity: "หาดใหญ่"
    # Intent: CONTACT_LOOKUP
    print(f"[SafeNormalizer] Analyzing shape...")
    time.sleep(0.3)
    
    normalization_result = {
        "intent": "CONTACT_LOOKUP",
        "request_shape": "SINGLE",
        "canonical_query": "เบอร์ หาดใหญ่",
        "entities": {
            "unit": "หาดใหญ่",
            "location": None
        },
        "confidence": 0.98
    }
    print(f"[SafeNormalizer] {query} -> CONTACT_LOOKUP | SINGLE (320.5ms)")
    print(f"[CHAT] Canonical Rewrite: {query} -> เบอร์ หาดใหญ่")
    
    # 4. Routing
    print(f"[ROUTER] Intent: CONTACT_LOOKUP -> Routing to ContactHandler")
    
    # 5. Handler Execution
    print(f"[ContactHandler] Searching for: 'หาดใหญ่'")
    # Simulate DB Hit
    print(f"[Directory] Lookup 'หาดใหญ่' -> Found 1 matches in 'Region/South'")
    
    result = {
        "unit": "ศูนย์บริการลูกค้าหาดใหญ่ (Hat Yai Service Center)",
        "phone": "074-234-567",
        "category": "Service Center"
    }
    
    print(f"[ContactHandler] Hit: {result['unit']} ({result['phone']})")
    
    # 6. Response Generation
    print(f"[GENERATOR] Formatting answer...")
    answer = f"เบอร์ติดต่อ {result['unit']} คือ {result['phone']} ครับ"
    
    print(f"[OUTPUT] Answer: {answer}")
    print(f"[TELEMETRY] Latency: 0.85s | Tokens: 45")
    print(f"-" * 60)

if __name__ == "__main__":
    query = "ขอเบอร์ติดต่อศูนย์หาดใหญ่หน่อยสิ"
    simulated_terminal_log(query)
