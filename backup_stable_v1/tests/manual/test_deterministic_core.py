
from src.ai.safe_normalizer import SafeNormalizer
from src.rag.handlers.directory_handler import DirectoryHandler
import json

def test_deterministic_core():
    llm_cfg = {"model": "llama3.2:3b", "base_url": "http://localhost:11434"}
    sn = SafeNormalizer(llm_cfg)
    
    # Mock some data for DirectoryHandler if needed, or but we can just test SN first
    test_queries = [
        "ขอตารางเบอร์ OMC",
        "ขอดูรูปแผนผัง helpdesk",
        "ตารางเบอร์ RNOC",
        "สมาชิก fttx",
        "ใครคือ ผจ.สบลตน.",
        "เบอร์ omc"
    ]
    
    print("=== TESTING SAFE NORMALIZER (ASSET DETECTION) ===")
    for q in test_queries:
        print(f"Query: {q}")
        res = sn.analyze(q)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        print("-" * 30)

if __name__ == "__main__":
    test_deterministic_core()
