
import sys
import os
import yaml

# Add project root to path (parent of src)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.chat_engine import ChatEngine

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def repro():
    config_path = os.path.join(project_root, "configs/config.yaml") # Adjust path if needed
    if not os.path.exists(config_path):
        config_path = "config.yaml" # Try local if running from root

    try:
        cfg = load_config(config_path)
    except Exception as e:
        print(f"Config load failed: {e}. Using dummy.")
        cfg = {
            "retrieval": {"top_k": 5},
            "llm": {"model": "typhoon-v1.5-instruct"},
            "chat": {},
            "rag": {"use_cache": False}
        }
        
    print("[INFO] Initializing ChatEngine...")
    chat = ChatEngine(cfg)
    
    q = "BRAS"
    print(f"[TEST] Testing query: {q}")
    
    try:
        res = chat.process(q)
        print("Result:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    repro()
