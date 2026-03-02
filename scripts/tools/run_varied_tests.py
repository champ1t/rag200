
import yaml
import sys
import os

# Ensure src is in path
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_tests():
    config_path = "configs/config.yaml"
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        return

    print("Initializing ChatEngine...")
    cfg = load_config(config_path)
    engine = ChatEngine(cfg)
    engine.warmup()
    
    test_queries = [
        "confgi vlan cisco ให้หน่อย",      # Typo + HowTo
        "snc เบอร์อะไร",                   # Typo + Contact
        "เน็ตหลุดทำไงดีคับ",                # Spoken + HowTo/General
        "ขอเบอร์พี่สมชาย แผนก a&i คับ",     # Spoken + Contact (Complex)
        "wdm คือรัย",                      # Slang + Knowledge
        "อยากรู้ข่าวน้ำท่วมเชียงรายล่าสุด",   # Web Knowledge
        "login huawei มะได้",              # Spoken + HowTo
        "ติดต่อ HR เรื่องลาป่วย",           # General Contact
        "vpn เข้าไม่ได้ error 691",        # Specific Error
        "ใครดูแลระบบ nms"                  # Directory/Role query
    ]
    
    results = []
    
    print(f"\n{'='*20} Running 10 Varied Queries {'='*20}\n")
    
    for i, q in enumerate(test_queries, 1):
        print(f"[{i}/10] Asking: {q}")
        try:
            resp = engine.process(q)
            route = resp.get("route", "unknown")
            answer = resp.get("answer", "")
            
            # Summarize answer
            summary = answer.replace('\n', ' ').strip()
            if len(summary) > 80:
                summary = summary[:77] + "..."
            
            results.append({
                "id": i,
                "query": q,
                "route": route,
                "answer_summary": summary
            })
            print(f"   -> Route: {route}")
        except Exception as e:
            print(f"   -> ERROR: {e}\n")
            results.append({"id": i, "query": q, "route": "ERROR", "answer_summary": str(e)})

    # Print Final Summary Table
    print(f"\n{'='*20} Test Results Summary {'='*20}")
    print(f"{'ID':<4} | {'Query':<30} | {'Intent':<20} | {'Answer Snippet'}")
    print("-" * 90)
    for r in results:
        q_disp = (r['query'][:27] + '..') if len(r['query']) > 27 else r['query']
        print(f"{r['id']:<4} | {q_disp:<30} | {r['route']:<20} | {r['answer_summary']}")

if __name__ == "__main__":
    run_tests()
