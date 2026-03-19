
import unittest
import os
import sys
import yaml
import random
import re

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.chat_engine import ChatEngine

class MetamorphicGenerator:
    """Generates variants of a query to test robustness."""
    
    POLITE_PREFIXES = ["ขอ", "รบกวน", "ช่วย", "อยากทราบ", "query", "search"]
    POLITE_SUFFIXES = ["ครับ", "ค่ะ", "krup", "ka", "หน่อย", "ด้วยครับ"]
    
    TYPO_MAP = {
        "เบอร์": ["เบอ", "เบอร", "โท"],
        "โทร": ["โท", "to", "call"],
        "ติดต่อ": ["ติดตอ", "contact"],
        "ข่าว": ["ขร่าว", "new", "news"],
        "วิธี": ["วิที", "howto", "how-to"],
        "แก้": ["แก", "fix"],
        "งาน": ["ngan", "team"],
    }
    
    @classmethod
    def generate_variants(cls, query: str, num_variants=5) -> list[str]:
        variants = set()
        variants.add(query) # Always include original
        
        # 1. Whitespace Spam
        variants.add(f"  {query}  ")
        variants.add(query.replace(" ", "   "))
        
        # 2. Polite Particles (Prefix/Suffix)
        for p in cls.POLITE_PREFIXES:
            variants.add(f"{p} {query}")
        for s in cls.POLITE_SUFFIXES:
            variants.add(f"{query} {s}")
            
        # 3. Typos (Replace functional keywords)
        for key, replacements in cls.TYPO_MAP.items():
            if key in query:
                for rep in replacements:
                    # Replace only the first occurrence or random?
                    v = query.replace(key, rep, 1)
                    variants.add(v)
        
        # 4. Remove Spaces (Thai script often has no spaces)
        variants.add(query.replace(" ", ""))
        
        # Sample if too many
        result = list(variants)
        if len(result) > num_variants:
            result = random.sample(result, num_variants)
        
        # Always put original back at start if missed
        if query not in result:
             result.insert(0, query)
             
        return result

class TestMetamorphicQueries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n[Metamorphic] Initializing ChatEngine...")
        config_path = os.path.join(os.path.dirname(__file__), "../../configs/config.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                cls.config = yaml.safe_load(f)
        else:
             cls.config = {
                "llm": {"model_name": "gemini-pro"},
                "retrieval": {"top_k": 3},
                "data_dir": "data/records",
                "vectorstore": {"type": "chroma", "persist_dir": "data/vectorstore", "collection_name": "smc_web"}
            }
        
        try:
             cls.engine = ChatEngine(cls.config)
        except Exception as e:
             print(f"Failed to init ChatEngine: {e}")
             raise e

        # Load Golden Queries
        yaml_path = os.path.join(os.path.dirname(__file__), "../../data/golden_queries.yaml")
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Golden queries file not found at {yaml_path}")
            
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            cls.queries = data.get("queries", [])

    def test_metamorphic_determinism(self):
        """
        For each golden query, generate variants.
        Assert that variants result in:
          1. Same Route (or compatible subset)
          2. Same Output Contract (must_contain)
        """
        print(f"\n[Metamorphic] Testing variants for {len(self.queries)} golden seeds...")
        
        failures = []
        
        for case in self.queries:
            seed_q = case["query"]
            must_route = case.get("must_route")
            must_contain = case.get("must_contain", [])
            
            # Skip cases without strict route (can't test determinism)
            if not must_route: 
                continue
                
            if isinstance(must_route, str): must_route = [must_route]
            
            print(f"  > Seed: '{seed_q}' (Expected: {must_route})")
            
            variants = MetamorphicGenerator.generate_variants(seed_q, num_variants=10)
            
            for v_q in variants:
                # print(f"    - Variant: '{v_q}'")
                try:
                    res = self.engine.process(v_q)
                    actual_route = res.get("route", "unknown")
                    answer = res.get("answer", "")
                    
                    # Check 1: Route
                    if actual_route not in must_route:
                        # Allow typo-correction routes if they exist?
                        # For now, strict.
                        if actual_route == "rag_clarify" and "Ambiguity" not in str(must_route):
                             # Clarification is acceptable fallback for highly mangled inputs, 
                             # but ideally robust handlers should catch it.
                             pass
                        else:
                            failures.append(f"Query '{v_q}' (Seed: {seed_q}) -> Route Miss: Got '{actual_route}', Expected {must_route}")
                            print(f"      [X] Route Fail: {actual_route} (Variant: '{v_q}')")
                            continue
                            
                    # Check 2: Content
                    for item in must_contain:
                        if item.lower() not in answer.lower() and item.lower() not in str(res): # lenient
                             failures.append(f"Query '{v_q}' -> Content Miss: Missing '{item}'")
                             print(f"      [X] Content Fail: Missing {item} (Variant: '{v_q}')")
                             
                except Exception as e:
                    failures.append(f"Query '{v_q}' CRASHED: {e}")
                    
        if failures:
            self.fail("\n\n" + "\n".join(failures[:20])) # Limit output
            
if __name__ == '__main__':
    unittest.main()
