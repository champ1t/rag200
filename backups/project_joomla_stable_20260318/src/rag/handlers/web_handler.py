from typing import Dict, Any, List
import time
from src.rag.ollama_client import ollama_generate

WEB_SYSTEM_PROMPT = """
คุณคือ AI ผู้ช่วยสำหรับ NT (โทรคมนาคมแห่งชาติ)
หน้าที่ของคุณคือตอบคำถามทั่วไปทางเทคนิค หรือข่าวสาร โดยใช้ข้อมูลจากการค้นหา (Web Search)

กฎเหล็ก (Strict Rules):
1. **ต้องตอบเป็นภาษาไทยเท่านั้น** (Thai Language ONLY)
   - ห้ามตอบเป็นภาษาอังกฤษ ยกเว้นทับศัพท์ทางเทคนิคที่จำเป็น
2. อ้างอิงเอกสารทางการ (Official Docs), มาตรฐาน (RFC, IEEE) หรือคู่มือ Vendor (Cisco, Huawei) เป็นหลัก
3. ถ้าเป็น News/Update ให้ถือว่าปีปัจจุบันคือ 2025/2026
4. การอ้างอิงแหล่งที่มา:
   - ต้องระบุ [ชื่อเว็บ/แหล่งที่มา] หลังข้อเท็จจริง
   - เช่น "อ้างอิงจากคู่มือ Cisco..."
5. ถ้าไม่แน่ใจ หรือไม่พบข้อมูล ให้ตอบว่า "ไม่พบข้อมูลอ้างอิงที่น่าเชื่อถือ"
6. ห้ามมโนคำสั่ง (Command) หรือขั้นตอนการตั้งค่าเอง

รูปแบบการตอบ (Markdown):
1. สรุปคำตอบให้กระชับ
2. แบ่งหัวข้อชัดเจน
3. ใช้ Bullet points เพื่อให้อ่านง่าย
"""

class WebHandler:
    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_cfg = llm_config
        
    def handle(self, query: str) -> Dict[str, Any]:
        t_start = time.time()
        
        # 1. Search Web (DuckDuckGo)
        search_results = self._search_duckduckgo(query)
        
        # 2. Fail-Closed Policy (User Request)
        if not search_results:
            print("[WebHandler] No results or Error -> FAIL CLOSED (Safe Mode)")
            return {
                "answer": (
                    "**ไม่สามารถค้นหาเว็บได้ในขณะนี้ (Rate limit/Network error)**\n"
                    "ระบบไม่สามารถตอบจากแหล่งภายนอกได้อย่างปลอดภัย\n\n"
                    "📌 **คำแนะนำ**:\n"
                    "1. ลองพิมพ์คำค้นหาให้ชัดเจนขึ้น (เช่นระบุชื่อรุ่น/ยี่ห้อ)\n"
                    "2. ลองค้นหาด้วยคำที่เกี่ยวข้องใน **ระบบเอกสารภายใน (SMC)** แทน"
                ),
                "route": "web_error",
                "latencies": {"web_search": (time.time() - t_start) * 1000}
            }
            
        # 3. Construct Prompt
        context_str = "Search Results:\n"
        sources = []
        for i, res in enumerate(search_results, 1):
            context_str += f"[{i}] {res['title']}\n    Source: {res['href']}\n    Snippet: {res['body']}\n\n"
            sources.append(res['href'])

        prompt = f"""{WEB_SYSTEM_PROMPT}
 
Context from Web Search:
{context_str}
 
User Question: {query}
 
Answer:"""
        
        # 4. Generate Answer
        response = ollama_generate(
            base_url=self.llm_cfg.get("base_url", "http://localhost:11434"),
            model=self.llm_cfg.get("model", "llama3.2:3b"),
            prompt=prompt,
            temperature=0.3, # Low temp for factual
            num_ctx=4096
        )
        
        latency = (time.time() - t_start) * 1000
        
        response_text = response.strip()
        
        # Force Append Sources (User Request: "At least include Source")
        if sources:
            response_text += "\n\nแหล่งที่มา:"
            for src in sources:
                response_text += f"\n🔗 {src}"

        return {
            "answer": response_text,
            "route": "web_knowledge",
            "latencies": {"web_llm": latency},
            "sources": sources
        }

    def _search_duckduckgo(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """
        Search using DuckDuckGo via duckduckgo_search package.
        """
        try:
            from duckduckgo_search import DDGS
            results = []
            print(f"[WebHandler] Searching DDG for: {query}")
            with DDGS() as ddgs:
                # ddgs.text returns an iterator
                # backend='html' is often more robust against rate limits than 'api' or 'lite'
                ddg_gen = ddgs.text(query, region='th-th', safesearch='moderate', max_results=max_results, backend='html')
                for r in ddg_gen:
                    results.append(r)
            
            print(f"[WebHandler] Found {len(results)} results")
            return results
        except Exception as e:
            print(f"[WebHandler] Search Error: {e}")
            return []
