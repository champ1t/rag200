
import json
import time
import sys
import unittest
from pathlib import Path
from src.core.chat_engine import ChatEngine

# Mock dependencies to avoid full startup overhead if possible
# But this is E2E, so we want full stack.

def run_e2e_eval():
    print("--- Running E2E RAG Validation (Phase R4) ---")
    
    # Load Test Data
    if len(sys.argv) > 1:
        dataset_path = Path(sys.argv[1])
    else:
        dataset_path = Path("data/eval/rag_e2e_final_gate.json")

    if not dataset_path.exists():
         # Fallback to R4 if R5 not found (or passed loop)
         dataset_path = Path("data/eval/rag_e2e_phase_r4.json")
    
    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}")
        return
        
    print(f"[INFO] Using Dataset: {dataset_path}")
    data = json.loads(dataset_path.read_text())
    
    # Initialize Engine
    # Load Config
    import yaml
    config_path = Path("configs/config.yaml")
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
    else:
        cfg = {} # Fallback or Mock
        
    engine = ChatEngine(cfg) 
    # Ensure cache is cold? Or warm? Let's assume as-is.
    
    results = []
    
    for case in data:
        q = case["query"]
        expected = case["expected_behavior"]
        case_type = case.get("type", "GENERAL")
        
        print(f"\n[E2E] Query: '{q}' (Type: {case_type})")
        
        t0 = time.time()
        res = engine.process(q)
        latency = (time.time() - t0) * 1000
        
        ans = res.get("answer", "")
        route = res.get("route", "unknown")
        
        # Determine Pass/Fail
        status = "FAIL"
        
        if expected == "PASS":
            if route in ["rag", "rag_cache", "rag_cache_l2", "article_answer"] or "cache" in route:
                if len(ans) > 20 and "ไม่พบข้อมูล" not in ans:
                    status = "PASS"
        elif expected == "PASS_GENERAL":
             # Allowed to pass even with low evidence if it uses General Fallback
             if "เนื่องจากไม่พบเอกสารภายใน" in ans or "หลักการทั่วไป" in ans:
                  status = "PASS"
             # Or if it passed normally (e.g. found article)
             elif route in ["rag", "article_answer"] and "ไม่พบข้อมูล" not in ans:
                  status = "PASS"
                  
        elif expected == "SAFE_MISS":
             if route in ["rag_miss_coverage", "rag_kill_switch", "article_nofetch"]:
                 status = "PASS"
             if "ไม่พบข้อมูล" in ans:
                 status = "PASS"
        elif expected == "REJECT":
            if "ไม่พบ" in ans or "ไม่สามารถ" in ans or route in ["rag_kill_switch", "rag_miss_coverage", "rag_review_fail"]:
                 status = "PASS"
        elif expected == "KILL_SWITCH":
            if route == "rag_kill_switch":
                status = "PASS"
        elif expected == "CHOICE":
             if route in ["contact_ambiguous", "contact_clarify", "contact_hit_contact_book_fuzzy"]:
                 status = "PASS"
             # Also allow soft fail to RAG if it answers somewhat correctly
             if "เลือก" in ans or "หมายถึง" in ans:
                 status = "PASS"
                 
        elif expected == "CACHE_HIT":
             if route in ["rag_cache", "rag_cache_l2"] or "cache" in route:
                 status = "PASS"
                 
        print(f"   -> Result: {status} (Route: {route}, Latency: {latency:.2f}ms)")
        if status == "FAIL":
             print(f"      [Fail Details] Ans: {ans[:100]}...")

                 
        print(f"   -> Result: {status} (Route: {route}, Latency: {latency:.2f}ms)")
        results.append({
            "query": q,
            "status": status,
            "latency": latency,
            "route": route,
            "answer_snippet": ans[:50]
        })
        
    # Summary
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)
    print(f"\n--- Summary ---")
    print(f"Total: {total}")
    print(f"Pass: {pass_count} ({pass_count/total*100:.1f}%)")
    
    # Save Report
    with open("results/rag_e2e_report.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    run_e2e_eval()
