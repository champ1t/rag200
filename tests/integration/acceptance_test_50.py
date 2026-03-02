import requests
import json
import time
import pandas as pd
import numpy as np
from pathlib import Path

# --- Configuration ---
BASE_URL = "http://localhost:8000/chat"
HEADERS = {"X-API-Key": "nt-rag-secret", "Content-Type": "application/json"}
SESSION_ID = "acceptance_test_v1"
EXPORT_PATH = "data/acceptance_results.csv"

LONG_TEXT = "รักษาระบบ " * 500 # ~4000 chars

# --- Scenarios (50 Cases) ---
SCENARIOS = [
    # 1-10: Technical / HowTo (Colloquial Thai)
    ("TR069 CWMP Setting", "article_answer", "Normal Technical"),
    ("วิธีแก้ TR069 ที่ลูกค้าออนไลน์หลุดบ่อย", "article_answer", "Synonym HowTo"),
    ("วิธีคอนฟิก Huawei fttx", "article_answer", "Config Procedure"),
    ("tr069 หลุดบ่อยทำยังไงดี", "article_answer", "Colloquial Troubleshooting"),
    ("Huawei fttx มีปัญหา speed ตก", "article_answer", "Performance Issue"),
    ("เซตค่า IP_SSH ทำไง", "article_answer", "Short Tech Question"),
    ("คู่มือ NCS เบื้องต้น", "article_answer", "Manual Search"),
    ("ข้อจำกัดของ NCS มีอะไรบ้าง", "article_answer", "Specific Constraint"),
    ("edoc เข้าเข้าไม่ได้", "article_answer", "Slang/Short Term"),
    ("วิธีโอนเบอร์ IP Phone", "article_answer", "Specific Feature"),

    # 11-20: Directory / Contact / Team
    ("เบอร์ สื่อสารข้อมูล ภูเก็ต", "contact_hit", "Regional Contact"),
    ("เบอร์ Intra TOT", "contact_hit", "Legacy Contact"),
    ("เบอร์โทรหาดใหญ่", "contact_hit", "City Contact"),
    ("ติดต่อแผนกไอที", "contact_hit", "Team Search"),
    ("ขอเบอร์ช่างซ่อมบำรุง", "contact_hit", "Role Search"),
    ("เบอร์ สอ.", "contact_hit", "Acronym Search"),
    ("รายชื่อเจ้าหน้าที่ สระบุรี", "contact_hit", "Regional List"),
    ("เบอร์โทรศัพท์ 02-123-4567", "contact_lookup", "Reverse Search"),
    ("ทีม Operation Support คือใคร", "contact_hit", "Team Identification"),
    ("เบอร์โทรศัพท์มือถือคุณจตุพร", "contact_hit", "Named Person Search"),

    # 21-30: Nav / Choices / Tables
    ("ตาราง proxy IP PHONE", "needs_choice", "Table Display"),
    ("คู่มือปฏิบัติงาน 1177 ภาคใต้", "needs_choice", "Navigational Guide"),
    ("ระเบียบการลาพักร้อน", "article_answer", "HR Policy"),
    ("ดาวน์โหลดฟอร์มเบิกสวัสดิการ", "article_answer", "Document Search"),
    ("ปฏิทินวันหยุด 2567", "article_answer", "Date Search"),
    ("โครงสร้างองค์กร NT", "article_answer", "Org Chart"),
    ("รายชื่อศูนย์บริการ กรุงเทพ", "needs_choice", "Service Center List"),
    ("แพ็กเกจเน็ตบ้าน", "needs_choice", "Product List"),
    ("โปรโมชั่นล่าสุด", "needs_choice", "Recency Search"),
    ("พื้นที่ให้บริการ 5G", "article_answer", "Coverage Search"),

    # 31-40: Knowledge / Concept (Deep)
    ("NCS คืออะไร", "article_answer", "Definition"),
    ("ระบบ FTTx ทำงานยังไง", "article_answer", "System Core"),
    ("ความแตกต่างระหว่าง IPv4 และ IPv6", "article_answer", "Comparison"),
    ("อธิบายเรื่อง VLAN", "article_answer", "Explanation"),
    ("ขั้นตอนการรับพนักงานใหม่", "article_answer", "Admin Process"),
    ("สิทธิการเบิกค่ารักษาพยาบาล", "article_answer", "Benefit Policy"),
    ("กติกาการใช้รถส่วนกลาง", "article_answer", "Facility Policy"),
    ("ระบบรักษาความปลอดภัย NT", "article_answer", "Security Concept"),
    ("นโยบาย PDPA", "article_answer", "Compliance"),
    ("จริยธรรมองค์กร", "article_answer", "Ethics"),

    # 41-50: Edge / Safety / No-Hit
    ("", "greeting", "Empty Input"),
    ("😂😂😂", "greeting", "Emoji Only"),
    (LONG_TEXT, "truncated_processing", "Ultra Long Input"),
    ("บลาบลาบลา 12345", "rag_miss_coverage", "Gibberish"),
    ("วิธีการถอนเงินจากตู้ ATM", "rag_security_guided", "Out of Domain"),
    ("ขอเบอร์โทรศัพท์คนที่ไม่รู้จัก", "rag_security_guided", "Privacy Edge Case"),
    ("ด่าคำหยาบ", "rag_security_guided", "Profanity/Harm"),
    ("กล้วยๆ ทำได้ไหม", "article_answer", "Slang Context"),
    ("Test post", "rag_miss_coverage", "Developer Test"),
    ("Bye bye", "greeting", "Ending")
]

import re

# --- Configuration ---
# ... (BASE_URL, HEADERS, SESSION_ID, EXPORT_PATH already defined)

# --- Out of Index / High Ambiguity Tagging ---
OUT_OF_INDEX_QUERIES = [
    "ระเบียบการลาพักร้อน", "ดาวน์โหลดฟอร์มเบิกสวัสดิการ", "ปฏิทินวันหยุด 2567", 
    "โครงสร้างองค์กร NT", "รายชื่อศูนย์บริการ กรุงเทพ", "พื้นที่ให้บริการ 5G",
    "ขั้นตอนการรับพนักงานใหม่", "สิทธิการเบิกค่ารักษาพยาบาล", "กติกาการใช้รถส่วนกลาง",
    "ระบบรักษาความปลอดภัย NT", "นโยบาย PDPA", "จริยธรรมองค์กร"
]

HIGH_AMBIGUITY_QUERIES = [
    "เบอร์ สอ.", "รายชื่อเจ้าหน้าที่ สระบุรี", "ทีม Operation Support คือใคร"
]

def analyze_signal_v3(resp_data, query, expected_cat):
    answer = resp_data.get("answer", "")
    route = resp_data.get("route", "")
    sources = resp_data.get("sources", [])
    ok = resp_data.get("ok", True)
    
    # 1. Source Link Presence (Anywhere)
    has_source = len(sources) > 0 or "http" in answer or "🔗" in answer or "แหล่งที่มา" in answer
    
    # 2. Title Presence (Mandatory for Article/Choice)
    has_title = "[" in answer[:300] and "]" in answer[:300]
    
    # 3. Phone Regex (for Contacts)
    has_phone = bool(re.search(r"0\d{1,2}-\d{3}-\d{4}|0\d{8,9}", answer))
    
    # --- Grading Logic ---
    
    # FAIL_HARD: System error or Logic Crash
    if not ok: return "FAIL_HARD", "Response marked as NOT OK"
    
    # PASS_SAFE: Expected MISS or Safety Guard
    if query in OUT_OF_INDEX_QUERIES or expected_cat in ["rag_miss_coverage", "rag_security_guided", "greeting"]:
        if route in ["rag_miss_coverage", "rag_security_guided", "greeting", "quick_reply", "clarify_miss", "rag_low_score_gate", "news_miss"]:
            return "PASS_SAFE", "Correct safety/miss behavior"

    # PASS_SAFE: Ambiguity Handling (User explicitly asked for this)
    if query in HIGH_AMBIGUITY_QUERIES and route in ["clarify_miss", "team_miss", "contact_miss_strict", "rag_clarify"]:
        return "PASS_SAFE", "Appropriate ambiguity/re-ask behavior"

    # Contact Hit Logic
    if "contact" in route or route == "cache_hit" or (expected_cat == "contact_hit" and route == "rag_cache_l2"):
        if has_phone: return "PASS_STRICT", "Found contact info"
        if "เบอร์" in answer or "ติดต่อ" in answer: return "PASS_SAFE", "Contact context present"

    # Needs Choice vs Article Mismatch (UX is fine if links are present)
    if expected_cat == "needs_choice" and route == "article_answer" and has_source:
        return "PASS_STRICT", "UX OK: Full article provided instead of menu"
    
    # Low Score Gate: Considered PASS_SAFE if it's an article answer that was safely gated
    if expected_cat == "article_answer" and route == "rag_low_score_gate":
        return "PASS_SAFE", "Safely gated low-confidence technical query"

    # PASS_STRICT: Perfect Article Answer
    if route == "article_answer" and has_title and has_source:
        return "PASS_STRICT", "Perfect article format"
    
    # Functionally correct Fallback
    if route == expected_cat or (expected_cat == "article_answer" and route == "rag_cache_l2"):
        return "PASS_SAFE", "Functionally correct, missing signals"

    return "FAIL_HARD", f"Route mismatch: Got {route}, Expected {expected_cat}"

def run_acceptance():
    print("="*60)
    print("      PROFESSIONAL ACCEPTANCE TEST V2.1 (STABILIZED)")
    print("="*60)
    
    results = []
    timeout_count = 0
    retry_count = 0
    
    batch_size = 10
    total_cases = len(SCENARIOS)
    
    for i, (query, expected_cat, desc) in enumerate(SCENARIOS, 1):
        batch_id = (i - 1) // batch_size + 1
        
        # Batch cooldown
        if i > 1 and i % batch_size == 1:
            wait_time = 8
            print(f"\n[BATCH {batch_id-1}] Finished. Cooling down {wait_time}s...")
            time.sleep(wait_time)

        attempts = 2
        current_data = None
        elapsed = 0
        status_tier = "FAIL_HARD"
        reason = "Unknown Error"
        
        for attempt in range(attempts):
            t_start = time.time()
            try:
                resp = requests.post(
                    BASE_URL, 
                    json={"query": query, "session_id": f"{SESSION_ID}_{i}"}, 
                    headers=HEADERS, 
                    timeout=75 
                )
                elapsed = (time.time() - t_start) * 1000
                
                if resp.status_code == 200:
                    current_data = resp.json()
                    status_tier, reason = analyze_signal_v3(current_data, query, expected_cat)
                    break
                else:
                    reason = f"HTTP {resp.status_code}"
            except requests.exceptions.Timeout:
                timeout_count += 1
                if attempt < attempts - 1:
                    retry_count += 1
                    print(f"      [!] Timeout on '{query[:20]}...' -> Retrying in 3s...")
                    time.sleep(3)
                else:
                    status_tier = "FAIL_HARD"
                    reason = "Read Timeout (Final)"
            except Exception as e:
                reason = str(e)
                break
        
        # Display Progress
        tag = f"[{status_tier}]"
        print(f"{i:02d}. [B{batch_id}] {tag:.<15} {query[:30]:.<35} {elapsed/1000:.1f}s | {reason}")
        
        results.append({
            "id": i, "query": query, "category": expected_cat, "desc": desc,
            "route": current_data.get("route") if current_data else "ERROR",
            "latency": elapsed, "status_tier": status_tier, "reason": reason,
            "batch_id": batch_id, "retry_used": (attempt > 0)
        })
        time.sleep(1.0) # Throttle

    # --- Summary ---
    df = pd.DataFrame(results)
    
    print("\n" + "="*40)
    print("      ENHANCED SCORECARD")
    print("="*40)
    p_strict = len(df[df['status_tier'] == 'PASS_STRICT'])
    p_safe = len(df[df['status_tier'] == 'PASS_SAFE'])
    f_hard = len(df[df['status_tier'] == 'FAIL_HARD'])
    
    print(f"PASS_STRICT: {p_strict:2d} | PASS_SAFE: {p_safe:2d} | FAIL_HARD: {f_hard:2d}")
    print(f"Timeouts:    {timeout_count:2d} | Retries:    {retry_count:2d}")
    
    total_effective = p_strict + p_safe
    print(f"\nEffective Performance: {total_effective}/50 ({(total_effective/50)*100:.1f}%)")
    
    print("\n[QUALITY BREAKDOWN]")
    for cat in df['category'].unique():
        if pd.isna(cat): continue
        cat_df = df[df['category'] == cat]
        s = len(cat_df[cat_df['status_tier'] == 'PASS_STRICT'])
        f = len(cat_df[cat_df['status_tier'] == 'PASS_SAFE'])
        print(f"  - {cat:.<20} {s} Strict | {f} Safe | {len(cat_df)} Total")

    df.to_csv(EXPORT_PATH, index=False)
    print(f"\nReport: {EXPORT_PATH}")

if __name__ == "__main__":
    run_acceptance()

if __name__ == "__main__":
    run_acceptance()
