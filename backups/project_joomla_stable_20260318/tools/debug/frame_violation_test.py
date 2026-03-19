
import json
import time
from src.core.chat_engine import ChatEngine

def run_frame_validation():
    print("🚀 Initializing Production Frame Validation Suite (Strict Mode)...")
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
        "CAT_1_CONSISTENCY": [
            "LOS เกิดจากอะไร",
            "สาเหตุของ LOS คืออะไร",
            "LOS หมายถึงอะไร",
            "ไฟ LOS บอกอะไร"
        ],
        "CAT_2_NEGATIVE_FRAMING": [
            "LOS ไม่ได้เกิดจากอะไร",
            "อะไรที่ไม่ใช่สาเหตุของ LOS",
            "software เกี่ยวกับ LOS ตรงไหนบ้าง"
        ],
        "CAT_3_FALSE_CAUSALITY": [
            "ทำไม reboot แล้ว LOS หาย",
            "ทำไมอัปเดตแล้ว LOS ขึ้น",
            "system ล่มพร้อม LOS แปลว่าอะไร"
        ],
        "CAT_4_BOUNDARY": [
            "หลักการตรวจสอบ LOS คืออะไร",
            "แนวคิดการจัดการ LOS",
            "มุมมองเชิงระบบเมื่อ LOS เกิด"
        ],
        "CAT_5_CONTAMINATION": [
            "LOS ต่างจาก Internet Down ยังไง",
            "LOS ต่างจาก Authentication Fail ยังไง",
            "LOS เกี่ยวกับ bandwidth หรือไม่"
        ]
    }

    print("\n--- Frame Violation Detection Report ---")
    
    for category, queries in test_cases.items():
        print(f"\n[{category}]")
        for q in queries:
            print(f"\n❓ Q: {q}")
            try:
                res = engine.process(q)
                ans = res.get('answer', '').strip()
                route = res.get('route')
                
                print(f"✅ A: {ans}")
                print(f"🛤 Route: {route}")
                
                # Basic automated checks (Manual review still required for tone)
                if "LOS" in q and "LOS" not in ans and "Loss of Signal" not in ans:
                    print("❌ FAILURE: LOS definition missing")
                
                if category == "CAT_3_FALSE_CAUSALITY":
                     if "ซอฟต์แวร์" in ans and "สาเหตุ" in ans and "ไม่" not in ans:
                         print("❌ FAILURE: Potential Causality Leak")
            
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_frame_validation()
