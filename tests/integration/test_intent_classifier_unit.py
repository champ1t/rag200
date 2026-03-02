
import unittest
import sys
import os

# Ensure src is in path
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine

# Mock config to initialize engine
MOCK_CONFIG = {
    "llm": {"model": "mock", "base_url": "mock"},
    "chat": {"show_context": False},
    "rag": {"use_cache": False},
    "security": {"hardening_threshold": 0.8},
    "retrieval": {"top_k": 3}
}

class TestIntentClassifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize engine once
        cls.engine = ChatEngine(MOCK_CONFIG)
        # Mock dependencies unlikely to be needed for just this method, 
        # but safe to have if __init__ does heavy lifting.
        # ChatEngine.__init__ loads resources, might take a second.
        
    def classify(self, query):
        return self.engine._classify_request_category(query)

    # 1. TECH_ARTICLE_LOOKUP (Vendor + Model / SMC-specific)
    def test_tech_lookup_valid(self):
        queries = [
            "Huawei NE8000 config",
            "Cisco ASR9006 command",
            "ZTE C300 oli",
            "Nokia 7750 features",
            "Meru wifi setup"
        ]
        for q in queries:
            with self.subTest(query=q):
                self.assertEqual(self.classify(q), "TECH_ARTICLE_LOOKUP")

    # 2. NON_SMC_TECH (Blocked Scenarios)
    def test_non_smc_tech(self):
        queries = [
            "Juniper MX960 configuration", # Non-SMC vendor
            "How to configure generic router", # Generic tech, no vendor
            "What is OSPF protocol?", # Tech term, no SMC context
            "Fiber optic cable types", # Tech term
            "Avaya switch setup" # Non-SMC vendor
        ]
        for q in queries:
            with self.subTest(query=q):
                self.assertEqual(self.classify(q), "NON_SMC_TECH")

    # 3. GENERAL_CHAT (Safe Response)
    def test_general_chat(self):
        queries = [
            "Hello there",
            "Good morning",
            "Who are you?",
            "What can you do?",
            "Tell me a joke"
        ]
        for q in queries:
            with self.subTest(query=q):
                self.assertEqual(self.classify(q), "GENERAL_CHAT")

    # 4. INVALID_QUERY (Nonsense)
    def test_invalid_query(self):
        queries = [
            "a", 
            "!",
            "", 
            "   ",
            "."
        ]
        for q in queries:
            with self.subTest(query=q):
                self.assertEqual(self.classify(q), "INVALID_QUERY")

    # 5. Edge Cases / Reviewer Traps
    def test_reviewer_edge_cases(self):
        # "Huawei" alone -> TECH (Contextual, but likely Tech)
        self.assertEqual(self.classify("Huawei"), "TECH_ARTICLE_LOOKUP")
        
        # "Config" alone -> NON_SMC_TECH (Too vague, no vendor)
        self.assertEqual(self.classify("Config"), "NON_SMC_TECH")
        
        # "Why is the sky blue?" -> GENERAL_CHAT
        self.assertEqual(self.classify("Why is the sky blue?"), "GENERAL_CHAT")

if __name__ == "__main__":
    unittest.main()
