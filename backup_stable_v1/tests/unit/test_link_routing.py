import sys
from pathlib import Path
import yaml

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.chat_engine import ChatEngine

def test_link_routing():
    config_path = "configs/config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
        
    engine = ChatEngine(cfg)
    
    test_cases = [
        "เข้า Edocument",
        "ลิงก์ Edocument",
        "ขอลิงก์ SMC",
        "ระบบบันทึกงาน SMC", # Exact anchor text
        "เข้า กองทุนสำรองฯ", # Should show auth warning
        "เบอร์โทรศัพท์", # Should go to contact routing
        "วิธีการใช้งาน e-doc" # Should go to RAG
    ]
    
    print("\n" + "="*50)
    print("STARTING LINK ROUTING TEST")
    print("="*50)
    
    for q in test_cases:
        print(f"\n[QUERY] {q}")
        res = engine.process(q)
        print(f"[ROUTE] {res['route']}")
        if res['route'] == 'link_lookup':
            print("[ANSWER PREVIEW]")
            print(res['answer'])
            if "Requires login" in res['answer']:
                print(">> Correctly flagged as Auth Required")
        elif res['route'] == 'rag':
            print("[ANSWER PREVIEW (RAG)]")
            print(res['answer'][:100] + "...")
            
    print("\n" + "="*50)
    print("TEST COMPLETE")
    print("="*50)

if __name__ == "__main__":
    test_link_routing()
