from src.core.chat_engine import ChatEngine
import yaml
import time

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

print("Initializing Chat Engine for Semantic Guard Verification...")
cfg = load_config("configs/config.yaml")
engine = ChatEngine(cfg)
engine.warmup()

test_cases = [
    # 1. Definition vs Procedure (Role Guard)
    "ONT ทำหน้าที่อะไร",
    "OLT มีบทบาทอย่างไร",
    
    # 2. Cause-Effect vs How-to (Impact Guard)
    "สัญญาณไม่เสถียรส่งผลกับ latency อย่างไร",
    "Packet loss ทำให้เกิดอะไร",
    
    # 3. Factual Discipline (Expert Override)
    "ONU กับ ONT ต่างกันอย่างไร", # Check for "Location" hallucination
    
    # 4. Mixed Intent Rule
    "LOS คืออะไร และควรแก้อย่างไร" # Expect: Def Answer + How-to Refusal
]

print("-" * 60)
for q in test_cases:
    print(f"Query: {q}")
    start = time.time()
    resp = engine.process(q)
    print(f"Latency: {(time.time() - start) * 1000:.2f}ms")
    print(f"Route: {resp.get('route', 'unknown')}")
    print(f"Intent (Override Check): {resp.get('intent', 'unknown')}")
    print(f"Answer:\n{resp['answer']}")
    print("-" * 60)
