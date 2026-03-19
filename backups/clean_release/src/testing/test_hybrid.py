import unittest
import sys
import os
import shutil
from pathlib import Path

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.vectorstore.bm25 import SimpleBM25
from src.vectorstore.chroma import ChromaVectorStore

TEST_DIR = "data/test_vectorstore"
BM25_PATH = "data/test_bm25.json"

class TestHybridSearch(unittest.TestCase):
    def setUp(self):
        # Clean up
        if Path(TEST_DIR).exists():
            shutil.rmtree(TEST_DIR)
        if Path(BM25_PATH).exists():
            os.remove(BM25_PATH)
            
    def tearDown(self):
        # Clean up
        if Path(TEST_DIR).exists():
            shutil.rmtree(TEST_DIR)
        if Path(BM25_PATH).exists():
            os.remove(BM25_PATH)

    def test_bm25_standalone(self):
        """Test pure BM25 logic"""
        bm = SimpleBM25()
        bm.add_document("doc1", "apple banana")
        bm.add_document("doc2", "banana cherry")
        bm.add_document("doc3", "apple apple apple")
        
        # Test 1: "cherry" -> only doc2
        res = bm.get_scores("cherry", top_k=3)
        self.assertEqual(res[0][0], "doc2")
        self.assertGreater(res[0][1], 0)
        
        # Test 2: "apple" -> doc3 (high freq) > doc1
        res = bm.get_scores("apple", top_k=3)
        self.assertEqual(res[0][0], "doc3")
        self.assertEqual(res[1][0], "doc1")
        
    def test_hybrid_integration(self):
        """Test Chroma+BM25 Integration"""
        # ID: 20 -> Hybrid Retrieval
        
        vs = ChromaVectorStore(
            persist_dir=TEST_DIR, 
            collection_name="test_hybrid",
            bm25_path=BM25_PATH
        )
        
        docs = [
            "Error 503: Service Unavailable. Check upstream server.",
            "How to fix internet connection generally.",
            "VLAN 100 is reserved for Management traffic.",
            "Banana split recipe."
        ]
        ids = ["err503", "internet", "vlan100", "banana"]
        metas = [{"cat": "tech"}, {"cat": "guide"}, {"cat": "tech"}, {"cat": "food"}]
        
        print("Upserting...")
        vs.upsert(ids, docs, metas)
        
        # Verify BM25 file created
        self.assertTrue(Path(BM25_PATH).exists())
        
        # Test 1: Exact Technical Term "Error 503"
        # Vector might do okay, but BM25 should nail it.
        print("Query: Error 503")
        res = vs.hybrid_query("Error 503", top_k=2, alpha=0.3) # Heavy BM25 weight (0.3 vector, 0.7 bm25)
        self.assertEqual(res[0].metadata["cat"], "tech")
        self.assertIn("Error 503", res[0].text)
        
        # Test 2: Semantic "Network issue"
        # "internet" doc should win via Vector, BM25 might yield nothing
        print("Query: Network issue")
        res = vs.hybrid_query("Network issue", top_k=2, alpha=0.9) # Heavy Vector
        self.assertIn("internet", res[0].text.lower())
        
        # Test 3: Mixed "VLAN management"
        # "vlan100" has both "VLAN" and "Management"
        res = vs.hybrid_query("VLAN management", top_k=1, alpha=0.5)
        self.assertEqual(res[0].metadata["cat"], "tech")
        self.assertIn("VLAN 100", res[0].text)

if __name__ == "__main__":
    unittest.main()
