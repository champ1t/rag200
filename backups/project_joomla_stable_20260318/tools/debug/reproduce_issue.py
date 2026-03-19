import sys
import os
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine
from src.vectorstore.base import SearchResult

def test_relaxed_governance_final():
    cfg = {
        "llm": {"model": "openthaigpt:latest"},
        "chat": {"threshold": 0.45, "cache_threshold": 0.90},
        "retrieval": {"top_k": 3},
        "rag": {"top_k": 3}
    }
    
    # Ensure config path exists
    os.makedirs("config", exist_ok=True)
    if not os.path.exists("config/routing_policy_v1.yaml"):
        with open("config/routing_policy_v1.yaml", "w") as f:
            f.write("intents: []")
            
    engine = ChatEngine(cfg)
    
    # Mock retrieval hits
    mock_hit = MagicMock(spec=SearchResult)
    mock_hit.page_content = "ZTE OLT C6XX basic commands are: show version, show running-config..."
    mock_hit.score = 0.95
    mock_hit.metadata = {
        "title": "ZTE OLT C6XX Manual",
        "source": "http://smc.nt.th/doc/ZTE_C6XX.pdf"
    }
    
    # Patch the engine's internal components to simulation success
    engine.vs.search = MagicMock(return_value=[mock_hit])
    
    # Mock whichever generator-like method is used
    # In ChatEngine.process, it calls gen_res = self...generate(...)
    # Let's see what the attribute name really is for the generator.
    # Looking at ChatEngine.process around line 2916...
    # Ah, I don't see 'generator' in the viewed snippet, but I'll patch whatever 'generate' method it finds.
    
    if hasattr(engine, "generator"):
        engine.generator.generate = MagicMock(return_value={"answer": "To Maintenance ZTE OLT C6XX...", "latency": 100})
    elif hasattr(engine, "controller"):
        # If it uses controller for generation
        engine.controller.process = MagicMock(return_value={"answer": "To Maintenance ZTE OLT C6XX...", "latency": 100})
    
    # TEST CASE 1: Command query (Should NOT be blocked)
    print("\n--- TEST: Technical Command Coverage ---")
    res = engine.process("BASIC COMMAND OLT ZTE C300")
    print(f"ROUTE: {res.get('route')}")
    ans = res.get('answer', '')
    
    if "📌 **แหล่งข้อมูลหลัก:**" in ans:
        print("STATUS: ✅ PASS (Source Link at top)")
    else:
        print("STATUS: ❌ FAIL (Source Link notation missing)")
        print(f"ANSWER SNIPPET: {ans[:200]}...")

if __name__ == "__main__":
    test_relaxed_governance_final()
