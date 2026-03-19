import requests
import json
import time

API_URL = "http://localhost:8000/chat"
HEADERS = {
    "X-API-Key": "nt-rag-secret",
    "Content-Type": "application/json"
}

def log_result(test_name, status, details=""):
    icon = "✅" if status == "PASS" else ("⚠️" if status == "WARN" else "❌")
    print(f"{icon} [{test_name}] {status}: {details}")

def run_chat(message, session, expected_phrases=[], forbidden_phrases=[], min_len=0, max_len=99999):
    try:
        payload = {
            "message": message,
            "user": "gate_tester",
            "session_id": session,
            "top_k": 3
        }
        t0 = time.time()
        resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=15)
        latency = (time.time() - t0) * 1000
        
        if resp.status_code != 200:
            return "FAIL", f"HTTP {resp.status_code}", ""
            
        data = resp.json()
        ans = data.get("answer", "")
        
        # Validation
        if len(ans) < min_len:
            return "WARN", f"Too short ({len(ans)} chars)", ans
        if len(ans) > max_len:
            return "WARN", f"Too long ({len(ans)} chars)", ans
            
        for phrase in expected_phrases:
            if phrase not in ans:
                return "FAIL", f"Missing '{phrase}'", ans
                
        for phrase in forbidden_phrases:
            if phrase in ans:
                return "FAIL", f"Found forbidden '{phrase}'", ans
                
        return "PASS", f"Lat={latency:.0f}ms", ans
        
    except Exception as e:
        return "FAIL", str(e), ""

def test_human_language():
    print("\n=== 1. Human Language Test ===")
    
    # 1.1 "วิธีแก้ tr069" -> Should fallback to TR069 content or polite fail
    status, reason, ans = run_chat("วิธีแก้ tr069", "sess_human", 
                                   expected_phrases=[]) 
    # Note: Likely to get "Coverage Check FAILED" or TR069 content.
    # Passing condition: No Error, Polite Response.
    is_safe = "ไม่พบข้อมูล" in ans or "[TR069" in ans
    log_result("Naive 'วิธีแก้ tr069'", "PASS" if is_safe else "WARN", f"Ans start: {ans[:30]}...")

    # 1.2 "เข้าเว็บ edoc"
    status, reason, ans = run_chat("เข้าเว็บ edoc", "sess_human", expected_phrases=[])
    is_safe = "ไม่พบข้อมูล" in ans or "http" in ans
    log_result("Naive 'เข้าเว็บ edoc'", "PASS" if is_safe else "WARN", f"Ans start: {ans[:30]}...")
    
    # 1.3 "huawei fttx มีปัญหา"
    status, reason, ans = run_chat("huawei fttx มีปัญหา", "sess_human", expected_phrases=[])
    # Should get Huawei content or fall back
    is_safe = "Huawei" in ans or "ไม่พบข้อมูล" in ans
    log_result("Naive 'huawei fttx...'", "PASS" if is_safe else "WARN", f"Ans start: {ans[:30]}...")

    # 1.4 "ip ssh คืออะไร" (Concept)
    status, reason, ans = run_chat("ip ssh คืออะไร", "sess_human", expected_phrases=[])
    is_safe = "SSH" in ans or "ไม่พบข้อมูล" in ans
    log_result("Naive 'ip ssh...'", "PASS" if is_safe else "WARN", f"Ans start: {ans[:30]}...")

def test_deterministic():
    print("\n=== 2. Same Question, Different Style ===")
    
    # Check if they map to same article (approx)
    q1 = "TR069 CWMP Setting"
    q2 = "ตั้งค่า TR069"
    
    s1, r1, a1 = run_chat(q1, "sess_det_1", expected_phrases=["TR069"])
    s2, r2, a2 = run_chat(q2, "sess_det_2", expected_phrases=[])
    
    # We expect both to be useful. Not necessarily identical chars (diff retrieval score), 
    # but same TOPIC (Title in brackets).
    
    title1 = a1.split('\n')[0] if a1 else ""
    title2 = a2.split('\n')[0] if a2 else ""
    
    print(f"   Q1 Title: {title1}")
    print(f"   Q2 Title: {title2}")
    
    if title1 == title2 and title1.startswith("["):
        log_result("Deterministic Title", "PASS", f"Both got {title1}")
    else:
        # If Q2 failed to find it?
        if "ไม่พบข้อมูล" in a2:
             log_result("Deterministic Title", "WARN", "Q2 missed article")
        else:
             log_result("Deterministic Title", "WARN", "Different articles/formats")

def test_session_safety():
    print("\n=== 3. Long Session Test (State Safety) ===")
    session = "sess_long_1"
    
    # Step 1: SBC
    log_result("Step 1: Ask SBC", "INFO", "...")
    s, r, a1 = run_chat("SBC", session, expected_phrases=["SBC", "Session", "Border"])
    if s != "PASS": log_result("SBC Query", s, r)
    
    # Step 2: IP SSH (Switch Context)
    log_result("Step 2: Switch to IP SSH", "INFO", "...")
    s, r, a2 = run_chat("ขอ IP SSH Server", session, expected_phrases=["SSH", "10."])
    if s != "PASS": log_result("SSH Query", s, r)
    
    # Verify A2 doesn't have SBC info
    if "SBC" in a2 and len(a2) < 500: # If short, shouldn't mention SBC
         log_result("Context Leak Check", "WARN", "Found 'SBC' in SSH answer?")
    else:
         log_result("Context Leak Check", "PASS", "Clean switch")
         
    # Step 3: Return to SBC
    log_result("Step 3: Return to SBC", "INFO", "...")
    s, r, a3 = run_chat("SBC คืออะไร", session, expected_phrases=["SBC"])
    
    # Verify A3 doesn't have SSH info
    if "SSH" in a3 and len(a3) < 500:
         log_result("Context Return Check", "WARN", "Found 'SSH' in SBC answer?")
    else:
         log_result("Context Return Check", "PASS", "Clean return")

def test_garbage_edge():
    print("\n=== 5. Garbage / Edge Input ===")
    
    # 5.1 Empty/Space
    s, r, a = run_chat("   ", "sess_edge")
    log_result("Empty Input", "PASS" if "ไม่พบ" in a or "ขออภัย" in a or len(a)<100 else "WARN", f"Ans: {a[:30]}")
    
    # 5.2 Numbers
    s, r, a = run_chat("123456", "sess_edge")
    log_result("Numeric Input", "PASS" if "ไม่พบ" in a or len(a)<100 else "WARN", f"Ans: {a[:30]}")
    
    # 5.3 Long Text (Lorem Ipsum simulation)
    # long_text = "test " * 500
    # s, r, a = run_chat(long_text, "sess_edge")
    # # Should not crash.
    # log_result("Long Input (2500 chars)", "PASS" if s != "FAIL" else "FAIL", f"Status: {r}")

def test_cache_consistency():
    print("\n=== 4. Cache Consistency (Snapshotted) ===")
    # Query Ribbon (Directory) which uses specific formatting
    s, r, ans = run_chat("Ribbon EdgeMare6000 DOC", "sess_cache")
    if s == "PASS":
        # Check Title
        has_title = "[Ribbon EdgeMare6000 DOC]" in ans
        has_link = "http" in ans
        log_result("Ribbon Output Check", "PASS" if (has_title and has_link) else "FAIL", 
                   f"Title found: {has_title}, Link found: {has_link}")
        # Save snapshot signature
        sig = ans[:50].replace('\n', ' ')
        print(f"   Signature: {sig}")
        return sig
    else:
        log_result("Ribbon Output Check", "FAIL", r)
        return None

if __name__ == "__main__":
    test_human_language()
    test_deterministic()
    test_session_safety()
    test_garbage_edge()
    test_cache_consistency()
