
import sys
import yaml
import time
from pathlib import Path

# Add src to path
sys.path.append(str(Path.cwd()))

from src.chat_engine import ChatEngine

def run_random_tests():
    # Load Config
    config_path = Path("configs/config.yaml")
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
    else:
        cfg = {}

    # Initialize Engine
    print("[INFO] Initializing ChatEngine...")
    engine = ChatEngine(cfg)

    # 10 Weird/Diverse Queries
    queries = [
        "สูตรไข่เจียว",             # 1. Out of Domain
        "...",                      # 2. Punctuation only
        "ont password",             # 3. Security (Should Redirect)
        "ใครหล่อสุดใน nt",        # 4. Subjective/Person
        "server farm อยู่ที่ไหน",    # 5. Facility Location
        "internet ใช้ไม่ได้ helps",  # 6. Mixed Lang + Typo
        "0812345678",               # 7. Reverse Lookup attempt
        "admin admin",              # 8. Credential Pattern
        "test",                     # 9. Short keyword
        "ช่วยด้วยครับ"              # 10. Urgent/No Context
    ]

    print("\n" + "="*50)
    print("MATCH 10 RANDOM SCENARIOS")
    print("="*50 + "\n")

    results = []

    for i, q in enumerate(queries, 1):
        print(f"[{i}] Query: '{q}'")
        engine.reset_context() # Fix: Ensure independent testing
        t_start = time.time()
        
        try:
            res = engine.process(q)
            latency = (time.time() - t_start) * 1000
            
            ans = res.get("answer", "")[:100].replace("\n", " ") + "..." # Truncate for display
            route = res.get("route", "N/A")
            
            print(f"    -> Route: {route}")
            print(f"    -> Answer: {ans}")
            print(f"    -> Time: {latency:.2f}ms")
            
            results.append({
                "id": i,
                "query": q,
                "route": route,
                "answer": ans,
                "latency": f"{latency:.0f}ms"
            })
            
        except Exception as e:
            print(f"    -> ERROR: {e}")
            results.append({
                "id": i,
                "query": q,
                "route": "ERROR",
                "answer": str(e),
                "latency": "N/A"
            })
        
        print("-" * 30)

    # Print Summary Table
    print("\n" + "="*60)
    print(f"{'ID':<3} | {'Query':<25} | {'Route':<20} | {'Latency':<8}")
    print("-" * 60)
    for r in results:
        print(f"{r['id']:<3} | {r['query']:<25} | {r['route']:<20} | {r['latency']:<8}")
    print("="*60)

if __name__ == "__main__":
    run_random_tests()
