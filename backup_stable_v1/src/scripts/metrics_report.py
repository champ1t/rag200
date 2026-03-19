import json
from pathlib import Path
from collections import defaultdict
import datetime
import statistics

def load_logs(log_path: str = "data/logs/chat_telemetry.jsonl"):
    logs = []
    path = Path(log_path)
    if not path.exists():
        print(f"No log file found at {path}")
        return []
    
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return logs

def generate_report():
    logs = load_logs()
    if not logs:
        return

    total_queries = len(logs)
    routes = defaultdict(int)
    modes = defaultdict(int)
    latencies = []
    pack_hits = 0
    clarify_asked = 0

    for log in logs:
        routes[log.get("route", "unknown")] += 1
        modes[log.get("mode", "unknown")] += 1
        if log.get("pack_hit"):
            pack_hits += 1
        if log.get("clarify_asked"):
            clarify_asked += 1
        
        # Latency
        lats = log.get("latencies", {})
        if "total" in lats:
            latencies.append(lats["total"])

    print(f"--- RAG Telemetry Report ---")
    print(f"Generated: {datetime.datetime.now()}")
    print(f"Total Queries: {total_queries}")
    
    print(f"\n[Routes]")
    for r, count in routes.items():
        print(f"  - {r}: {count} ({count/total_queries*100:.1f}%)")
        
    print(f"\n[Modes]")
    for m, count in modes.items():
        print(f"  - {m}: {count}")
        
    print(f"\n[Knowledge Packs]")
    print(f"  - Hits: {pack_hits} ({pack_hits/total_queries*100:.1f}%)")
    print(f"  - Clarifications Asked: {clarify_asked}")
    
    print(f"\n[Latency (ms)]")
    if latencies:
        print(f"  - Avg: {statistics.mean(latencies):.2f}")
        print(f"  - Min: {min(latencies):.2f}")
        print(f"  - Max: {max(latencies):.2f}")
    else:
        print("  - N/A")

if __name__ == "__main__":
    generate_report()
