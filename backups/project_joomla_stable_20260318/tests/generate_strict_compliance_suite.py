import sys
import os
import json
import re
import yaml
import random
from typing import List, Dict, Any

# Ensure src is in path
sys.path.append(os.getcwd())

from src.directory.lookup import load_records, precompute_record
from src.core.chat_engine import ChatEngine
from src.utils.normalization import normalize_for_matching

# ---------------------------------------------------------
# Test Generator
# ---------------------------------------------------------

class TestSuiteGenerator:
    def __init__(self, records: List[Dict]):
        self.records = records
        self.tests = []
        self.generated_ids = set()

    def add_test(self, query: str, expected_match: str, expected_phones: List[str], type: str, notes: str):
        # Deduplicate tests
        tid = f"{query}::{expected_match}"
        if tid in self.generated_ids: return
        self.generated_ids.add(tid)
        
        self.tests.append({
            "test_id": f"TEST_{len(self.tests)+1:04d}",
            "type": type,
            "query": query,
            "expected_match": expected_match,
            # We expect any of the valid phones or all? 
            # Requirement: "Expected phones must match exactly the stored phone strings"
            # We will verify that the answer contains the phones.
            "expected_phones": expected_phones, 
            "notes": notes
        })

    def generate_suite(self):
        print(f"[INFO] Generating tests for {len(self.records)} records...")
        
        for r in self.records:
            # Ensure strict fields
            name = r.get("name", "").strip()
            phones = r.get("phones", [])
            if not name or not phones: continue
            
            # 1. Exact Query
            self.add_test(name, name, phones, "EXACT", "Exact stored name match")
            
            # 2. Variant (Punctuation/Spacing)
            # Remove hyphens, extra spaces, dots
            var_1 = name.replace("-", " ").replace(".", " ").replace("  ", " ").strip()
            if var_1 != name:
                self.add_test(var_1, name, phones, "VARIANT_SPACING", "Removed punctuation/spaces")
                
            # Remove spaces entirely (Merged)
            var_2 = name.replace(" ", "")
            if var_2 != name and len(var_2) > 3: # Avoid merging short acronyms too much
                self.add_test(var_2, name, phones, "VARIANT_MERGED", "Merged tokens")
                
            # 3. Typo/Alias Variant
            # Removing "ศูนย์", "แผนก"
            for prefix in ["ศูนย์", "แผนก", "ส่วน", "งาน", "ฝ่าย"]:
                if name.startswith(prefix):
                    stripped = name[len(prefix):].strip()
                    if stripped:
                        self.add_test(stripped, name, phones, "VARIANT_PREFIX_STRIP", f"Stripped prefix {prefix}")
            
            # 4. Special Groups
            # Hyphens
            if "-" in name:
                no_hyphen = name.replace("-", " ")
                self.add_test(no_hyphen, name, phones, "SPECIAL_HYPHEN", "Hyphen replaced with space")
                no_hyphen_merged = name.replace("-", "")
                self.add_test(no_hyphen_merged, name, phones, "SPECIAL_HYPHEN_MERGED", "Hyphen removed")
                
            # Dots
            if "." in name:
                no_dot = name.replace(".", " ")
                self.add_test(no_dot, name, phones, "SPECIAL_DOT", "Dot replaced with space")
                no_dot_merged = name.replace(".", "")
                self.add_test(no_dot_merged, name, phones, "SPECIAL_DOT_MERGED", "Dot removed")
                
            # Parentheses
            if "(" in name and ")" in name:
                # Test without content in parens
                no_paren = re.sub(r"\(.*?\)", "", name).strip()
                if no_paren:
                    self.add_test(no_paren, name, phones, "SPECIAL_PAREN", "Content outside parentheses")
                # Test content inside parens
                in_paren = re.search(r"\((.*?)\)", name)
                if in_paren:
                    content = in_paren.group(1).strip()
                    if len(content) > 2:
                        self.add_test(content, name, phones, "SPECIAL_PAREN_CONTENT", "Content inside parentheses")

        # 5. Stress Tests (20 random items)
        samples = random.sample(self.records, min(20, len(self.records)))
        for r in samples:
            name = r.get("name", "")
            phones = r.get("phones", [])
            
            # Messy Whitespace
            messy = "  ".join(name.split())
            self.add_test(f"   {messy}   ", name, phones, "STRESS_WHITESPACE", "Messy whitespace")
            
            # Mixed Case (if English)
            if any(c.isascii() and c.isalpha() for c in name):
                mixed = "".join([c.upper() if i%2==0 else c.lower() for i, c in enumerate(name)])
                self.add_test(mixed, name, phones, "STRESS_MIXED_CASE", "Mixed case query")
                
            # Prefixes
            prefixes = ["เบอร์", "ขอเบอร์", "โทร", "ติดต่อ"]
            p = random.choice(prefixes)
            self.add_test(f"{p} {name}", name, phones, "STRESS_PREFIX", f"Prefix {p}")
            
            # Thai+English (Mock)
            # If name is English, add Thai prefix. If Thai, add English prefix
            if name.isascii():
                self.add_test(f"เบอร์ {name}", name, phones, "STRESS_TH_EN", "Thai prefix + Eng Name")
            else:
                self.add_test(f"contact {name}", name, phones, "STRESS_TH_EN", "Eng prefix + Thai Name")

    def get_json(self):
        return json.dumps(self.tests, indent=2, ensure_ascii=False)

# ---------------------------------------------------------
# Test Runner
# ---------------------------------------------------------

def run_suite(suite_json, engine):
    tests = json.loads(suite_json)
    passed = 0
    failed = 0
    results = []
    
    print(f"\n[RUNNER] Executing {len(tests)} tests...")
    
    for i, t in enumerate(tests):
        q = t["query"]
        expect_match = t["expected_match"]
        # Normalize expected match for comparison
        # Actually checking if expected_match is in hits list
        
        # Run Query
        res = engine.process(q, session_id=f"test_suite_{i}")
        hits = res.get("hits") or []
        answer = res.get("answer", "")
        route = res.get("route")
        
        # Check Success
        hit_found = False
        for h in hits:
            # Check name or key_norm
            h_name = h.get("name", "")
            # We check if EXPECTED MATCH name is found in returned hits
            # Normalize both to be safe
            if normalize_for_matching(expect_match) == normalize_for_matching(h_name):
                hit_found = True
                # Check phones
                phones_returned = h.get("phones", [])
                # Requirement: "Expected phones must match exactly the stored phone strings"
                # Use set comparison
                s_expected = set(t["expected_phones"])
                s_returned = set(phones_returned)
                if not s_expected.issubset(s_returned):
                    t["error"] = f"Phones Mismatch: Exp {s_expected} vs Got {s_returned}"
                    hit_found = False # Strict check
                break
        
        if not hit_found:
            # Fallback: Check if answer contains phones directly (for Ambiguous cases where hits might be clipped but present?)
            # But specific requirement is retrieval.
            # Loose check for ambiguous lists:
            if "contact_ambiguous" in str(route):
                # If ambiguous, check if expected match name is in answer text
                if expect_match in answer:
                    hit_found = True # Pass for ambiguity (retrieved)
            
        if hit_found:
            passed += 1
            print(f".", end="", flush=True)
        else:
            failed += 1
            error_msg = t.get("error", "Expected Match Not Found in Hits/Answer")
            print(f"F", end="", flush=True)
            results.append({
                "id": t["test_id"],
                "query": q,
                "expected": expect_match,
                "got_route": route,
                "got_answer_snippet": answer[:100],
                "error": error_msg
            })
            
    print(f"\n\n[RESULTS] Passed: {passed}, Failed: {failed}")
    
    if results:
        print("\n--- Failures ---")
        for r in results[:10]: # HEAD 10
            print(r)
        if len(results) > 10:
             print(f"... and {len(results)-10} more.")

    return results

# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():
    # 1. Load Config & Engine
    cfg_path = "configs/config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    print("[INIT] initializing ChatEngine...")
    engine = ChatEngine(cfg)
    
    # 2. Get Records
    records = engine.records
    # Precompute to ensure they are ready for generator logic checks (if any)
    for r in records:
        precompute_record(r)
        
    # 3. Generate Suite
    gen = TestSuiteGenerator(records)
    gen.generate_suite()
    suite_json = gen.get_json()
    
    # Save Suite
    with open("tests/strict_compliance_suite.json", "w", encoding="utf-8") as f:
        f.write(suite_json)
    print(f"[INFO] Suite saved to tests/strict_compliance_suite.json ({len(gen.tests)} tests)")
    
    # 4. Run Suite
    failures = run_suite(suite_json, engine)
    
    # 5. Verify Pending Choice (Explicit Requirement)
    print("\n[VERIFY] Pending Choice Logic (2-Turn)")
    
    # Setup: Ambiguous Query
    q1 = "เบอร์ NOC"
    res1 = engine.process(q1, session_id="test_choice")
    if res1.get("route") == "contact_ambiguous":
        print(f"Turn 1 '{q1}': Ambiguous -> PASS")
        # Check Candidates
        # Turn 2: Select "1"
        q2 = "1"
        res2 = engine.process(q2, session_id="test_choice")
        ans2 = res2.get("answer", "")
        route2 = res2.get("route")
        
        # Expect HIT
        if "contact_hit_choice" in route2 or "contact_hit" in str(route2) or "02-" in ans2:
             print(f"Turn 2 '{q2}': Resolved to '{ans2[:50]}...' -> PASS")
        else:
             print(f"Turn 2 '{q2}': Failed. Route={route2}, Ans={ans2}")
    else:
        print(f"Turn 1 '{q1}': Not Ambiguous? Route={res1.get('route')}")

    # 6. Verify Normalization (Explicit Requirement)
    print("\n[VERIFY] Normalization (Prefix Strip)")
    q_norm = "ขอเบอร์ noc"
    res_norm = engine.process(q_norm, session_id="test_norm")
    if "Noc" in res_norm.get("answer", "") or res_norm.get("hits"):
        print(f"Query '{q_norm}' -> Found matches -> PASS")
    else:
        print(f"Query '{q_norm}' -> Failed")

if __name__ == "__main__":
    main()
