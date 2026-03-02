import yaml
from src.core.chat_engine import ChatEngine

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def verify_contact_v221():
    print("=== Verifying Contact Assistant (Phase 221) ===")
    
    cfg = load_config("configs/config.yaml")
    # Mock LLM to avoid real calls? Or use real one? 
    # Use real one to test TEMPLATE_CONTACT formatting.
    # Ensure Ollama is running.
    
    engine = ChatEngine(cfg)
    
    # Test 1: Ambiguous -> Disambiguation State
    print("\n--- Test 1: Ambiguous Query (CSOC) ---")
    q1 = "ขอเบอร์ CSOC"
    res1 = engine.process(q1)
    print(f"Answer:\n{res1['answer']}")
    
    if "ใกล้เคียงกันหลายรายการ" not in res1['answer']:
        print("[FAIL] Expected ambiguous prompt.")
    else:
        print("[PASS] Ambiguous prompt received.")
        
    if not engine.pending_contact_clarify:
        print("[FAIL] State not set.")
    else:
        print(f"[PASS] State set. Candidates: {len(engine.pending_contact_clarify['choices'])}")
        
    # Test 2: Disambiguation Reply (1)
    print("\n--- Test 2: Reply '1' ---")
    q2 = "1"
    res2 = engine.process(q2)
    print(f"Answer:\n{res2['answer']}")
    
    if "เบอร์โทร:" not in res2['answer']:
         print("[FAIL] Expected HIT format.")
    else:
         print("[PASS] Received HIT format.")
         
    if engine.pending_contact_clarify:
        print("[FAIL] State not cleared.")
    else:
        print("[PASS] State cleared.")

    # Test 3: New Search (Invalid Name) -> Should be Miss or new Hit
    print("\n--- Test 3: New Search (Reset State) ---")
    # First set state again
    engine.process("ขอเบอร์ CSOC") 
    
    print("Sending 'เบอร์แม่บ้าน' (Should ignore CSOC choices and search new)")
    q3 = "เบอร์แม่บ้าน" 
    res3 = engine.process(q3)
    print(f"Answer:\n{res3['answer']}")
    
    if "CSOC" in res3['answer']:
        print("[FAIL] Seems to have stuck to previous choices.")
    else:
        print("[PASS] Treated as new query.")

    # Test 4: Strict Miss
    print("\n--- Test 4: Strict Miss ---")
    q4 = "ขอเบอร์มนุษย์ต่างดาว"
    res4 = engine.process(q4)
    print(f"Answer:\n{res4['answer']}")
    
    if "ไม่พบข้อมูล" not in res4['answer'] or "ช่วยระบุ" not in res4['answer']:
        print("[FAIL] Miss format incorrect.")
    else:
        print("[PASS] Miss format correct.")

if __name__ == "__main__":
    verify_contact_v221()
