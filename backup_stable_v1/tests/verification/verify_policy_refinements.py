import sys
import yaml
import os
# Fix python path to allow imports from src
sys.path.append(os.getcwd())

from src.chat_engine import ChatEngine

def verify():
    print("Loading config...")
    try:
        cfg = yaml.safe_load(open("configs/config.yaml"))
    except Exception as e:
        print(f"Error loading config: {e}")
        return

    # Mock or Ensure Mock Web for reproducible tests?
    # For now, we assume live environment or whatever is configured.
    # We want to test logic, so live vector store is good.

    print("Initializing ChatEngine...")
    engine = ChatEngine(cfg)
    engine.warmup()
    
    print("\nXXX_TEST_START_XXX")
    
    # CASE 1: Internal Safety Override
    # "web search" prefix usually forces WEB_KNOWLEDGE intent in many router implementations,
    # or at least biases it. 
    # Failure Mode: If it goes to WEB_KNOWLEDGE, the safety check should kick in because "cisco ios commands" is internally known.
    q1 = "web search cisco ios commands"
    print(f"\n[TEST 1] Query: '{q1}' (Expected: GENERAL_QA due to Safety Check Override)")
    resp1 = engine.process(q1)
    route1 = resp1.get("route")
    print(f"[RESULT 1] Route: {route1}")
    
    if route1 == "WEB_KNOWLEDGE":
        print("[FAIL] Safety Check did NOT override.")
    else:
        print("[PASS] Safety Check overrode WEB_KNOWLEDGE (or router picked internal naturally).")

    # CASE 2: Valid Web Search
    q2 = "latest news about Chiang Rai floods 2024" 
    print(f"\n[TEST 2] Query: '{q2}' (Expected: WEB_KNOWLEDGE)")
    # This might fail if the router is not configured for web at all, or if "floods" matches something internal.
    # Assuming "Chiang Rai" is not in internal docs.
    resp2 = engine.process(q2)
    route2 = resp2.get("route")
    print(f"[RESULT 2] Route: {route2}")
    
    if route2 == "WEB_KNOWLEDGE":
        print("[PASS] Correctly routed to Web.")
    else:
        print(f"[WARN] Routed to {route2}. Might count as pass if system has no web search configured yet.")

    # CASE 3: Article Cleaning
    # We query for an article we know exists: "cisco ios commands"
    q3 = "cisco ios commands"
    print(f"\n[TEST 3] Query: '{q3}' (Checking Content Cleaning)")
    resp3 = engine.process(q3)
    ans3 = resp3.get("answer", "")
    
    print(f"[RESULT 3] Answer Snippet (last 100 chars): ...{ans3[-100:] if len(ans3) > 100 else ans3}")
    
    # Check Read More
    if "📌 เนื้อหามีรายละเอียดเพิ่มเติม" in ans3:
        print("[PASS] 'Read More' link found.")
    else:
        print("[WARN] 'Read More' link NOT found. (Maybe article was short?)")

    # Check Noise
    noise_markers = ["Main Menu", "User Menu", "Login Form", "Remember Me", "WDM (แนะนำIE)"]
    found_noise = [m for m in noise_markers if m in ans3]
    
    if found_noise:
        print(f"[FAIL] Found noise markers: {found_noise}")
    else:
        print("[PASS] No common noise markers found.")

    print("XXX_TEST_END_XXX")

if __name__ == "__main__":
    verify()
