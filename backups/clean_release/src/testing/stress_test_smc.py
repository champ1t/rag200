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

class SMCStressTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n[SMCStressTest] Initializing ChatEngine...")
        cls.config = load_config("configs/config.yaml")
        cls.config["chat"]["mode"] = "production"
        # We allow cache to test real-world behavior, or disable if strict RAG test needed
        # Let's keep cache disabled to stress test retrieval
        if "cache" not in cls.config: cls.config["cache"] = {}
        cls.config["cache"]["enabled"] = False
        
        cls.engine = ChatEngine(cls.config)

    def _test_query(self, query, expected_routes=None, required_text=None, forbidden_text=None):
        print(f"\nQ: {query}")
        start = time.time()
        
        self.engine.reset_context()
        resp = self.engine.process(query)
        duration = time.time() - start
        
        ans = resp["answer"]
        route = resp.get("route", "unknown")
        
        print(f"A: {ans[:150]}... (Route: {route}, Time: {duration:.2f}s)")
        
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
            # self.fail("; ".join(errors)) # Don't fail hard, just report
            return False
        else:
            print("✅ PASSED")
            return True

    def test_run_50_questions(self):
        failures = 0
        questions = [
            # --- Huawei BRAS / IPPGW ---
            ("Huawei bras ippgw command มีอะไรบ้าง", ["article_answer", "rag_answer", "rag_clarify", "rag"], []), # Clarification is acceptable
            ("ขอไฟล์ config ScriptV5.xlsx", ["article_answer", "rag_answer", "link_lookup"], ["docs.google.com", "ScriptV5"]),
            ("เบอร์โทร Support Huawei BRAS", ["contact_hit_role", "article_answer", "rag_answer", "rag_clarify", "rag"], []), # Clarify or Hit
            ("วิธี clear ip address ลูกค้าใน IP Pool", ["article_answer", "rag_answer", "howto_procedure"], ["recycle", "lock"]),
            ("คำสั่งดู mac address ใน vlan pppoe", ["article_answer", "rag_answer"], ["display access-user", "pevlan"]),
            
            # --- Huawei ADSL ---
            ("วิธี add adsl Huawei", ["article_answer", "rag_answer", "howto_procedure"], ["service-port", "vpi", "vci"]),
            ("คำสั่งแก้ line profile ADSL Huawei", ["article_answer", "rag_answer"], ["activate", "profile-index"]),
            ("เปลี่ยน vlan ที่ port adsl ทำยังไง", ["article_answer", "rag_answer", "howto_procedure"], ["undo service-port"]),
            ("วิธีดูความเร็วใน node ADSL", ["article_answer", "rag_answer"], ["display adsl line-profile"]),
            
            # --- ZTE OLT ---
            ("Template ZTE FTTX v.3 อยู่ที่ไหน", ["link_lookup", "article_answer", "rag_answer"], ["http", "wrapper"]),
            ("คำสั่ง config ZTE OLT C300", ["article_answer", "rag_answer"], ["C300"]),
            ("วิธีดู ONU Event Log", ["link_lookup", "article_answer", "rag_answer"], ["wrapper", "Itemid"]),
            ("ZTE C6xx config ยังไง", ["article_answer", "rag_answer"], ["C6xx"]),
            ("คำสั่ง show บน ZTE C6xx", ["article_answer", "rag_answer"], ["show"]),
            ("ZTE telnet to ONU command", ["article_answer", "rag_answer"], ["telnet"]),
            
            # --- Bridge Mode / Modem ---
            ("วิธีตั้งค่า Bridge Mode Forth GPO-4900WS", ["article_answer", "rag_answer", "howto_procedure"], ["192.168.1.254", "promp"]),
            ("Username ปัจจุบันของ Forth GPO-4900WS", ["article_answer", "rag_answer"], ["admin", "tot"]),
            ("ขอคู่มือ Bridge Mode Forth PDF", ["article_answer", "rag_answer", "link_lookup"], ["pdf"]),
            
            # --- IP Phone / VoIP ---
            ("ขอ Proxy IP Phone", ["link_lookup", "article_answer", "rag_answer"], ["Proxy"]),
            ("วิธี Get IP IPPhone", ["link_lookup", "article_answer", "rag_answer"], ["wrapper"]),
            ("Config ATA Planet VIP-157S", ["article_answer", "rag_answer"], ["Planet"]),
            
            # --- Cisco / Network ---
            ("Convert ASR920 to NCS link", ["link_lookup", "article_answer", "rag_answer"], ["wrapper"]),
            ("Cisco IOS Commands มีอะไรบ้าง", ["article_answer", "rag_answer"], ["Cisco"]),
            ("วิธีทำ EtherChannel Cisco", ["article_answer", "rag_answer", "howto_procedure"], ["EtherChannel"]),
            ("คำสั่ง show power บนอุปกรณ์", ["article_answer", "rag_answer"], ["show power"]),
            
            # --- SMC General / Contacts ---
            ("เบอร์ผส.บลตน.", ["contact_hit_role", "position_holder_hit"], ["ผส."]),
            ("ใครเป็น ผจ.สบลตน.", ["position_holder_hit", "directory_hit_role"], ["ผจ."]),
            ("ขอลิงก์หน้าหลัก SMC", ["link_lookup", "article_answer"], ["smc/index.php"]),
            ("ข่าวสาร SMC ล่าสุด", ["news_hit", "news_search"], ["ข่าว"]),
            ("เบอร์ติดต่อ SMC Support", ["contact_hit_team", "contact_hit_role", "article_answer"], ["SMC"]),
            ("SMC Extension Dashboard คือลิงก์ไหน", ["link_lookup", "article_answer"], ["DEV_SERVER_IP"]),
            ("ทางเข้า SMC AI", ["link_lookup", "article_answer"], ["SMC AI"]),
            
            # --- Links & Systems ---
            ("ขอลิงก์ Edocument", ["link_lookup"], ["ntedoc"]),
            ("เข้าเว็บ HR ได้ที่ไหน", ["link_lookup"], ["webhr"]),
            ("ลิงก์ NT Academy", ["link_lookup"], ["lms.COMPANY_NAME"]),
            ("เว็บกองทุนสำรองเลี้ยงชีพ", ["link_lookup"], ["pvd"]),
            ("ระบบสุราษฎร์ NMS", ["link_lookup", "article_answer"], ["totsni"]),
            ("ระบบนราธิวาส NMS", ["link_lookup", "article_answer"], ["INTERNAL_NMS_IP"]),
            
            # --- Knowledge & Procedures (General) ---
            ("DNS ของ NT คืออะไร", ["knowledge_pack", "rag_answer"], ["DNS"]),
            ("วิธีตั้งค่า VLAN Planning", ["article_answer", "howto_procedure"], ["VLAN"]),
            ("BRAS IP Address คืออะไร", ["article_answer", "rag_answer"], ["BRAS"]),
            ("วิธีจูนเน็ตให้ลูกค้า", ["howto_procedure", "rag_answer"], []), # Generic
            
            # --- Edge Cases ---
            ("รหัสผ่าน root password", ["rag_controller_rejected", "contact_miss"], ["ไม่พบข้อมูล"]),
            ("ใครขายก๋วยเตี๋ยว", ["rag_no_docs", "rag_low_score", "general_qa"], ["ไม่พบข้อมูล"]),
            ("ข่าวดาราเกาหลี", ["news_miss", "rag_no_docs"], ["ไม่พบข้อมูล"]),
            ("แมวร้องยังไง", ["rag_no_docs", "general_qa"], []),
            
            # --- Specific Details ---
            ("IP Pool knl-dhcp-1 ใช้ทำอะไร", ["article_answer", "rag_answer"], ["pool"]),
            ("เบอร์คุณกับตัน SMC", ["contact_hit_person", "article_answer"], ["092-992949"]),
            ("เบอร์คุณก้าน SMC", ["contact_hit_person", "article_answer"], ["084-4689122"]),
            ("เบอร์คุณบอม SMC", ["contact_hit_person", "article_answer"], ["061-7836661"]),
        ]
        
        print(f"\nrunning {len(questions)} questions...\n")
        
        for i, (q, routes, txts) in enumerate(questions):
            print(f"--- Q{i+1} ---")
            if not self._test_query(q, expected_routes=routes, required_text=txts):
                failures += 1
                
        print(f"\n\nTotal Failures: {failures} / {len(questions)}")
        
        if failures > 0:
            self.fail(f"Stress test failed with {failures} errors.")

if __name__ == "__main__":
    unittest.main()
