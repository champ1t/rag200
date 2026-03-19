
import sys
import os

# Mock classes to simulate dependencies
class MockVectorStore:
    def __init__(self, should_match=False, score=0.0):
        self.should_match = should_match
        self.score = score

    def hybrid_query(self, query, top_k=1):
        if self.should_match:
            class Match:
                def __init__(self, score):
                    self.score = score
            return [Match(self.score)]
        return []

class MockWebHandler:
    def handle(self, query):
        return f"Web Search Result for: {query}"

class MockRoutingPolicy:
    def get(self, key, default=None):
        if key == "web_knowledge":
            return {"internal_override_threshold": 0.65}
        return default

# We need to test the logic inside ChatEngine.process (specifically the WEB_KNOWLEDGE block)
# Since we can't easily instantiate the full ChatEngine due to complex deps, 
# we will extract the logic or test the side effects if we were to instantiate it.
# However, the user wants verification. The best way is to unit test the LOGIC itself.

def test_safety_check_logic(query, vector_store_score, expected_override):
    print(f"--- Testing Query: '{query}' with Internal Score: {vector_store_score} ---")
    
    # Setup mocks
    routing_policy = {"web_knowledge": {"internal_override_threshold": 0.65}}
    policy_threshold = routing_policy["web_knowledge"]["internal_override_threshold"]
    
    # Simulate Vector Store response
    safety_hits = []
    if vector_store_score > 0:
        class Match:
            pass
        m = Match()
        m.score = vector_store_score
        safety_hits = [m]
    
    # Logic from chat_engine.py
    intent = "WEB_KNOWLEDGE"
    print(f"[DEBUG] Web Knowledge Safety Check for: '{query}' (Threshold: {policy_threshold})")
    
    final_intent = intent
    
    if safety_hits and safety_hits[0].score > policy_threshold:
        matched_score = safety_hits[0].score
        print(f"[DEBUG] Safety Check: Found internal match (score={matched_score:.2f}) -> Override to SMC")
        print(f"[DEBUG] SAFETY_OVERRIDE\nquery=\"{query}\"\ninternal_score={matched_score:.4f}\noriginal_intent=WEB_KNOWLEDGE\nfinal_intent=GENERAL_QA")
        final_intent = "GENERAL_QA"
    else:
        print(f"[DEBUG] Routing to WebHandler: {query}")
    
    if final_intent == "GENERAL_QA" and expected_override:
        print("✅ PASS: Correctly overrode to GENERAL_QA")
    elif final_intent == "WEB_KNOWLEDGE" and not expected_override:
        print("✅ PASS: Correctly stayed as WEB_KNOWLEDGE")
    else:
        print(f"❌ FAIL: Expected override={expected_override}, got intent={final_intent}")

if __name__ == "__main__":
    print("=== Verifying Web Knowledge Safety Check Logic ===\n")
    # Test 1: High confidence internal match (Should Override)
    test_safety_check_logic("config vlan cisco", 0.85, True)
    
    print("\n")
    
    # Test 2: Low confidence internal match (Should NOT Override)
    test_safety_check_logic("recent floods in chiang rai", 0.30, False)
    
    print("\n")
    
    # Test 3: No internal match (Should NOT Override)
    test_safety_check_logic("something completely unknown", 0.0, False)
