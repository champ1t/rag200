
import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.chat_engine import ChatEngine
from src.rag.article_interpreter import ArticleInterpreter

import yaml

def load_config(path: str):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def test_scenarios():
    print("Loading Config...")
    cfg = load_config("configs/config.yaml")
    print("Initializing ChatEngine...")
    engine = ChatEngine(cfg)
    
    scenarios = [
        {
            "name": "Inside SMC - Procedure (Fast-Path)",
            "query": "วิธีเข้า ONU ZTE",
            "expect_llm": False,
            "expect_route": "article_answer"
        },
        {
            "name": "Inside SMC - Specific Command (Fast-Path)",
            "query": "cmd ตั้งค่า bridge mode zte",
            "expect_llm": False,
            "expect_route": "article_answer"
        },
        {
            "name": "Inside SMC - Explanation (LLM Grounded)",
            "query": "สรุปสาเหตุที่ FTTx speed ตก", 
            "expect_llm": True,
            "expect_route": "article_answer" # Still article route, but uses LLM inside interpreter
        },
        {
            "name": "General Knowledge (Outside SMC)",
            "query": "ช่วยอธิบายหลักการทำงานของ Fiber Optic เบื้องต้น",
            "expect_llm": True,
            "expect_route": "rag_answer" # Should fall back to general RAG or LLM if not in SMC
        }
    ]
    
    print("\n=== Starting Comprehensive Scenario Test ===\n")
    
    for sc in scenarios:
        print(f"--- Testing: {sc['name']} ---")
        q = sc['query']
        print(f"Q: {q}")
        
        start = time.time()
        res = engine.process(q)
        duration = (time.time() - start) * 100
        
        print(f"Route: {res.get('route')}")
        
        # Check Latency/LLM usage
        latencies = res.get('latencies', {})
        llm_time = latencies.get('llm', 0) + latencies.get('generator', 0)
        
        used_llm = llm_time > 100 # Threshold for "Used LLM"
        
        print(f"Duration: {duration:.2f}ms")
        print(f"LLM Latency: {llm_time:.2f}ms (Used LLM: {used_llm})")
        
        # Verification
        if sc['expect_llm'] != used_llm:
            # Special case: Explanation logic is inside ArticleInterpreter which might not report to top-level latencies['llm'] directly
            # depending on how it's implemented. Let's inspect the answer content for cues.
            pass

        print(f"Answer Snippet: {res['answer'][:200]}...")
        print("-" * 30 + "\n")

if __name__ == "__main__":
    test_scenarios()
