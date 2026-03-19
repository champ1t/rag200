
import unittest
from unittest.mock import MagicMock, patch
from src.chat_engine import ChatEngine
from src.ai.router import IntentRouter
from src.rag.handlers.dispatch_mapper import DispatchMapper
from src.rag.handlers.directory_handler import DirectoryHandler

class TestDispatchAndRouting(unittest.TestCase):
    def setUp(self):
        # Mock Config and Components
        self.mock_llm_cfg = {"base_url": "http://mock", "model": "mock"}
        self.router = IntentRouter(self.mock_llm_cfg)
        
        # Mock Directory Handler
        self.mock_dir_handler = MagicMock(spec=DirectoryHandler)
        self.mock_dir_handler.handle_management_query.return_value = {
            "answer": "[บทบาท]\n- ชื่อ: Mock Executive",
            "route": "position_lookup"
        }
        
        # Mock ChatEngine (Partial)
        mock_cfg = {
            "llm": self.mock_llm_cfg,
            "retrieval": {"top_k": 5},
            "chat": {"save_log": False}
        }
        self.engine = ChatEngine(cfg=mock_cfg)
        self.engine.router = self.router
        self.engine.directory_handler = self.mock_dir_handler
        self.engine.kp_manager = MagicMock()
        self.engine.save_log = False
        
        # Mock Cache for DispatchMapper
        self.mock_cache = MagicMock()
        self.mock_cache._url_to_text = {
            "http://dispatch": "[Title] การจ่ายงานเลขหมายวงจรเช่า (SCOMS)\n\n**ปัตตานี**\nXBN000201: ติดต่อ 073-123456\n\n**ตรัง**\n(Fallback Header)\nTRANG001: 075-111222"
        }
        self.engine.processed_cache = self.mock_cache

    def test_management_lookup_routing(self):
        """Test 'รายชื่อผู้บริหาร' maps to MANAGEMENT_LOOKUP"""
        q = "รายชื่อผู้บริหาร"
        res = self.router.route(q)
        self.assertEqual(res["intent"], "MANAGEMENT_LOOKUP")
        
        # Simulate ChatEngine flow
        # We need to bypass `process` fully or mock router return inside engine?
        # ChatEngine.process calls router.route(q)
        # engine.router is set to self.router.
        
        # Mock engine.corrector
        self.engine.corrector = MagicMock()
        self.engine.corrector.correct.return_value = q
        
        # Run process (mock internal specific handlers to avoid side effects except DirHandler)
        with patch.object(self.engine, "_log_telemetry"):
            res = self.engine.process(q)
            
        self.mock_dir_handler.handle_management_query.assert_called()
        self.assertEqual(res["route"], "position_lookup")

    def test_dispatch_fuzzy_typo(self):
        """Test 'ปัตตนี' typo correction via DispatchMapper"""
        q = "การจ่ายงานเลขหมายวงจรเช่าปัตตนี" # Typo
        # Check DispatchMapper directly first
        res = DispatchMapper.handle(q, self.mock_cache)
        self.assertIn("ปัตตานี", res["answer"])
        self.assertIn("073-123456", res["answer"])
        self.assertEqual(res["route"], "dispatch_mapper_hit")

    def test_dispatch_fallback_regex(self):
        """Test 'ตรัง' via Fallback Regex (simulated missing map entry)"""
        # We need to simulate that 'ตรัง' is NOT in the parsed map, but IS in text
        # DispatchMapper._parse_dispatch_article relies on extractors.
        # If we use a tricky format for 'ตรัง' in mock_cache that parser misses but regex hits?
        # Standard parser looks for "**Header**".
        # Let's mock _parse_dispatch_article to miss 'ตรัง'
        
        original_parser = DispatchMapper._parse_dispatch_article
        
        def mock_parser(text):
            # Return valid map for Patani, but miss Trang
            return {"ปัตตานี": "XBN000201: ติดต่อ 073-123456"}
            
        with patch("src.rag.handlers.dispatch_mapper.DispatchMapper._parse_dispatch_article", side_effect=mock_parser):
            q = "การจ่ายงานเลขหมายวงจรเช่าตรัง"
            res = DispatchMapper.handle(q, self.mock_cache)
            
            # Should hit Fallback Logic
            self.assertIn("ตรัง (Fallback)", res["answer"])
            self.assertIn("TRANG001", res["answer"])

    def test_followup_state(self):
        """Test 'awaiting_province' state flow"""
        # 1. Ask general -> Get General Answer + Context
        q1 = "การจ่ายงานเลขหมายวงจรเช่า"
        
        # Mock DispatchMapper.is_match = True
        # Mock handle returning general
        with patch("src.rag.handlers.dispatch_mapper.DispatchMapper.handle") as mock_handle:
            mock_handle.return_value = {
                "answer": "ข้อมูลทั่วไป...ระบุจังหวัด",
                "route": "dispatch_mapper_general",
                "context": "awaiting_province"
            }
            res1 = self.engine.process(q1)
            self.assertEqual(res1["context"], "awaiting_province")
            
            # Mimic saving context (The loop in main/server does this, but engine.last_context stores it for NEXT turn)
            # engine.process doesn't automatically set last_context for next call in UNIT TEST unless we mock session/persistence.
            # We must manually set engine.last_context for next call.
            self.engine.last_context = {"context": "awaiting_province"}
            
            # 2. Ask "ปัตตนี" (Typo) -> Should hit Followup
            q2 = "ปัตตนี"
            # This time, DispatchMapper.is_match might be False (it checks for 'จ่ายงาน' etc.)
            # But the 'awaiting_province' block is checked BEFORE is_match.
            
            # We need DispatchMapper.handle_followup to be called
            # and it should call handle(), which calls extract_location -> fuzzy match
            
            # We'll use REAL DispatchMapper.handle_followup logic here (no mock on handle_followup)
            # But we need mock_handle (handle) to return the specific result for Pattani
            mock_handle.return_value = {
                "answer": "**ปัตตานี**...",
                "route": "dispatch_mapper_hit"
            }
            
            res2 = self.engine.process(q2)
            
            # Verify Flow
            # It should have called handle_followup, which calls handle
            # And returned dispatch result
            self.assertEqual(res2["route"], "dispatch_mapper_hit")
            
            
if __name__ == '__main__':
    unittest.main()
