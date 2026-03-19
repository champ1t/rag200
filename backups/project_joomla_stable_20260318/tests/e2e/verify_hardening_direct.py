
import json
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine
import yaml

# Load config
with open("configs/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Initialize Engine
engine = ChatEngine(config)

def test_query(label, query):
    print(f"\n--- [{label}] Query: {query} ---")
    res = engine.process(query)
    
    print(f"Route: {res.get('route')}")
    print(f"Answer: {res.get('answer')[:100]}...") # Print first 100 chars
    
    audit = res.get("audit", {})
    print("Audit Block:")
    print(json.dumps(audit, indent=2, ensure_ascii=False))
    
    return res

# 1) Exact Match
test_query("TC-V21-1: Exact Match", "zte sw command")

# 2) Soft Exact Match
test_query("TC-V21-2: Soft Exact Match", "ZTE--SW--Command")

test_query("TC-V21-3: Low Context Article", "authentication required")

# 4) Normal Article
test_query("TC-V21-4: Normal Article", "GPON Overview")

# 4) Non-SMC Vendor (Cisco)
test_query("TC-V22-1: Non-SMC Vendor", "Cisco OLT new command 2024")

# 5) Out-of-Scope Vendor (Juniper)
test_query("TC-V22-2: Out-of-Scope Vendor", "Juniper router config")

print("\n--- Verification Complete ---")
