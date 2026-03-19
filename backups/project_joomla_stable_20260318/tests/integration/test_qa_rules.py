from src.core.chat_engine import ChatEngine
import yaml
import time

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

print("Initializing Chat Engine for QA Verification...")
cfg = load_config("configs/config.yaml")
engine = ChatEngine(cfg)
engine.warmup()

test_cases = [
    # 1. Reasoning/Hypothetical (Should NOT Refuse)
    "Reboot แล้วหาย เป็นเพราะอะไรได้บ้าง",
    "เป็นไปได้ไหมที่สายขาดแล้ว LOS ไม่แดง",
    
    # 2. Technical Accuracy & Comparison
    "ใยแก้วนำแสงต่างจากสายทองแดงอย่างไร",
    
    # 3. How-to Boundary (Should Refuse How-to, but maybe define conceptual)
    "ขอขั้นตอนแก้ LOS",
    
    # 4. Technical Fact Check
    "ONU คือหน่วยงานอะไร"  # Should correct to "Device"
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
