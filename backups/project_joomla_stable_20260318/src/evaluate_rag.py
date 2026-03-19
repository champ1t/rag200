
import json
import time
import argparse
from pathlib import Path
import yaml
import statistics

from src.core.chat_engine import ChatEngine

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/config.yaml")
    ap.add_argument("--golden", default="data/golden_queries.json")
    ap.add_argument("--runs", type=int, default=1, help="Number of times to run each query for latency avg")
    args = ap.parse_args()

    cfg = load_config(args.config)
    
    # Disable logs during eval to avoid noise? Or keep them?
    # cfg["chat"]["save_log"] = False 
    
    print("[EVAL] Initializing Engine...")
    engine = ChatEngine(cfg)
    engine.warmup()

    golden_path = Path(args.golden)
    if not golden_path.exists():
        print(f"[ERROR] Golden queries not found: {golden_path}")
        return

    queries = json.loads(golden_path.read_text(encoding="utf-8"))
    print(f"[EVAL] Loaded {len(queries)} cases.")

    results = []
    latencies = {"total": [], "vector_search": [], "llm": [], "routing": []}

    for case in queries:
        q = case["question"]
        expected_type = case.get("expected_type")
        expected_contains = case.get("expected_contains")
        
        print(f"\n[CASE] {q}")
        
        # Multiple runs for latency stability
        run_lats = []
        last_resp = None
        
        for _ in range(args.runs):
            engine.last_context = None # Ensure isolation (unless multi-turn)
            
            # Handle list input for multi-turn
            if isinstance(q, list):
                # Process sequence, keep context
                msgs = q
                turn_resps = []
                for msg in msgs:
                    resp = engine.process(msg)
                    turn_resps.append(resp)
                
                # Use verify logic on the LAST response
                last_resp = turn_resps[-1]
                # Sum latencies? or just last?
                # Total latency of flow
                total_lat = sum([r.get("latencies", {}).get("total", 0) for r in turn_resps])
                last_resp["latencies"]["total"] = total_lat
                
                run_lats.append(last_resp.get("latencies", {}))
            else:
                resp = engine.process(q)
                run_lats.append(resp.get("latencies", {}))
                last_resp = resp
            
        # Avg latencies for this case
        avg_lat = {}
        for k in ["total", "vector_search", "llm", "routing"]:
            vals = [l.get(k, 0) for l in run_lats if l.get(k) is not None]
            if vals:
                avg_lat[k] = statistics.mean(vals)
                latencies[k].extend(vals) # Collect all for global stats

        # Verification Logic (Upgraded)
        passed = True
        failure_reason = ""
        actual_route = last_resp.get("route", "")
        answer_text = last_resp.get("answer", "")
        retrieved_ctx = last_resp.get("retrieved_context", []) # New field

        # Check Route/Type
        if expected_type == "person" or expected_type == "team":
             if "contact" not in actual_route:
                 passed = False
                 failure_reason = f"Route Mismatch (Got {actual_route})"
        elif expected_type == "knowledge" or expected_type == "procedure":
             if actual_route not in ["rag", "rag_clarify"]:
                 passed = False
                 failure_reason = f"Route Mismatch (Got {actual_route})"
        elif expected_type == "irrelevant":
             print(f"[DEBUG] Checking irrelevant: route={actual_route}")
             refusal_phrases = ["No information", "ไม่พบข้อมูลที่ยืนยันคำตอบนี้ในระบบ"]
             is_refusal = any(phrase in answer_text for phrase in refusal_phrases)
             
             # Pass if route is explicit rejection OR answer contains refusal
             if actual_route not in ["rag_low_score", "rag_no_docs", "ood", "rag_controller_rejected", "rag_evaluator_rejected"] and not is_refusal:
                 passed = False
                 failure_reason = f"Route Mismatch (Got {actual_route} and Answer was not refusal)"
        
        # Check Content (Granular)
        if passed and expected_contains:
            # 1. Answer Check
            in_answer = expected_contains.lower() in answer_text.lower()
            
            if not in_answer:
                passed = False
                
                # 2. Retrieval Check (Diagnosis)
                # Check if it was in the retrieved context?
                in_context = False
                for doc in retrieved_ctx:
                    if expected_contains.lower() in doc.get("text", "").lower():
                        in_context = True
                        break
                
                if in_context:
                    failure_reason = "Generation Fail (Found in Context, Missing in Answer)"
                else:
                    failure_reason = "Retrieval Fail (Missing in Context)"

        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] route={actual_route} | latency={avg_lat.get('total',0):.1f}ms")
        if not passed:
             print(f"      Reason: {failure_reason}")
        
        results.append({
            "question": q,
            "passed": passed,
            "failure_reason": failure_reason,
            "latency": avg_lat
        })

    # Summary
    print("\n" + "="*40)
    print("EVALUATION SUMMARY")
    print("="*40)
    pass_count = sum(1 for r in results if r["passed"])
    print(f"Passed: {pass_count}/{len(results)}")
    
    print("\nLatency (Avg):")
    for k, vals in latencies.items():
        if vals:
            print(f"  {k}: {statistics.mean(vals):.2f} ms")

if __name__ == "__main__":
    main()
