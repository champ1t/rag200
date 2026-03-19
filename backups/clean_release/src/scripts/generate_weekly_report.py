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
    
    cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
    
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                # Parse timestamp
                ts_val = data.get("timestamp")
                if ts_val:
                    if isinstance(ts_val, (int, float)):
                        ts = datetime.datetime.fromtimestamp(ts_val)
                    else:
                        ts = datetime.datetime.fromisoformat(ts_val)
                        
                    if ts >= cutoff:
                        logs.append(data)
            except (json.JSONDecodeError, ValueError):
                continue
    return logs

def generate_weekly_report():
    logs = load_logs()
    if not logs:
        print("No logs found for the last 7 days.")
        return

    total_queries = len(logs)
    routes = defaultdict(int)
    
    # KPIs
    contact_total = 0
    contact_hits = 0
    contact_misses = 0
    contact_ambiguous = 0
    
    news_total = 0
    news_hits = 0 # article_answer
    news_misses = 0
    
    team_total = 0
    team_hits = 0
    team_misses = 0
    team_ambiguous = 0
    
    latencies = []
    miss_queries = []

    for log in logs:
        r = log.get("route", "unknown")
        routes[r] += 1
        
        if "miss" in r:
            q = log.get("query", "").strip()
            if q: miss_queries.append(q)
        
        # Categorize
        if "contact_" in r or r == "contact_lookup":
            contact_total += 1
            if "hit" in r: contact_hits += 1
            elif "miss" in r: contact_misses += 1
            elif "ambiguous" in r: contact_ambiguous += 1
            
        if r in ["news_search", "article_answer", "news_miss"]:
            news_total += 1
            if r == "article_answer": news_hits += 1
            elif r == "news_miss": news_misses += 1
        if r in ["news_search", "article_answer", "news_miss", "news_miss_filtered"]:
            news_total += 1
            if r == "article_answer": news_hits += 1
            elif r.startswith("news_miss"): news_misses += 1
            # news_search might be intermediate
            
        if "team_" in r:
            team_total += 1
            if "hit" in r: team_hits += 1
            elif "miss" in r: team_misses += 1
            elif "ambiguous" in r: team_ambiguous += 1
        
        # Latency
        lats = log.get("latencies", {})
        if "total" in lats:
            latencies.append(lats["total"])

    print(f"--- Weekly Coverage Report (Last 7 Days) ---")
    print(f"Generated: {datetime.datetime.now()}")
    print(f"Total Queries: {total_queries}")
    
    print(f"\n[Contact Center]")
    if contact_total > 0:
        print(f"  Total: {contact_total}")
        print(f"  Resolution Rate: {contact_hits/contact_total*100:.1f}% ({contact_hits} hits)")
        print(f"  Miss Rate: {contact_misses/contact_total*100:.1f}% ({contact_misses} misses)")
        print(f"  Ambiguity Rate: {contact_ambiguous/contact_total*100:.1f}% ({contact_ambiguous} ambiguous)")
    else:
        print("  No contact queries.")

    print(f"\n[Knowledge/News]")
    if news_total > 0:
        print(f"  Total: {news_total}")
        print(f"  Found Rate: {news_hits/news_total*100:.1f}% ({news_hits} found)")
        print(f"  Miss Rate: {(news_total - news_hits)/news_total*100:.1f}%")
    print(f"\n[Knowledge/News]")
    if news_total > 0:
        print(f"  Total: {news_total}")
        print(f"  Found Rate: {news_hits/news_total*100:.1f}% ({news_hits} found)")
        print(f"  Miss Rate: {(news_total - news_hits)/news_total*100:.1f}%")
    else:
        print("  No news queries.")
        
    print(f"\n[Team Directory]")
    if team_total > 0:
        print(f"  Total: {team_total}")
        print(f"  Resolution Rate: {team_hits/team_total*100:.1f}% ({team_hits} hits)")
        print(f"  Miss Rate: {team_misses/team_total*100:.1f}% ({team_misses} misses)")
        print(f"  Ambiguity Rate: {team_ambiguous/team_total*100:.1f}% ({team_ambiguous} ambiguous)")
    else:
        print("  No team queries.")
        
    print(f"\n[Top Routes]")
    top_routes = sorted(routes.items(), key=lambda x: x[1], reverse=True)[:5]
    for r, c in top_routes:
        print(f"  - {r}: {c}")
        
    print(f"\n[Performance]")
    if latencies:
        avg = statistics.mean(latencies)
        lats_sorted = sorted(latencies)
        p95 = lats_sorted[int(len(lats_sorted) * 0.95)]
        print(f"  Avg Latency: {avg:.2f}ms")
        print(f"  P95 Latency: {p95:.2f}ms")
    else:
        print("  N/A")

    if miss_queries:
        from collections import Counter
        print(f"\n[Top Content Gaps (Misses)]")
        for q, count in Counter(miss_queries).most_common(5):
             print(f"  - '{q}': {count}")

if __name__ == "__main__":
    generate_weekly_report()
