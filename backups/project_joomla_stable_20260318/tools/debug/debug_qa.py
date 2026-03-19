
import sys
import os
import yaml
from pprint import pprint

# Setup paths
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine

def debug_query(query):
    print(f"--- Debugging Query: {query} ---")
    
    # Load Config
    with open("configs/config.yaml", "r") as f:
        cfg = yaml.safe_load(f)
    
    # Init Engine
    engine = ChatEngine(cfg)
    
    # Mock Session
    res = engine.process(query, session_id="debug_session")
    
    print("\n--- Result ---")
    print(f"Route: {res.get('route')}")
    print(f"Answer: {res.get('answer')}")
    
    # If possible, inspect engine internals usually requires modifying code or logging.
    # But checking 'route' is a good first step.

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "มาตรฐาน5ส"
    debug_query(q)
