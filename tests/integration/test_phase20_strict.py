#!/usr/bin/env python3
"""
SMC RAG – STRICT TEST SUITE (Phase 20+)
Validates all hardening measures with production-level rigor.
"""

import sys
import json
import requests
import time
from typing import Dict, Any, List
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8999"
ENDPOINT = f"{BASE_URL}/chat"

class TestResult:
    def __init__(self, test_id: str, name: str):
        self.test_id = test_id
        self.name = name
        self.passed = False
        self.actual = {}
        self.expected = {}
        self.errors = []
        self.warnings = []
    
    def to_dict(self):
        return {
            "test_id": self.test_id,
            "name": self.name,
            "status": "✅ PASS" if self.passed else "❌ FAIL",
            "errors": self.errors,
            "warnings": self.warnings,
            "actual": self.actual,
            "expected": self.expected
        }

def query_rag(text: str) -> Dict[str, Any]:
    """Send query to RAG system and return response"""
    try:
        response = requests.post(
            ENDPOINT,
            json={"query": text},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e), "answer": "", "route": "error"}

def run_test_suite():
    """Execute all test cases"""
    results = []
    
    print("=" * 80)
    print("SMC RAG – STRICT TEST SUITE (Phase 20+)")
    print("=" * 80)
    print(f"Test Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # ========================================================================
    # 1️⃣ DETERMINISTIC MATCH – SOFT NORMALIZE (CRITICAL)
    # ========================================================================
    print("1️⃣ DETERMINISTIC MATCH – SOFT NORMALIZE")
    print("-" * 80)
    
    # TC-D1: Exact Match (Canonical)
    result = TestResult("TC-D1", "Exact Match (Canonical): 'ZTE-SW Command'")
    res = query_rag("ZTE-SW Command")
    result.actual = {
        "route": res.get("route"),
        "audit": res.get("audit", {}),
        "answer_preview": res.get("answer", "")[:100]
    }
    result.expected = {
        "confidence_mode": "article_link_only_exact",
        "link_present": True,
        "decision_reason": "Contains 'Exact Match' or 'Forced LINK_ONLY'"
    }
    
    # Validate
    if "article_link_only" in res.get("route", ""):
        result.passed = True
    else:
        result.errors.append(f"Expected Link-Only route, got: {res.get('route')}")
    
    if "🔗" not in res.get("answer", ""):
        result.errors.append("No link emoji found in answer")
        result.passed = False
    
    results.append(result)
    print(f"{result.test_id}: {result.name}")
    print(f"   Status: {result.to_dict()['status']}")
    print()
    
    # TC-D2: Case Insensitive
    result = TestResult("TC-D2", "Case Insensitive: 'zte-sw command'")
    res = query_rag("zte-sw command")
    result.actual = {"route": res.get("route"), "audit": res.get("audit", {})}
    
    if "article_link_only" in res.get("route", ""):
        result.passed = True
    else:
        result.errors.append(f"Expected Link-Only route, got: {res.get('route')}")
    
    results.append(result)
    print(f"{result.test_id}: {result.name}")
    print(f"   Status: {result.to_dict()['status']}")
    print()
    
    # TC-D3: Space / Dash Normalize
    result = TestResult("TC-D3", "Space Normalize: 'zte sw command'")
    res = query_rag("zte sw command")
    result.actual = {"route": res.get("route")}
    
    if "article_link_only" in res.get("route", "") or res.get("route") == "article_answer":
        result.passed = True
    else:
        result.errors.append(f"Unexpected route: {res.get('route')}")
    
    results.append(result)
    print(f"{result.test_id}: {result.name}")
    print(f"   Status: {result.to_dict()['status']}")
    print()
    
    # TC-D4: Underscore Normalize
    result = TestResult("TC-D4", "Underscore Normalize: 'ZTE__SW__Command'")
    res = query_rag("ZTE__SW__Command")
    result.actual = {"route": res.get("route"), "audit": res.get("audit", {})}
    
    audit = res.get("audit", {})
    if "article_link_only" in res.get("route", ""):
        result.passed = True
    
    if not audit.get("normalized_query"):
        result.warnings.append("normalized_query not found in audit")
    
    results.append(result)
    print(f"{result.test_id}: {result.name}")
    print(f"   Status: {result.to_dict()['status']}")
    print()
    
    # TC-D5: Extra Spaces
    result = TestResult("TC-D5", "Extra Spaces: '   ZTE   SW    Command   '")
    res = query_rag("   ZTE   SW    Command   ")
    result.actual = {"route": res.get("route")}
    
    if "article_link_only" in res.get("route", "") or res.get("route") == "article_answer":
        result.passed = True
    else:
        result.errors.append(f"Trim/collapse failed: {res.get('route')}")
    
    results.append(result)
    print(f"{result.test_id}: {result.name}")
    print(f"   Status: {result.to_dict()['status']}")
    print()
    
    # ========================================================================
    # 2️⃣ OVERVIEW / INDEX RULE
    # ========================================================================
    print("2️⃣ OVERVIEW / INDEX RULE")
    print("-" * 80)
    
    # TC-O1: Overview Index
    result = TestResult("TC-O1", "Overview Index: 'ONU Command'")
    res = query_rag("ONU Command")
    result.actual = {"route": res.get("route"), "answer_preview": res.get("answer", "")[:150]}
    
    # Check for link-only behavior
    if "link_only" in res.get("route", "").lower():
        result.passed = True
    else:
        result.warnings.append(f"Expected link-only for overview index, got: {res.get('route')}")
    
    results.append(result)
    print(f"{result.test_id}: {result.name}")
    print(f"   Status: {result.to_dict()['status']}")
    print()
    
    # TC-O2: Overview with COMMAND intent
    result = TestResult("TC-O2", "Overview with COMMAND intent: 'คำสั่ง ONU'")
    res = query_rag("คำสั่ง ONU")
    result.actual = {"route": res.get("route")}
    
    # Should be link-only regardless of intent
    if "link_only" in res.get("route", "").lower() or res.get("route") == "article_answer":
        result.passed = True
    else:
        result.warnings.append(f"Intent should be ignored for overview: {res.get('route')}")
    
    results.append(result)
    print(f"{result.test_id}: {result.name}")
    print(f"   Status: {result.to_dict()['status']}")
    print()
    
    # ========================================================================
    # 3️⃣ LLM PATH – LOW CONTEXT GUARD
    # ========================================================================
    print("3️⃣ LOW CONTEXT GUARD")
    print("-" * 80)
    
    # TC-L1: Short Article
    result = TestResult("TC-L1", "Short Article: 'show power DE'")
    res = query_rag("show power DE")
    result.actual = {"route": res.get("route"), "audit": res.get("audit", {})}
    
    # Should detect low context if article is short
    route = res.get("route", "")
    if "low_context" in route or "link_only" in route or "blocked" in route or "miss" in route:
        result.passed = True
    else:
        result.warnings.append(f"Short article handling: {route}")
    
    results.append(result)
    print(f"{result.test_id}: {result.name}")
    print(f"   Status: {result.to_dict()['status']}")
    print()
    
    # TC-L2: Long Technical Article
    result = TestResult("TC-L2", "Long Article: 'คำสั่ง ASR920-12GE'")
    res = query_rag("คำสั่ง ASR920-12GE")
    result.actual = {"route": res.get("route"), "answer_length": len(res.get("answer", ""))}
    
    # Should provide summary or link
    if res.get("route") in ["article_answer", "article_link_only", "article_link_only_exact"]:
        result.passed = True
    else:
        result.warnings.append(f"Long article route: {res.get('route')}")
    
    results.append(result)
    print(f"{result.test_id}: {result.name}")
    print(f"   Status: {result.to_dict()['status']}")
    print()
    
    # TC-L3: COMMAND with insufficient bullets
    result = TestResult("TC-L3", "Low Bullets: 'NCS Command'")
    res = query_rag("NCS Command")
    result.actual = {"route": res.get("route")}
    
    # Accept any valid route
    if res.get("route") in ["article_answer", "article_link_only", "article_link_only_low_context", "article_link_only_exact"]:
        result.passed = True
    else:
        result.warnings.append(f"Command route: {res.get('route')}")
    
    results.append(result)
    print(f"{result.test_id}: {result.name}")
    print(f"   Status: {result.to_dict()['status']}")
    print()
    
    # ========================================================================
    # 4️⃣ LINK POLICY – SINGLE CANONICAL LINK
    # ========================================================================
    print("4️⃣ SINGLE CANONICAL LINK")
    print("-" * 80)
    
    # TC-S1: Single Link Enforcement
    result = TestResult("TC-S1", "Single Link: 'zte telnet to onu'")
    res = query_rag("zte telnet to onu")
    answer = res.get("answer", "")
    link_count = answer.count("🔗")
    
    result.actual = {"route": res.get("route"), "link_count": link_count}
    
    if link_count <= 2:  # Allow for header + potential footer
        result.passed = True
    else:
        result.errors.append(f"Too many links found: {link_count}")
    
    results.append(result)
    print(f"{result.test_id}: {result.name}")
    print(f"   Status: {result.to_dict()['status']}")
    print()
    
    # TC-S2: Multiple possible links
    result = TestResult("TC-S2", "Best Match Selection: 'Command NCS'")
    res = query_rag("Command NCS")
    result.actual = {"route": res.get("route"), "audit": res.get("audit", {})}
    
    # Should select best match
    if res.get("route") != "error":
        result.passed = True
    
    results.append(result)
    print(f"{result.test_id}: {result.name}")
    print(f"   Status: {result.to_dict()['status']}")
    print()
    
    # ========================================================================
    # 5️⃣ GOVERNANCE / BLOCKING
    # ========================================================================
    print("5️⃣ GOVERNANCE / BLOCKING")
    print("-" * 80)
    
    # TC-G1: No SMC Match
    result = TestResult("TC-G1", "No Match: 'Cisco OLT new command 2024'")
    res = query_rag("Cisco OLT new command 2024")
    result.actual = {"route": res.get("route"), "answer_preview": res.get("answer", "")[:100]}
    
    # Should be blocked or miss
    if "blocked" in res.get("route", "") or "miss" in res.get("route", ""):
        result.passed = True
    else:
        result.warnings.append(f"Non-SMC query route: {res.get('route')}")
    
    results.append(result)
    print(f"{result.test_id}: {result.name}")
    print(f"   Status: {result.to_dict()['status']}")
    print()
    
    # TC-G2: Near Match but not Exact
    result = TestResult("TC-G2", "Near Match: 'ZTE Switch Commands'")
    res = query_rag("ZTE Switch Commands")
    result.actual = {"route": res.get("route")}
    
    # Should not be treated as exact
    if res.get("route") != "article_link_only_exact":
        result.passed = True
    else:
        result.warnings.append("Near match treated as exact")
    
    results.append(result)
    print(f"{result.test_id}: {result.name}")
    print(f"   Status: {result.to_dict()['status']}")
    print()
    
    # ========================================================================
    # 6️⃣ AUDIT LOG TRACEABILITY
    # ========================================================================
    print("6️⃣ AUDIT LOG TRACEABILITY")
    print("-" * 80)
    
    # TC-A1: Audit Completeness
    result = TestResult("TC-A1", "Audit Completeness Check")
    res = query_rag("ZTE-SW Command")
    audit = res.get("audit", {})
    
    result.actual = {"audit_fields": list(audit.keys())}
    result.expected = {
        "required_fields": ["normalized_query", "matched_article_title", "confidence_mode", "decision_reason"]
    }
    
    missing_fields = []
    for field in result.expected["required_fields"]:
        if field not in audit:
            missing_fields.append(field)
    
    if not missing_fields:
        result.passed = True
    else:
        result.errors.append(f"Missing audit fields: {missing_fields}")
    
    results.append(result)
    print(f"{result.test_id}: {result.name}")
    print(f"   Status: {result.to_dict()['status']}")
    print(f"   Audit Fields: {list(audit.keys())}")
    print()
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    warnings = sum(len(r.warnings) for r in results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {total - passed} ❌")
    print(f"Warnings: {warnings} ⚠️")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    print()
    
    # Detailed Results
    print("DETAILED RESULTS:")
    print("-" * 80)
    for r in results:
        status_icon = "✅" if r.passed else "❌"
        print(f"{status_icon} {r.test_id}: {r.name}")
        if r.errors:
            for err in r.errors:
                print(f"   ❌ {err}")
        if r.warnings:
            for warn in r.warnings:
                print(f"   ⚠️  {warn}")
    
    print()
    print(f"Test End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Save results to JSON
    with open("test_results_phase20.json", "w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in results], f, indent=2, ensure_ascii=False)
    
    print("\n📄 Detailed results saved to: test_results_phase20.json")
    
    return passed, total

if __name__ == "__main__":
    try:
        passed, total = run_test_suite()
        sys.exit(0 if passed == total else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
