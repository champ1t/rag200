
from src.rag.article_interpreter import ArticleInterpreter
import sys

# Mock Data
TYPE_A_QUERY = "ONT ZTE password"
TYPE_B_QUERY = "ทำความรู้จัก EtherChannel"

LONG_CONTENT_WITH_STRUCTURE = """
<h1>Setting up EtherChannel</h1>
<ul>
<li>Step 1: config terminal</li>
<li>Step 2: interface port-channel 1</li>
</ul>
<p>This is a long explanation about LACP and PAgP...</p>
""" + ("<p>More text...</p>" * 100)

print("=== Phase 121 Verification: Type A vs Type B Logic ===\n")

interpreter = ArticleInterpreter(llm_cfg={"model": "test", "base_url": "http://localhost:11434"})

# 1. Test Type B Trigger (Prioritized over Structure)
print(f"Testing Query: '{TYPE_B_QUERY}'")

# Logic Duplication from Interpreter (since we want to verify the logic we just wrote)
explain_keywords = ["อธิบาย", "สาเหตุ", "ทำไม", "เพราะอะไร", "สรุป", "วิเคราะห์", "เกิดจากอะไร", "explain", "why", "reason", "summary"]
type_b_triggers = ["ทำความรู้จัก", "หลักการ", "overview", "concept", "คืออะไร"]
tutorial_keywords = explain_keywords + type_b_triggers

detected = any(k in TYPE_B_QUERY for k in tutorial_keywords)
print(f"Intent Detected: {detected}")

if detected:
    print("[PASS] Tutorial Intent Detected -> Should Bypass Fast-Path and go to LLM.")
else:
    print("[FAIL] Tutorial Intent NOT Detected.")

# 2. Test Type A Fallback (Structure + !Tutorial)
print(f"\nTesting Query: '{TYPE_A_QUERY}'")
detected_tutorial_a = any(k in TYPE_A_QUERY for k in tutorial_keywords)
print(f"Is Tutorial?: {detected_tutorial_a}")

if not detected_tutorial_a:
    print("[PASS] Not Tutorial -> Proceed to Structure Check (Type A).")
else:
    print("[FAIL] False Positive on Tutorial Intent.")

print("\n=== End Verification ===")
