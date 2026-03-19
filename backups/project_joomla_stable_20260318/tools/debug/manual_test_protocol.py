import sys
import os
import yaml
import time
from src.core.chat_engine import ChatEngine

# Load config
def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

print("[TEST] Initializing Chat Engine...")
cfg = load_config("configs/config.yaml")

# Disable saving logs to avoid polluting production logs
# (Assuming ChatEngine has a flag or we just ignore it as it writes to run_id)
# Just let it run naturally.

engine = ChatEngine(cfg)
engine.warmup()

queries = [
    "ONU คืออะไร และมีหน้าที่อะไร",
    "Network Layer คืออะไรในเชิงแนวคิด",
    "Alarm ในระบบเครือข่ายคืออะไร",
    "ทำไมสัญญาณขาดช่วงจึงกระทบคุณภาพบริการ",
    "OSI Model มีไว้เพื่ออะไร",
    "เหตุใด Monitoring จึงช่วยลด downtime",
    "LOS ส่งผลต่อ SLA อย่างไรในภาพรวม"
]

print("-" * 60)
for i, q in enumerate(queries, 1):
    print(f"[{i}] Query: {q}")
    start = time.time()
    resp = engine.process(q)
    lat = (time.time() - start) * 1000
    
    route = resp.get("route", "unknown")
    answer = resp['answer'].replace("\n", " ").strip()
    
    print(f"    Route:   {route}")
    print(f"    Latency: {lat:.2f}ms")
    print(f"    Answer:  {answer[:300]}...")
    print("-" * 60)
