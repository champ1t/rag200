
import unittest
import sys
from unittest.mock import MagicMock

# Mock dependencies
sys.modules["requests"] = MagicMock()
sys.modules["chromadb"] = MagicMock()

from src.rag.generator import RAGGenerator
from src.rag.prompts import get_template, TEMPLATE_FACTUAL, TEMPLATE_CONCEPTUAL

class TestPhaseR2(unittest.TestCase):
    
    def test_template_selection(self):
        self.assertEqual(get_template("HOWTO_PROCEDURE"), TEMPLATE_FACTUAL)
        self.assertEqual(get_template("EXPLAIN"), TEMPLATE_CONCEPTUAL)
        self.assertNotEqual(get_template("GENERAL_QA"), TEMPLATE_FACTUAL)

    def test_token_budgeting(self):
        # We need to mock ollama_client.ollama_generate to inspect call args
        gen = RAGGenerator({"base_url": "mock", "model": "mock"})
        
        # Patch the ollama_generate function imported in generator
        import src.rag.generator
        original_ollama = src.rag.generator.ollama_generate
        src.rag.generator.ollama_generate = MagicMock(return_value="Mock Answer")
        
        try:
            # 1. Fact -> Low Limit
            gen.generate("q", [], "HOWTO_PROCEDURE")
            args, kwargs = src.rag.generator.ollama_generate.call_args
            self.assertEqual(kwargs["num_predict"], 256)
            
            # 2. Concept -> High Limit
            gen.generate("q", [], "EXPLAIN")
            args, kwargs = src.rag.generator.ollama_generate.call_args
            self.assertEqual(kwargs["num_predict"], 640)
            
        finally:
            src.rag.generator.ollama_generate = original_ollama

    def test_context_truncation(self):
        gen = RAGGenerator({"base_url": "mock", "model": "mock"})
        
        # Mock long doc
        long_doc = MagicMock()
        long_doc.text = "A" * 2000
        long_doc.metadata = {"title": "Long Doc"}
        
        # Patch ollama to capture prompt
        import src.rag.generator
        original_ollama = src.rag.generator.ollama_generate
        mock_ollama = MagicMock(return_value="Ans")
        src.rag.generator.ollama_generate = mock_ollama
        
        try:
            gen.generate("q", [long_doc], "GENERAL")
            args, kwargs = mock_ollama.call_args
            prompt = kwargs["prompt"]
            
            # Check if truncated (should not have 2000 As)
            self.assertIn("...(truncated)", prompt)
            self.assertLess(len(prompt), 3000) # Budget check
            
        finally:
            src.rag.generator.ollama_generate = original_ollama

if __name__ == "__main__":
    unittest.main()
