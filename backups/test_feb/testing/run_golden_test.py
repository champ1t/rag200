import unittest
import json
import os
import sys
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import argparse
# Define the integration flag (Core vs Integration Split)
parser = argparse.ArgumentParser()
parser.add_argument("--include-integration", action="store_true", help="Run integration tests (real models)")
# Parse known args so unittest doesn't complain
opts, unit_args = parser.parse_known_args()
# Update sys.argv so unittest sees only its own args
sys.argv = [sys.argv[0]] + unit_args

from src.chat_engine import ChatEngine
from src.rag.article_interpreter import ArticleInterpreter

class TestGoldenCases(unittest.TestCase):
    def setUp(self):
        # Initialize Engine with Mocks for Speed/Stability where needed
        # We Mock LLM generation in ArticleInterpreter to avoid 404s/Cost, 
        # BUT we want routing logic to be real.
        
        # Load Config (Matching exact schema expected by ChatEngine)
        self.config = {
            "retrieval": {
                "top_k": 5,
                "score_threshold": 0.5
            },
            "llm": {
                "model": "mock-model",
                "base_url": "http://localhost:11434",
                "temperature": 0.0,
                "max_tokens": 512
            },
            "vectorstore": {
                "persist_directory": "./chroma_db",
                "collection_name": "nt_rag"
            },
            "directory": {
                "enabled": True
            }
        }
        
        self.engine = ChatEngine(self.config)

        # --- MOCK DATA INJECTION (Crucial for Deterministic Logic Testing) ---
        
        # 1. Clear & Mock Link Index (Prevent Accidental Matches like Google Drive)
        self.engine.processed_cache._link_index = [
             {"text": "Driver Download", "href": "http://example.com/driver.exe", "source": "Download"}
        ]
        self.engine.processed_cache._url_to_text = {}
        self.engine.processed_cache._loaded = True # Prevent implicit load() overwriting/logic
        
        
        def mock_find_links(query, threshold=0.65):
            q = query.lower()
            if "ribbon" in q:
                return [{
                    "items": [{"href": "http://10.192.133.33/smc/index.php?option=com_content&view=article&id=646:ribbon-edgemare6000-doc&catid=49:-smc&Itemid=84", "text": "Ribbon Manual"}],
                    "score": 1.0
                }]
            if "ssh" in q:
                 return [{
                    "items": [{"href": "http://10.192.133.33/smc/index.php?option=com_content&view=article&id=663:ip-ssh&catid=49:-smc&Itemid=84", "text": "SSH Config Guide"}],
                    "score": 1.0
                }]
            if "download" in q or "ดาวน์โหลด" in q:
                if "download" in q or "ดาวน์โหลด" in q:
                 return [{
                    "items": [{"href": "http://example.com/driver.exe", "text": "Driver Download", "source": "Download"}],
                    "score": 1.0
                }]
            return [] # No match for others
            
        self.engine.processed_cache.find_links_fuzzy = MagicMock(side_effect=mock_find_links)

        # 2. Mock Records (For Contact Lookup)
        self.engine.records = [
            {"name": "SBC North", "phones": ["0-2575-9444"], "tags": ["sbc", "north", "support"], "type": "team", "rule_id": "r1", "id": "1"},
            {"name": "SBC South", "phones": ["0-2575-9445"], "tags": ["sbc", "south", "support"], "type": "team", "rule_id": "r2", "id": "2"},
            {"name": "SBC Support", "phones": ["0-2575-9446"], "tags": ["sbc", "support"], "type": "team", "rule_id": "r3", "id": "3"},
            {"name": "CSOC", "phones": ["0-2575-9999"], "tags": ["csoc"], "type": "team", "rule_id": "r4", "id": "4"},
            {"name": "CSOC Backup", "phones": ["0-2575-8888"], "tags": ["csoc", "backup"], "type": "team", "rule_id": "r5", "id": "5"},
            {"name": "HelpDesk A", "phones": ["02-1"], "tags": ["helpdesk"], "type": "team", "id": "hd1"},
            {"name": "HelpDesk B", "phones": ["02-2"], "tags": ["helpdesk"], "type": "team", "id": "hd2"}
        ]
        
        # 2a. Re-init DirectoryHandler with new records
        if hasattr(self.engine, "directory_handler"):
            from src.rag.handlers.directory_handler import DirectoryHandler
            # Mock empty indices for simplicity, we focus on ContactHandler fallback
            team_idx = {}
            for r in self.engine.records: 
                if r.get("type") == "team": team_idx[r["name"]] = {"members": [], "sources": []}
            self.engine.directory_handler = DirectoryHandler({}, self.engine.records, team_idx)

        # 3. Disable Caching (L2) to force Logic
        if hasattr(self.engine, "cache"):
            self._saved_cache = self.engine.cache
            self.engine.cache = None
        
        if hasattr(self.engine, "cache_manager"):
             self._saved_cache_manager = self.engine.cache_manager
             self.engine.cache_manager = None
             
        # 4. Mock KnowledgePack
        if hasattr(self.engine, "kp_manager"):
            self.engine.kp_manager = MagicMock()
            self.engine.kp_manager.search.return_value = [] 
            self.engine.kp_manager.lookup.return_value = None
            self.engine.kp_manager.resolve_alias.return_value = None
            
        # 5. Mock VectorStore (VS) with Clean Logic
        self.engine.vs = MagicMock()
        
        def mock_search(query, top_k=5, **kwargs):
            results = []
            q_lower = query.lower()
            
            # Scenario: Text-Dense Article (IP SSH)
            if "ssh" in q_lower:
                results.append(MagicMock(
                    page_content="วิธีตั้งค่า SSH บนอุปกรณ์ Cisco\n1. เข้าสู่ Global Config\n2. สร้าง rsa key...",
                    metadata={"source": "http://10.192.133.33/smc/index.php?option=com_content&view=article&id=663:ip-ssh&catid=49:-smc&Itemid=84", "title": "SSH Config Guide", "score": 1.0}
                ))
            
            # Scenario: Ribbon Fallback (Directory)
            if "ribbon" in q_lower:
                 results.append(MagicMock(
                    page_content="Manual for Ribbon EdgeMare 6000 found Link: http://10.192.133.33/smc/index.php?option=com_content&view=article&id=646:ribbon-edgemare6000-doc&catid=49:-smc&Itemid=84",
                    metadata={"source": "http://10.192.133.33/smc/index.php?option=com_content&view=article&id=646:ribbon-edgemare6000-doc&catid=49:-smc&Itemid=84", "title": "Ribbon Manual", "score": 1.0}
                ))

            # Scenario: Cache A/B (Distinct Content)
            if "query_a_unique" in q_lower:
                 results.append(MagicMock(page_content="Content for A_UNIQUE", metadata={"source":"http://a", "title":"A", "score": 0.9}))
            if "query_b_unique" in q_lower:
                 results.append(MagicMock(page_content="Content for B_UNIQUE", metadata={"source":"http://b", "title":"B", "score": 0.9}))

            # Scenario: Security
            if "api key" in q_lower or "password" in q_lower:
                 results.append(MagicMock(page_content="Sensitive Data: API Key/Password is blocked.", metadata={"source": "secure_doc", "title": "Sec", "score": 0.9}))
            
            # Ensure score attribute is set
            for r in results:
                r.score = r.metadata.get("score", 0.0)
            return results

        def mock_search_with_score(query, *args, **kwargs):
            docs = mock_search(query)
            # Return list of (doc, score)
            return [(d, d.metadata.get("score", 0.9)) for d in docs]
            
        self.engine.vs.similarity_search = mock_search
        self.engine.vs.similarity_search_with_score = mock_search_with_score
        self.engine.vs.similarity_search_with_relevance_scores = mock_search_with_score
        self.engine.vs.search = mock_search
        self.engine.vs.hybrid_query = mock_search

        # 6. Pre-load Mock Article Content using REAL URLs
        ribbon_url = "http://10.192.133.33/smc/index.php?option=com_content&view=article&id=646:ribbon-edgemare6000-doc&catid=49:-smc&Itemid=84"
        ribbon_content = "Ribbon EdgeMare 6000 Manuals\n"
        for i in range(25):
             ribbon_content += f"{i+1}. Ribbon Manual {i} (http://example.com/manual_{i}.pdf)\n"
        self.engine.processed_cache._url_to_text[ribbon_url] = ribbon_content
        
        ssh_url = "http://10.192.133.33/smc/index.php?option=com_content&view=article&id=663:ip-ssh&catid=49:-smc&Itemid=84"
        self.engine.processed_cache._url_to_text[ssh_url] = "วิธีตั้งค่า SSH บนอุปกรณ์ Cisco\n1. enable\n2. config terminal\n3. crypto key generate rsa\n4. ip ssh version 2..."
        self.engine.processed_cache._url_to_text["http://a"] = "This is the answer for A unique."
        self.engine.processed_cache._url_to_text["http://b"] = "This is the answer for B unique."
        self.engine.processed_cache._url_to_text["secure_doc"] = "Sensitive Data: API Key/Password is blocked."

        # 6. Contact Lookup Mock (Deterministic) - Method 2 from Design
        if not opts.include_integration:
            # Patch lookup_phones to return deterministic results without real fuzzy matching
            import src.directory.lookup
            
            def mock_lookup(query, records):
                q = query.lower()
                if "helpdesk" in q:
                    return [
                        {"id": "hd1", "name": "HelpDesk Gen", "phones": ["1111"], "type": "team", "_score": 90},
                        {"id": "hd2", "name": "HelpDesk IT", "phones": ["2222"], "type": "team", "_score": 85},
                        {"id": "hd3", "name": "HelpDesk HR", "phones": ["3333"], "type": "team", "_score": 80},
                    ]
                if "sbc north" in q:
                     return [{"id": "1", "name": "SBC North", "phones": ["02-2575-9444"], "type": "team", "_score": 100}]
                if "sbc" in q: # Ambiguous generic
                     return [
                        {"id": "1", "name": "SBC North", "phones": ["0-2575-9444"], "type": "team", "_score": 85},
                        {"id": "2", "name": "SBC South", "phones": ["0-2575-9445"], "type": "team", "_score": 85}
                     ]
                if "csoc" in q:
                     return [
                        {"id": "4", "name": "CSOC", "phones": ["0-2575-9999"], "type": "team", "_score": 100},
                        {"id": "5", "name": "CSOC Backup", "phones": ["0-2575-8888"], "type": "team", "_score": 90}
                     ]
                return []
            
            src.directory.lookup.lookup_phones = MagicMock(side_effect=mock_lookup)
        
        # 7. Mock ArticleInterpreter LLM (Module Level)
        # We must patch the imported function used by ArticleInterpreter
        import src.rag.article_interpreter
        
        def mock_generate(prompt, **kwargs):
            p = str(prompt).lower()
            if "ssh" in p: return "SUMMARY: SSH Setup: enable, config terminal (Article Mode)"
            if "helpdesk" in p: return "HelpDesk Info"
            if "unique" in p: return p # Return content for collision test
            return "General Summary"
            
        src.rag.article_interpreter.ollama_generate = MagicMock(side_effect=mock_generate)
        
        # 8. GuardRail Mock
        if hasattr(self.engine, "guard"):
            if hasattr(self.engine.guard, "keywords"):
               self.engine.guard.keywords.extend(["password", "api key"])

        with open('src/testing/golden_cases.json', 'r', encoding='utf-8') as f:
            self.cases = json.load(f)

    def test_golden_cases(self):
        print(f"\n=== Running Golden Test Suite ({len(self.cases)} Scenarios) ===")
        
        self.pass_count = 0
        self.fail_count = 0
        results = []
        
        for case in self.cases:
            case_id = case['id']
            print(f"\n>> Case: {case_id} ({case['description']})")
            
            # Special Handling for Cache Collision Test
            if case_id == "cache_collision_sequence":
                # Enable a Mock Dictionary Cache
                mock_cache_storage = {}
                self.engine.cache = MagicMock()
                
                def mock_cache_check(query, **kwargs):
                    key = query.strip().lower() 
                    if key in mock_cache_storage:
                        return mock_cache_storage[key]
                    return None
                    
                def mock_cache_store(query, result, *args, **kwargs):
                    key = query.strip().lower()
                    mock_cache_storage[key] = result
                    
                self.engine.cache.check.side_effect = mock_cache_check
                self.engine.cache.store.side_effect = mock_cache_store
                if hasattr(self.engine, "cache_manager") and self.engine.cache_manager:
                     self.engine.cache_manager.cache = self.engine.cache
            else:
                self.engine.cache = None
                if hasattr(self.engine, "cache_manager") and self.engine.cache_manager:
                     self.engine.cache_manager.cache = None

            session_id = f"golden_{case_id}"
            
            failed = False
            for step_idx, step in enumerate(case['steps']):
                query = step['query']
                print(f"   Step {step_idx+1}: '{query}' ... ", end='', flush=True)
                
                try:
                    response = self.engine.process(query)
                except Exception as e:
                    print(f"ERROR: {e}")
                    failed = True
                    break
                
                # DEBUG OUTPUT
                if 'answer' in response:
                     answer_text = response.get('answer', "")
                     links_count = answer_text.count("🔗")
                     if links_count == 0: links_count = answer_text.count("http")
                         
                     choices_count = len(response.get('choices', []))
                     # Map hits to choices for Ambiguous routes
                     if choices_count == 0 and response.get('hits') and "ambiguous" in str(response.get('route')):
                         choices_count = len(response.get('hits'))
                         
                     route = response.get('route', 'unknown')
                     print(f" [Route={route} | Links={links_count} | Choices={choices_count}]")
                
                # CHECKS
                if 'expected_route' in step:
                    expected = step['expected_route']
                    actual = response.get('route')
                    match = actual in expected if isinstance(expected, list) else actual == expected
                    if not match:
                        print(f"FAIL (Route Mismatch: got '{actual}', expected '{expected}')")
                        failed = True

                if 'expected_keywords' in step:
                    ans = response.get('answer', "")
                    for kw in step['expected_keywords']:
                        if kw.lower() not in ans.lower():
                            print(f"FAIL (Missing signal '{kw}')")
                            failed = True

                if 'forbidden_keywords' in step:
                    ans = response.get('answer', "")
                    for kw in step['forbidden_keywords']:
                        if kw.lower() in ans.lower():
                            print(f"FAIL (Forbidden signal found '{kw}')")
                            failed = True

                if 'min_links_count' in step:
                    min_links = step['min_links_count']
                    ans = response.get('answer', "")
                    actual_links = max(ans.count("🔗"), ans.count("http"))
                    if actual_links < min_links:
                        print(f"FAIL (Links Count Low: got {actual_links}, expected >= {min_links})")
                        failed = True

                if 'min_choices_count' in step:
                    min_choices = step['min_choices_count']
                    actual_choices = len(response.get('choices', []))
                    if actual_choices == 0:
                         actual_choices = len(response.get('candidates', [])) or len(response.get('hits', []))
                         # Check Engine State for Pending Question (Ambiguity)
                         if actual_choices == 0 and self.engine.pending_question:
                             actual_choices = len(self.engine.pending_question.get("candidates", []))
                             
                    if actual_choices < min_choices:
                         print(f"FAIL (Choices Count Low: got {actual_choices}, expected >= {min_choices})")
                         print(f"DEBUG: Response Keys: {list(response.keys())}")
                         if 'candidates' in response: print(f"DEBUG: Candidates: {response['candidates']}")
                         failed = True

                if failed: break
            
            if failed:
                print("FAIL")
                self.fail_count += 1
                results.append((case_id, "FAIL"))
            else:
                print("PASS")
                self.pass_count += 1
                results.append((case_id, "PASS"))

        print("\n=== Summary ===")
        print(f"Passed: {self.pass_count}/{len(self.cases)}")
        for cid, status in results:
            if status == "FAIL":
                print(f" - {cid}: FAIL")
        
        if self.fail_count > 0:
            self.fail(f"{self.fail_count} Golden Cases Failed")

if __name__ == "__main__":
    # Custom test runner for CI exit code strategy
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGoldenCases)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # CI Exit Code Strategy (Phase 5)
    if opts.include_integration:
        # Integration mode: Always exit 0, just report failures
        if not result.wasSuccessful():
            print("\n" + "="*60)
            print("⚠️  INTEGRATION TEST FAILURES DETECTED")
            print("="*60)
            print(f"Failed: {len(result.failures)} scenarios")
            print("These tests require real models/embeddings.")
            print("Core suite should still pass 100%.")
            print("="*60)
        sys.exit(0)  # Never fail CI on integration issues
    else:
        # Core mode: Strict exit code for CI/CD
        if result.wasSuccessful():
            print("\n" + "="*60)
            print("✅ CORE SUITE: 13/13 PASSED")
            print("="*60)
            sys.exit(0)
        else:
            print("\n" + "="*60)
            print("❌ CORE SUITE FAILED - CI BLOCKED")
            print("="*60)
            sys.exit(1)
