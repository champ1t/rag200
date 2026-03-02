
import json
import sys
import os
import yaml
import time
from pathlib import Path

# Add src to path
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine

def run_test_suite():
    # Load config
    config_path = "configs/config.yaml"
    if not os.path.exists(config_path):
        print(f"Error: Config not found at {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Initialize Engine
    print("Initializing ChatEngine...")
    engine = ChatEngine(config)
    print("ChatEngine initialized.\n")

    test_cases = [
        # --- 1.1 Regression Tests ---
        {"label": "Regression: Exact Match", "query": "zte sw command", "expected_route": "article_link_only_exact"},
        {"label": "Regression: Soft-norm Match", "query": "ZTE--SW--Command", "expected_route": "article_link_only_exact"},
        {"label": "Regression: Normal Article (Summary)", "query": "GPON Overview", "expected_route": "article_answer"},
        {"label": "Regression: Primary Vendor Sanity", "query": "Huawei manual", "expected_route": None}, # Should NOT be blocked_vendor

        # --- 1.2 Boundary / Adversarial ---
        {"label": "Boundary: Ambiguity (Short)", "query": "zte sw", "expected_route": "blocked_ambiguous"},
        {"label": "Boundary: Ambiguity (Mixed)", "query": "command zte sw overview", "expected_route": "blocked_ambiguous"},
        {"label": "Boundary: Comparison (Cross-vendor)", "query": "ZTE OLT vs Huawei OLT", "expected_route": "blocked_scope"},
        {"label": "Boundary: Cisco (Adversarial)", "query": "Cisco command like ZTE", "expected_route": "blocked_vendor_out_of_scope"},

        # --- 1.3 Thai Language Stress Test ---
        {"label": "Thai Stress: Mixed Lang", "query": "ขอ command zte sw ที่ใช้ config vlan หน่อย", "expected_route": "article_link_only_exact"},
        {"label": "Thai Stress: Spacing Error", "query": "zte  sw    command", "expected_route": "article_link_only_exact"},
        {"label": "Thai Stress: Long Query/Short Intent", "query": "ขอ command zte sw ที่ใช้ config vlan หน่อย แบบที่อยู่ใน manual", "expected_route": "article_link_only_exact"},
    ]

    results = []

    print(f"{'Label':<40} | {'Route':<30} | {'Status':<10}")
    print("-" * 88)

    for tc in test_cases:
        label = tc["label"]
        query = tc["query"]
        expected = tc["expected_route"]
        
        try:
            res = engine.process(query)
            route = res.get("route")
            audit = res.get("audit", {})
            reason = audit.get("decision_reason", "N/A")
            
            # Simple pass/fail based on route if expected is provided
            status = "PASS"
            if expected and route != expected:
                status = "FAIL"
            
            # Special case for Primary Vendor Sanity
            if label == "Regression: Primary Vendor Sanity" and route == "blocked_vendor_out_of_scope":
                status = "FAIL"

            print(f"{label:<40} | {str(route):<30} | {status:<10}")
            
            results.append({
                "label": label,
                "query": query,
                "route": route,
                "expected": expected,
                "status": status,
                "reason": reason,
                "normalized_query": audit.get("normalized_query")
            })
        except Exception as e:
            print(f"{label:<40} | ERROR: {str(e):<23} | FAIL")
            results.append({"label": label, "query": query, "status": "ERROR", "error": str(e)})

    # Log results to file
    with open("PHASE23_TEST_RESULTS.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Generate Markdown Summary
    with open("PHASE23_TEST_RESULTS.md", "w", encoding="utf-8") as f:
        f.write("# Phase 23 Test Results\n\n")
        f.write("| Label | Query | Route | Status | Decision Reason |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for r in results:
            f.write(f"| {r['label']} | `{r['query']}` | `{r['route']}` | {r['status']} | {r.get('reason', 'N/A')} |\n")

    print(f"\nResults saved to PHASE23_TEST_RESULTS.md")

if __name__ == "__main__":
    run_test_suite()
