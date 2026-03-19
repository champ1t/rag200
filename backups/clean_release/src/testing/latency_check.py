
import sys
import os
import time
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine
from src.main import load_config

def test_latency():
    print("=== Latency Check (Router Optimization) ===")
    config_path = os.path.join(os.getcwd(), "configs/config.yaml")
    cfg = load_config(config_path)
    
    # Init (includes resource load)
    t_init = time.time()
    chat = ChatEngine(cfg)
    print(f"Init Time: {time.time() - t_init:.2f}s")
    
    queries = [
        ("Type A (Intent)", "ติดต่อ helpdesk"),
        ("Type B (Tutorial)", "what is mpls")
    ]
    
    for label, query in queries:
        print(f"\n--- Testing {label} ---")
        print(f"Query: {query}")
        
        t0 = time.time()
        try:
            res = chat.process(query)
            latency = time.time() - t0
            print(f"Total Latency: {latency:.2f}s")
            print(f"Answer Sample: {res.get('answer', '')[:100]}...")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

    print("\n=== Check Complete ===")
    
    # Check breakdown if available
    if "latencies" in res:
        print("Breakdown:", res["latencies"])

if __name__ == "__main__":
    test_latency()
