
import time
import sys
import os

# Ensure src is in path
sys.path.append(os.getcwd())

import yaml
from src.core.chat_engine import ChatEngine

def test_cache_fix():
    print("[TEST] Initializing Engine...")
    with open("configs/config.yaml") as f:
        cfg = yaml.safe_load(f)
    engine = ChatEngine(cfg)

    print("\n[TEST] Run 1: 'RAG คืออะไร' (Expect General Fallback)")
    t1 = time.time()
    res1 = engine.process("RAG คืออะไร")
    lat1 = time.time() - t1
    print(f"Latency 1: {lat1:.4f}s")
    print(f"Route 1: {res1.get('route')}")
    print(f"Answer 1: {res1.get('answer')[:100]}...")
    
    # Store explicit result/score for debugging
    if res1.get('hits'):
        print(f"Score 1: {res1['hits'][0].get('score')}")

    print("\n[TEST] Run 2: 'RAG คืออะไร' (Expect Cache Hit + No Kill Switch)")
    t2 = time.time()
    res2 = engine.process("RAG คืออะไร")
    lat2 = time.time() - t2
    print(f"Latency 2: {lat2:.4f}s")
    print(f"Route 2: {res2.get('route')}")
    print(f"Answer 2: {res2.get('answer')[:100]}...")

    if res2.get('route') == 'rag_kill_switch':
        print("\n[FAIL] Kill Switch triggered on Run 2! Cache logic is broken.")
    elif lat2 < 1.0:
        print("\n[PASS] Cache Hit + Fast (<1s). Fix verified.")
    else:
        print(f"\n[WARN] Took {lat2}s. Maybe not fully cached?")

if __name__ == "__main__":
    test_cache_fix()
