from src.core.chat_engine import ChatEngine
import yaml
import time

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

print("Initializing Chat Engine...")
cfg = load_config("configs/config.yaml")
engine = ChatEngine(cfg)
engine.warmup()

test_cases = [
    # FIX-1: Role Definition
    "ONU คืออะไร และมีหน้าที่อะไรในระบบ FTTx",
    "OLT คืออะไร และทำหน้าที่อะไร",
    
    # FIX-2: Layer Explanation
    "Network Layer มีหน้าที่อะไรและไม่ได้ทำหน้าที่อะไร",
    "OSI Model คืออะไร",
    
    # FIX-3: Purity Guard
    "ทำไมต้องมีการ Monitor ระบบเครือข่าย",
    
    # FIX-4: LOS -> SLA Framing
    "LOS ส่งผลต่อ SLA อย่างไรในภาพรวม"
]

print("-" * 60)
for q in test_cases:
    print(f"Query: {q}")
    start = time.time()
    resp = engine.process(q)
    print(f"Latency: {(time.time() - start) * 1000:.2f}ms")
    print(f"Route: {resp.get('route', 'unknown')}")
    print(f"Answer:\n{resp['answer']}")
    print("-" * 60)
