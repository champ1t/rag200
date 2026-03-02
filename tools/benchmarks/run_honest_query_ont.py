#!/usr/bin/env python3
"""
Honest Citation Demo - Using Real SMC URL
"""
import sys
import time

def simulated_terminal_log_ont_smc():
    query = "ont password"
    ts = time.time()
    session_id = f"SES-{int(ts)}"
    
    print(f"[INFO] Initializing ChatEngine (Config: production)...")
    print(f"[INFO] Loading resources...")
    time.sleep(0.3)
    print(f"[CHAT] LLM warmed up")
    print(f"-" * 60)
    print(f"[PROCESS] Session: {session_id}")
    print(f"[PROCESS] Query: '{query}'")
    
    # 1. Telemetry
    print(f"[TELEMETRY] mode=FULL intent=UNKNOWN")
    print(f"[DEBUG] Regex Hit: 'password' -> Potential CREDENTIAL_LOOKUP")
    
    # 2. Safe Normalizer
    print(f"[SafeNormalizer] Analyzing shape...")
    time.sleep(0.2)
    print(f"[SafeNormalizer] {query} -> HOWTO_PROCEDURE | SINGLE (280ms)")
    
    # 3. Canonical
    print(f"[CHAT] Canonical Rewrite: {query} -> default password ont")
    
    # 4. Routing
    print(f"[ROUTER] Intent: HOWTO_PROCEDURE -> Routing to KnowledgeHandler")
    
    # 5. Retrieval
    print(f"[KnowledgeHandler] Searching VectorDB for 'default password ont'...")
    print(f"[VectorStore] Found 3 candidates (Score: 0.92, 0.72, 0.65)")
    print(f"[Reranker] Boosting 'ONT Password - SMC Article' (Exact Match)")
    
    # 6. Generation
    print(f"[GENERATOR] Policy Check: PUBLIC_DEFAULT_CREDS -> ALLOWED")
    print(f"[GENERATOR] Formatting answer (Template: FACTUAL)...")
    
    answer = """[รหัสผ่านเริ่มต้น ONT (Default Password)]
ข้อมูล:
- Username: admin
- Password: [ดูที่สติกเกอร์ใต้เครื่อง] หรือ tot
- IP Address: 192.168.1.1

แหล่งที่มา:
http://10.192.133.33/smc/index.php?option=com_content&view=article&id=666:ont-password&catid=49:-smc&Itemid=84"""
    
    print(f"[OUTPUT] Answer:\n{answer}")
    print(f"[TELEMETRY] Latency: 0.92s | Tokens: 65")
    print(f"-" * 60)
    print(f"[CITATION] ✓ Traceability Check: PASSED")
    print(f"[CITATION] Source URL is clickable and verifiable")
    print(f"-" * 60)

if __name__ == "__main__":
    simulated_terminal_log_ont_smc()
