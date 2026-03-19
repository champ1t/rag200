import time
import random
from datetime import datetime

# ANSI Colors for Professional Terminal Output
BS = "\033[1m" # Bold
R = "\033[91m" # Red
G = "\033[92m" # Green
Y = "\033[93m" # Yellow
B = "\033[94m" # Blue
C = "\033[96m" # Cyan
W = "\033[0m"  # Reset

def log_step(step_num, title):
    print(f"\n{BS}------------- STEP {step_num}: {title} -------------{W}")

def log_info(component, msg, color=W):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{color}[{ts}] [{component}] {msg}{W}")

def simulate_wait(min_ms, max_ms):
    time.sleep(random.uniform(min_ms, max_ms) / 1000)

def run_pipeline_trace(query_text, verify_type="RAG"):
    print("\n" + "="*80)
    print(f" {BS}INCOMING REQUEST: \"{query_text}\"{W}")
    print("="*80)

    # --- STEP 1: INPUT PROCESSING ---
    log_step(1, "INPUT PROCESSING")
    log_info("GATEWAY", f"Received payload. Length: {len(query_text)} chars.", W)
    log_info("SANITIZER", "Input validated. No malicious injection detected.", G)

    # --- STEP 2: ROUTER DECISION ---
    log_step(2, "INTELLIGENT ROUTER")
    simulate_wait(50, 100)
    log_info("ROUTER", "Analyzing intent vectors...", C)
    
    intent = "UNKNOWN"
    route = "UNKNOWN"
    
    if verify_type == "DETERMINISTIC":
        intent = "CONTACT_LOOKUP"
        route = "DETERMINISTIC_ENGINE"
        log_info("ROUTER", f"Detected Intent: {G}{intent}{C}", C)
        log_info("ROUTER", f"Routing Rule: MATCH(Regex 'เบอร์') AND MATCH(Entity 'คุณสมบูรณ์')", C)
        log_info("ROUTER", f"Decision: {G}Route to SQL Engine (High Confidence){W}", C)
        
    elif verify_type == "RAG":
        intent = "KNOWLEDGE_SEARCH"
        route = "VECTOR_RAG"
        log_info("ROUTER", f"Detected Intent: {Y}{intent}{C}", C)
        log_info("ROUTER", "No deterministic hard-rules matched.", Y)
        log_info("ROUTER", f"Decision: {Y}Route to Hybrid RAG (Semantic Search){W}", C)
        
    elif verify_type == "GUARDRAIL_FAIL":
        intent = "OFF_TOPIC"
        log_info("ROUTER", f"Detected Intent: {R}{intent}{C}", C)
        log_info("ROUTER", f"Decision: {R}BLOCK (Policy Violation){W}", C)
        print(f"\n{R}>> SYSTEM REJECTED REQUEST.{W}")
        return

    elif verify_type == "INTERNAL_RAG":
        intent = "TECH_SUPPORT"
        route = "VECTOR_RAG"
        log_info("ROUTER", f"Detected Intent: {C}{intent}{C}", C)
        log_info("ROUTER", f"Knowledge Source: {C}INTERNAL_WIKI (SMC){C}", C)
        log_info("ROUTER", f"Decision: {C}Route to Knowledge Base{W}", C)

    elif verify_type == "CONCEPT_RAG":
        intent = "CONCEPT_EXPLAIN"
        route = "VECTOR_RAG"
        log_info("ROUTER", f"Detected Intent: {G}{intent}{C}", C)
        log_info("ROUTER", f"Decision: {G}Route to General Knowledge (Whitepapers){W}", C)

    elif verify_type == "CISCO_CONFIG":
        intent = "TECH_CONFIG"
        route = "VECTOR_RAG"
        log_info("ROUTER", f"Detected Intent: {B}{intent}{C}", C)
        log_info("ROUTER", f"Decision: {B}Route to Technical Ops Guide{W}", C)

    # --- STEP 3: EXECUTION ---
    log_step(3, f"EXECUTION ({route})")
    
    if verify_type == "DETERMINISTIC":
        simulate_wait(30, 60)
        log_info("SQL_ENG", "Generating Query: SELECT phone FROM contacts WHERE name LIKE '%Somboon%'", B)
        log_info("SQL_ENG", "Database Hit: 1 Record Found.", B)
    
    elif verify_type == "RAG":
        simulate_wait(100, 200)
        log_info("VECTOR_DB", "Embedding query dimensions (1536 dims)...", Y)
        log_info("VECTOR_DB", "Similarity Search (Top-K=3)...", Y)
        log_info("VECTOR_DB", "Context Retrieved: [Document: IT_Policy_2024.pdf (Score: 0.92)]", Y)
        simulate_wait(500, 800)
        log_info("LLM", "Synthesizing answer with Grounding Check...", Y)

    elif verify_type == "LOW_CONFIDENCE":
        simulate_wait(100, 200)
        log_info("VECTOR_DB", "Embedding query dimensions (1536 dims)...", Y)
        log_info("VECTOR_DB", "Similarity Search (Top-K=3)...", Y)
        log_info("VECTOR_DB", f"Context Retrieved: [Doc: Employee_Handbook.pdf (Score: {R}0.45{Y})]", Y)
        log_info("VECTOR_DB", f" ALERT: Retrieval Score below threshold (0.6)", R)

    elif verify_type == "INTERNAL_RAG":
        simulate_wait(100, 200)
        log_info("VECTOR_DB", "Embedding query dimensions (1536 dims)...", Y)
        log_info("VECTOR_DB", "Similarity Search (Top-K=1)...", Y)
        log_info("VECTOR_DB", f"Context Retrieved: [Article ID: 563 (Score: {G}0.95{Y})]", Y)
        log_info("VECTOR_DB", "Title: 'Fix IP Context Private for SMC'", Y)
        simulate_wait(500, 800)
        log_info("LLM", "Synthesizing technical resolution...", Y)

    elif verify_type == "CONCEPT_RAG":
        simulate_wait(100, 200)
        log_info("VECTOR_DB", "Similarity Search (Top-K=2)...", Y)
        log_info("VECTOR_DB", f"Context Retrieved: [Whitepaper: Network_Trends_2025.pdf (Score: {G}0.89{Y})]", Y)
        simulate_wait(800, 1200)
        log_info("LLM", "Synthesizing conceptual explanation...", Y)

    elif verify_type == "CISCO_CONFIG":
        simulate_wait(100, 200)
        log_info("VECTOR_DB", "Similarity Search (Top-K=1)...", Y)
        log_info("VECTOR_DB", f"Context Retrieved: [Doc: Cisco_IR829_Config_Guide.md (Score: {G}0.94{Y})]", Y)
        simulate_wait(600, 900)
        log_info("LLM", "Generating validation steps for Bridge Group...", Y)

    # --- STEP 4: GOVERNANCE & FINAL RESPONSE ---
    log_step(4, "GOVERNANCE & FINAL RESPONSE")
    
    if verify_type == "LOW_CONFIDENCE":
         log_info("HALLUCINATION_GUARD", "Analyzing context sufficiency...", R)
         log_info("HALLUCINATION_GUARD", "Result: INSUFFICIENT DATA. Preventing generation.", R)
         print("-" * 80)
         print(f"{Y}>> RESPONSE: ขออภัยครับ ผมไม่พบข้อมูลเกี่ยวกับเรื่องนี้ในฐานข้อมูลปัจจุบันครับ (Fallback triggered){W}")
         print("-" * 80)
         return

    log_info("GUARDRAILS", "Checking output for PII leakage...", G)
    log_info("GUARDRAILS", "Verification: PASSED.", G)
    log_info("AUDIT_LOG", f"Transaction recorded. Latency: {random.randint(200,800)}ms.", W)
    
    print("-" * 80)
    if verify_type == "DETERMINISTIC":
        print(f"{G}>> RESPONSE: เบอร์โทรคุณสมบูรณ์คือ 081-234-5678 ครับ (Verified by DB){W}")
    elif verify_type == "INTERNAL_RAG":
        print(f"{G}>> RESPONSE: ปัญหานี้แก้ไขได้โดยการตรวจสอบ IP Mapping ตามบทความ 'IP Context Private' ครับ{W}")
        print(f"{G}>> REFERENCE: http://10.192.133.33/smc/index.php?option=com_content&view=article&id=563:ip-context-private&catid=49:-smc&Itemid=84{W}")
    elif verify_type == "CONCEPT_RAG":
        print(f"{G}>> RESPONSE: โครงสร้างเดิมไม่รองรับ Latency ต่ำและ Real-time AI Processing จึงต้องขยับไปสู่ Intelligent Mesh และ Edge Computing ครับ{W}")
        print(f"{G}>> SOURCE: Network Trends 2025 – Intelligent Architecture{W}")
        print(f"{G}>> LINK: http://10.192.133.33/docs/whitepapers/Network_Trends_2025.pdf{W}")
    elif verify_type == "CISCO_CONFIG":
        print(f"{G}>> RESPONSE: ใช้คำสั่ง `bridge irb` เพื่อเปิดใช้งาน และกำหนด `bridge-group <id>` ที่ interface ครับ{W}")
        print(f"{G}>> SOURCE: Cisco IR829 Configuration Guide – Bridge Groups{W}")
        print(f"{G}>> LINK: http://10.192.133.33/docs/cisco/IR829_Config_Guide.html#bridge-groups{W}")
    else:
        print(f"{G}>> RESPONSE: คุณสามารถรีเซ็ตรหัสผ่านได้ที่หน้าเว็บ portal.company.com ครับ{W}")
        print(f"{G}>> REFERENCE: http://10.192.133.33/docs/policies/IT_Policy_2024.pdf{W}")
    print("-" * 80)
    return

if __name__ == "__main__":
    # 1. Deterministic
    run_pipeline_trace("ขอเบอร์โทรคุณสมบูรณ์ แผนก IT ครับ", verify_type="DETERMINISTIC")
    time.sleep(1)
    
    # 2. Tech Support (Internal Wiki)
    run_pipeline_trace("ขอวิธีแก้ user สำหรับลูกค้า context private หน่อย", verify_type="INTERNAL_RAG")
    time.sleep(1)

    # 3. Concept (Trend)
    run_pipeline_trace("ทำไม Core, Distributed, Edge ถึงไม่เพียงพออีกต่อไป", verify_type="CONCEPT_RAG")
    time.sleep(1)

    # 4. Config (Cisco)
    run_pipeline_trace("การทำ Bridge ระหว่างพอร์ตใน Cisco Router", verify_type="CISCO_CONFIG")

