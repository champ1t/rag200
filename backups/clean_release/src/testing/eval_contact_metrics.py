
import json
import time
import sys
import statistics
import datetime
from pathlib import Path
from unittest.mock import MagicMock

# Mock dependencies
sys.modules['requests'] = MagicMock()
sys.modules['bs4'] = MagicMock()
sys.modules['lxml'] = MagicMock()
sys.modules['lxml.html'] = MagicMock()

from src.rag.handlers.contact_handler import ContactHandler
from src.utils.normalization import normalize_for_contact

# ----------------------------------------------------------------------
# Mock Records (Need sufficient coverage for Golden Dataset)
# ----------------------------------------------------------------------
RECORDS = [
    {"id": "1", "name": "IP-Phone SBC", "name_norm": "ip-phone sbc", "phones": ["1001"], "type": "team"},
    {"id": "2", "name": "SBC Core", "name_norm": "sbc core", "phones": ["1002"], "type": "team"},
    {"id": "3", "name": "BRAS TOT", "name_norm": "bras tot", "phones": ["1003"], "type": "team"},
    {"id": "4", "name": "ศูนย์ OMC หาดใหญ่", "name_norm": "ศูนย์ omc หาดใหญ่", "phones": ["1004"], "type": "team"},
    {"id": "5", "name": "IP Network", "name_norm": "ip network", "phones": ["1005"], "type": "team"},
    {"id": "6", "name": "NOC", "name_norm": "noc", "phones": ["1006"], "type": "team"}, # Canonical NOC
    {"id": "7", "name": "ผู้ดูแลระบบ", "name_norm": "ผู้ดูแลระบบ", "phones": ["1007"], "type": "team"}, # Admin
    {"id": "8", "name": "ผจ.สบลตน.", "name_norm": "ผจ.สบลตน.", "phones": ["1008"], "type": "team"}, # Manager
    {"id": "9", "name": "HelpDesk", "name_norm": "helpdesk", "phones": ["1009"], "type": "team"},
    {"id": "10", "name": "TACACS", "name_norm": "tacacs", "phones": ["1010"], "type": "team"},
    {"id": "11", "name": "ศูนย์ OMC สงขลา", "name_norm": "ศูนย์ omc สงขลา", "phones": ["1011"], "type": "team"},
    {"id": "12", "name": "Call Center", "name_norm": "call center", "phones": ["1177"], "type": "team"},
]

def run_eval(data_path: str, output_dir: str):
    p = Path(data_path)
    if not p.exists():
        print(f"[ERR] File not found: {data_path}")
        return

    queries = json.loads(p.read_text(encoding='utf-8'))
    
    # Run ID
    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = Path(output_dir) / f"contact_phase140_run_{run_id}.jsonl"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"--- Running Eval Phase 140 (N={len(queries)}) ---")
    
    results = []
    latencies = []
    metrics = {"HIT": 0, "CHOICE": 0, "REJECT": 0, "FP": 0}
    
    with open(out_file, "w", encoding="utf-8") as f:
        for item in queries:
            qid = item["id"]
            q = item["query"]
            gold = item["expected"]
            
            # Exec
            start = time.time()
            res = ContactHandler.handle(q, RECORDS)
            dur = (time.time() - start) * 1000
            
            # Analyze
            hits = res.get("hits", [])
            route = res.get("route", "")
            
            top_match_name = hits[0]["name"] if hits else None
            top_score = hits[0].get("_score", 0) if hits else 0
            
            # Determine System Decision
            decision = "REJECT"
            if top_score >= 80: decision = "HIT"
            elif 40 <= top_score < 80 or (hits and len(hits)>1): decision = "CHOICE" # Simplification
            elif not hits or "miss" in route: decision = "REJECT"
            
            # Map AMBIGUOUS gold to CHOICE
            gold_type = "CHOICE" if gold == "AMBIGUOUS" else ("REJECT" if gold == "REJECT" else "HIT")
            
            # Evaluation
            is_correct = False
            if gold == "AMBIGUOUS":
                is_correct = (decision == "CHOICE")
            elif gold == "REJECT":
                is_correct = (decision == "REJECT")
            else:
                # HIT expectation: Must be HIT AND correct name
                is_correct = (decision == "HIT" and top_match_name == gold)
            
            # False Positive Check
            # If Gold=REJECT but Decision=HIT -> FP
            # If Gold=ExpectedName but Decision=HIT(WrongName) -> FP
            is_fp = False
            if gold == "REJECT" and decision == "HIT": is_fp = True
            if gold not in ["AMBIGUOUS", "REJECT"] and decision == "HIT" and top_match_name != gold: is_fp = True
            
            if is_fp: metrics["FP"] += 1
            if decision == "HIT": metrics["HIT"] += 1
            elif decision == "CHOICE": metrics["CHOICE"] += 1
            elif decision == "REJECT": metrics["REJECT"] += 1
            
            latencies.append(dur)
            
            q_norm = normalize_for_contact(q)
            
            record = {
                "id": qid,
                "query": q,
                "normalized": q_norm,
                "gold": gold,
                "decision": decision,
                "outcome_correct": is_correct,
                "is_false_positive": is_fp,
                "top_match": top_match_name,
                "score": top_score,
                "latency_ms": dur
            }
            results.append(record)
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
            status_icon = "✅" if is_correct else "❌"
            if is_fp: status_icon = "⚠️ FP"
            print(f"{status_icon} [{dur:.1f}ms] {q} -> {decision} (Gold: {gold})")
            
    # Summary
    total = len(queries)
    p95 = statistics.quantiles(latencies, n=20)[-1] if len(latencies) >= 20 else max(latencies)
    
    print("\n--- Summary ---")
    print(f"Total: {total}")
    print(f"Hit Rate:    {metrics['HIT']/total:.1%}")
    print(f"Choice Rate: {metrics['CHOICE']/total:.1%}")
    print(f"Reject Rate: {metrics['REJECT']/total:.1%}")
    print(f"False Pos:   {metrics['FP']}")
    print(f"Output saved to {out_file}")
    
    # Export CSVs
    import csv
    
    # Summary CSV
    sum_file = Path(output_dir) / "contact_phase140_summary.csv"
    with open(sum_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Queries", total])
        writer.writerow(["Hit Rate", f"{metrics['HIT']/total:.1%}"])
        writer.writerow(["Choice Rate", f"{metrics['CHOICE']/total:.1%}"])
        writer.writerow(["Reject Rate", f"{metrics['REJECT']/total:.1%}"])
        writer.writerow(["False Positives", metrics["FP"]])
        writer.writerow(["P95 Latency (ms)", f"{p95:.2f}"])
        
    print(f"Summary CSV saved to {sum_file}")
    
    # Failures CSV
    fail_file = Path(output_dir) / "contact_phase140_failures.csv"
    with open(fail_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Query", "Expected", "Actual", "Score"])
        for r in results:
            if not r["outcome_correct"]:
                 writer.writerow([r["id"], r["query"], r["gold"], r["decision"], r["score"]])
                 
    print(f"Failures CSV saved to {fail_file}")

if __name__ == "__main__":
    import argparse
    run_eval("data/eval/contact_queries_phase140.json", "results")
