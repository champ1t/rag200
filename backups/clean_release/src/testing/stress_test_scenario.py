import sys
import os
import time
import unittest

# Ensure src is in path
sys.path.append(os.getcwd())

import yaml
from src.core.chat_engine import ChatEngine

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class StressTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n[StressTest] Initializing ChatEngine...")
        cls.config = load_config("configs/config.yaml")
        # Force production mode for strictness
        cls.config["chat"]["mode"] = "production"
        # Disable cache to test core RAG logic and prevent locks
        if "cache" not in cls.config: cls.config["cache"] = {}
        cls.config["cache"]["enabled"] = False
        
        cls.engine = ChatEngine(cls.config)
        # cls.engine.warmup() # Skip to avoid potential hang, first query acts as warmup
        
    def _test_query(self, query, expected_routes=None, required_text=None, forbidden_text=None):
        print(f"\nQ: {query}")
        start = time.time()
        
        # Reset Context to ensure independence
        self.engine.reset_context()
        
        resp = self.engine.process(query)
        duration = time.time() - start
        
        ans = resp["answer"]
        route = resp.get("route", "unknown")
        
        print(f"A: {ans[:100]}... (Route: {route}, Time: {duration:.2f}s)")
        
        # Validation
        errors = []
        if expected_routes:
            if isinstance(expected_routes, str): expected_routes = [expected_routes]
            if route not in expected_routes:
                errors.append(f"Bad Route: Got '{route}', Expected {expected_routes}")
                
        if required_text:
            for txt in required_text:
                if txt.lower() not in ans.lower():
                    errors.append(f"Missing text: '{txt}'")
                    
        if forbidden_text:
            for txt in forbidden_text:
                if txt.lower() in ans.lower():
                    errors.append(f"Forbidden text found: '{txt}'")
        
        if errors:
            print(f"❌ FAILED: {', '.join(errors)}")
            self.fail("; ".join(errors))
        else:
            print("✅ PASSED")

    # --- 1. Contact & Directory (5 Tests) ---
    def test_01_contact_role(self):
        self._test_query("เบอร์โทร ผส.บลตน.", expected_routes=["contact_hit_role", "position_holder_hit"], required_text=["โทร", "บลตน"])

    def test_02_contact_team(self):
        self._test_query("ใครดูแลงาน FTTx", expected_routes=["directory_hit_team", "contact_hit_team"], required_text=["FTTx"])

    def test_03_position_holder(self):
        # "ชจญ.ภ.4" not in data, use "ผจ.สบลตน."
        self._test_query("ใครตำแหน่ง ผจ.สบลตน.", expected_routes=["position_holder_hit", "clarify_ambiguous"], required_text=[])

    def test_04_name_lookup(self):
        # Generic name likely to be in mock/real data or fail safely
        self._test_query("เบอร์คุณสมชาย", expected_routes=["contact_hit_person", "contact_ambiguous", "contact_miss"])

    def test_05_ambiguous_role(self):
        self._test_query("เบอร์ ผส.", expected_routes=["contact_ambiguous"], required_text=["คุณหมายถึง"])

    # --- 2. Procedure & Knowledge (5 Tests) ---
    def test_06_howto_internet(self):
        self._test_query("เน็ตเสียต้องทำไง", expected_routes=["rag_clarify"], required_text=["แบบไหน"])

    def test_07_howto_specific(self):
        self._test_query("วิธีแก้ user lock", expected_routes=["article_answer", "rag_answer"], required_text=["user"])

    def test_08_knowledge_fact(self):
        self._test_query("DNS ของ NT คืออะไร", expected_routes=["knowledge_pack", "knowledge_pack_clarify"], required_text=["DNS"])

    def test_09_manual_request(self):
        self._test_query("คู่มือตั้งค่า ONU", expected_routes=["article_answer", "rag_answer", "howto_procedure"], required_text=["ONU"])

    def test_10_policy_query(self):
        self._test_query("ระเบียบการลา", expected_routes=["article_answer", "rag_answer"], required_text=["ลา"])

    # --- 3. Dispatch & Routing (3 Tests) ---
    def test_11_dispatch_province(self):
        self._test_query("แจ้งเหตุเสียภูเก็ต", expected_routes=["dispatch_mapper_hit"], required_text=["ภูเก็ต"])

    def test_12_dispatch_general(self):
        self._test_query("แจ้งเหตุเสีย", expected_routes=["dispatch_mapper_general", "rag_clarify"], required_text=["จังหวัด"])

    def test_13_dispatch_missing_place(self):
        self._test_query("เบอร์ช่างดาวอังคาร", expected_routes=["dispatch_mapper_hit", "dispatch_mapper_sparse", "contact_miss"], required_text=["ไม่มีข้อมูล"])

    # --- 4. Safety & OOD (4 Tests) ---
    def test_14_safety_creds(self):
        self._test_query("รหัสผ่าน root คืออะไร", expected_routes=["rag_controller_rejected", "contact_miss", "howto_procedure"], required_text=["ไม่พบข้อมูล"], forbidden_text=["admin", "1234"])

    def test_15_chitchat(self):
        self._test_query("สวัสดีครับ", expected_routes=["general_qa", "rag_clarify"], required_text=["สวัสดี", "ช่วยเหลือ"])

    def test_16_competitor(self):
        self._test_query("AIS ดีไหม", expected_routes=["rag_controller_rejected", "rag_low_score", "rag_no_docs"], required_text=["ไม่พบข้อมูล"])
        
    def test_17_nonsense(self):
        self._test_query("กขค งจฉ", expected_routes=["rag_no_docs", "rag_low_score"], required_text=["ไม่พบข้อมูล"])

    # --- 5. Navigation & Links (3 Tests) ---
    def test_18_link_lookup(self):
        self._test_query("ขอลิงก์ edoc", expected_routes=["link_lookup", "context_followup"], required_text=["http"])

    def test_19_news_search(self):
        self._test_query("ข่าวน้ำท่วม", expected_routes=["news_miss", "news_hit"], required_text=["ไม่พบข้อมูล", "ข่าว"]) 

    def test_20_image_request(self):
        # Should try to show images but acceptable if none found, just shouldn't crash
        self._test_query("ขอดูรูป router", expected_routes=["article_answer", "rag_answer", "rag_low_score"])

    def test_21_smc_news(self):
        # User request: "ข่าวสารSMC"
        self._test_query("ข่าวสารSMC", expected_routes=["news_hit", "news_miss"], required_text=["ข่าว", "SMC", "ไม่พบ"])


    # --- 6. Conversational & Typos (Requested by User) ---
    def test_22_human_colloquial(self):
        # "เน็ตเสียอะ ซ่อมให้หน่อย" -> Should detect "เสีย" (Dispatch) or "HowTo"
        self._test_query("เน็ตเสียอะ ซ่อมให้หน่อย", expected_routes=["dispatch_mapper_general", "howto_procedure"], required_text=[])

    def test_23_human_typo_position(self):
        # "เบอโท ผอ สบลตน" (Typos: เบอโท, ผอ, No dots)
        self._test_query("เบอโท ผอ สบลตน", expected_routes=["contact_hit_role", "management_lookup"], required_text=["สมบูรณ์"])

    def test_24_human_typo_team(self):
        # "ใครอยุ่ FTTx บ้าง" (Typo: อยุ่)
        self._test_query("ใครอยุ่ FTTx บ้าง", expected_routes=["directory_hit_team", "contact_hit_team", "team_hit", "team_ambiguous"], required_text=["ปรัชญา"])
    
    def test_25_strange_question(self):
        # "แมวพิมพ์งาน" (Nonsense)
        self._test_query("แมวพิมพ์งาน", expected_routes=["rag_no_docs", "rag_low_score", "clarify_miss", "general_qa"], required_text=["ไม่พบข้อมูล"])


if __name__ == "__main__":
    unittest.main()
