import sys
from pathlib import Path
import yaml

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.core.chat_engine import ChatEngine

def test_position_lookup():
    config_path = "configs/config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
        
    engine = ChatEngine(cfg)
    
    test_cases = [
        "ใครดำรงตำแหน่ง ผส.บลตน.",
        "ใครคือ ผจ.สบลตน.",
        "Supervisor Agent มีใครบ้าง",
        "ชื่อตำแหน่ง Supervisor Agent", # Should match logic
        "ผส.บลตน.", # Should match if name not too generic?
        "ใครเป็น CEO" # Should fail (not in our manual extraction)
    ]
    
    print("\n" + "="*50)
    print("STARTING POSITION LOOKUP TEST")
    print("="*50)
    
    for q in test_cases:
        print(f"\n[QUERY] {q}")
        res = engine.process(q)
        print(f"[ROUTE] {res['route']}")
        if res['route'] == 'position_lookup':
            print("[ANSWER PREVIEW]")
            print(res['answer'])
        elif res['route'] == 'link_lookup':
            print(f"[LINK] {res['answer'][:50]}...")
            
    print("\n" + "="*50)
    print("TEST COMPLETE")
    print("="*50)

if __name__ == "__main__":
    test_position_lookup()
