
import json
import time
from src.core.chat_engine import ChatEngine

def run_test():
    print("🚀 Initializing Production RAG Engine...")
    engine = ChatEngine({
        "llm": {
            "model": "llama3.2:3b",
            "temperature": 0.0,
            "base_url": "http://localhost:11434"
        },
        "chat": {"log_level": "INFO"},
        "rag": {"enabled": True},
        "retrieval": {"top_k": 3}
    })

    test_cases = {
        "1. LOS / Optical Signal (Core Deterministic)": [
            "LOS เกิดจาก software bug ได้ไหม",
            "ถ้า firmware พัง จะขึ้น LOS ไหม",
            "LOS ต่างจาก Link Down ยังไง",
            "ไฟ LOS กระพริบ แต่ internet ยังใช้ได้ เป็นไปได้ไหม",
            "LOS เกิดจากอุณหภูมิสูงได้ไหม",
            "ทำไม LOS ถึงเป็นสีแดง ไม่ใช่สีอื่น"
        ],
        "2. Fiber Language Trap (Semantic Drift)": [
            "เบอร์ไฟเบอร์หาย คืออะไร",
            "ไฟเบอร์ขาดเบอร์เดียว อินเทอร์เน็ตทั้งบ้านดับไหม",
            "ไฟเบอร์มีเบอร์เหมือนเบอร์โทรไหม",
            "เปลี่ยนเบอร์ไฟเบอร์ ต้องเดินสายใหม่ไหม"
        ],
        "3. Mixed Language / Intent Confusion": [
            "LOS red light means what",
            "Why does LOS occur in fiber network",
            "fiber no signal but power ok",
            "ONU LOS คืออะไร"
        ],
        "4. Conceptual vs Procedural Boundary": [
            "ถ้า LOS ขึ้นควรทำยังไง",
            "แก้ LOS ยังไงให้หายเร็ว",
            "LOS แก้ได้ไหม",
            "LOS ถือว่าเป็นความเสียหายระดับไหน"
        ],
        "5. ONU / OLT / Architecture Understanding": [
            "ONU ต่างจาก OLT ยังไง",
            "LOS เกิดฝั่ง ONU หรือ OLT",
            "ถ้า OLT ปิด จะขึ้น LOS ไหม",
            "ONU มีหน้าที่เกี่ยวกับสัญญาณแสงอะไร"
        ],
        "6. Weird / Edge / Reviewer Trap": [
            "LOS ถือเป็น error หรือ status",
            "LOS เป็น logical หรือ physical problem",
            "ถ้าเห็น LOS แต่ค่า optical power ปกติ แปลว่าอะไร",
            "LOS ต่างจาก attenuation ยังไง",
            "LOS เกิดเฉพาะไฟเบอร์หรือไม่"
        ]
    }

    results = {}

    for category, queries in test_cases.items():
        print(f"\n--- Category: {category} ---")
        results[category] = []
        for q in queries:
            print(f"Testing: {q}")
            try:
                res = engine.process(q)
                answer = res.get('answer', 'NO ANSWER')
                route = res.get('route', 'UNKNOWN')
                results[category].append({
                    "query": q,
                    "answer": answer,
                    "route": route
                })
                print(f"Result: {answer[:100]}...")
            except Exception as e:
                print(f"Error testing {q}: {e}")
                results[category].append({
                    "query": q,
                    "answer": f"ERROR: {str(e)}",
                    "route": "error"
                })

    # Save to file
    with open("compliance_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Print formatted output for the user
    print("\n\n" + "="*50)
    print("FINAL COMPLIANCE TEST RESULTS")
    print("="*50)
    
    for category, items in results.items():
        print(f"\n## {category}")
        for item in items:
            print(f"\nQ: {item['query']}")
            print(f"A: {item['answer']}")
            print("-" * 20)

if __name__ == "__main__":
    run_test()
