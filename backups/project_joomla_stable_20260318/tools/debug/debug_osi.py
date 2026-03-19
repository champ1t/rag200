from src.core.chat_engine import ChatEngine
import yaml

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

cfg = load_config("configs/config.yaml")
engine = ChatEngine(cfg)
engine.warmup()

q = "OSI Model มีไว้เพื่ออะไร"
print(f"Testing: {q}")
resp = engine.process(q)
print(f"Route: {resp.get('route')}")
