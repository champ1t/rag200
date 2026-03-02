
import asyncio
import os
import sys

# Ensure current directory is in python path
sys.path.insert(0, os.getcwd())

from src.core.chat_engine import ChatEngine
from src.config import load_config

async def test_summary():
    cfg = load_config()
    engine = ChatEngine(cfg)
    # Warmup to load resources
    print("[INFO] Warming up engine...")
    engine.warmup()
    
    print("\n\n=== TESTING SUMMARIZER v205 ===\n")
    query = "add adsl Huawei"
    print(f"Query: {query}")
    
    response = await engine.achat(query)
    print("\n--- RESPONSE START ---\n")
    print(response)
    print("\n--- RESPONSE END ---\n")

if __name__ == "__main__":
    asyncio.run(test_summary())
