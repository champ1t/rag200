
import yaml
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure src is in path
sys.path.append(os.getcwd())

# Define Mock Hit Class (mimics SearchResult)
class MockHit:
    def __init__(self, id, score, text, metadata):
        self.id = id
        self.score = score
        self.page_content = text # LangChain style
        self.metadata = metadata or {}
        
    def __repr__(self):
        return f"MockHit(id={self.id}, score={self.score})"

# Define Mock Vector Store
class MockVectorStore:
    def __init__(self, *args, **kwargs):
        self.collection = MagicMock()
        self.collection.count.return_value = 100
        
    def hybrid_query(self, query, top_k=3, filter=None):
        query_lower = query.lower()
        
        # 1. SMC / Contact Intention
        if any(x in query_lower for x in ["snc", "sbc", "smc", "contact", "เบอร์", "ติดต่อ", "nms", "hr"]):
            return [MockHit(
                id="chunk_1",
                score=0.88,
                text="เบอร์โทรศัพท์ศูนย์ปฏิบัติการ SMC (SMC Contact): 02-123-4567. ผู้ดูแลระบบ NMS: คุณสมชาย (A&I) โทร 081-111-2222. HR Contact: 02-999-8888.",
                metadata={"source": "contact_list", "url": "http://10.192.133.33/smc/contact"}
            )]
             
        # 2. Config / HowTo
        # LONG CONTENT to test "Read More" and Truncation
        if any(x in query_lower for x in ["config", "vlan", "cisco", "huawei", "confgi", "login", "error", "vpn", "ทำยังไง", "เน็ตหลุด"]):
            long_text = "วิธีการ Config VLAN Cisco (Updated 2024):\n" + \
                        ("This is a very long line of text to force the summarizer to consider truncating or summarizing specifically. " * 10) + "\n" + \
                        "Step 1: Enter global configuration mode (conf t).\n" + \
                        "Step 2: Enter vlan <id> command.\n" + \
                        "Step 3: Name the vlan properly.\n" + \
                        "Step 4: Exit and save (write memory).\n" + \
                        "NAVIGATION MENU: Home | About | Contact Us | Privacy Policy\n" + \
                        "FOOTER: Copyright 2024 NT PLC.\n" + \
                        ("Repeat content to ensure length exceeds limits. " * 5)
            
            return [MockHit(
                id="chunk_2",
                score=0.85,
                text=long_text,
                metadata={"source": "howto_wiki", "url": "http://10.192.133.33/wiki/config"}
            )]
            
        # 3. Web Knowledge (Low Score)
        if any(x in query_lower for x in ["flood", "น้ำท่วม", "ข่าว"]):
             return [MockHit(
                id="chunk_3",
                score=0.35, # Low score to trigger Web Knowledge
                text="ข่าวน้ำท่วมเก่าปี 2020...",
                metadata={"source": "old_news"}
            )]

        # 4. Unknown / General
        if "wdm" in query_lower:
             return [MockHit(
                id="chunk_4",
                score=0.75,
                text="WDM (Wavelength Division Multiplexing) คือเทคโนโลยีการส่งข้อมูลแสง...",
                metadata={"source": "tech_dict"}
            )]

        return []

# GLOBALLY PATCH SentenceTransformer & Chromadb
mock_st_module = MagicMock()
sys.modules["sentence_transformers"] = mock_st_module
sys.modules["sentence_transformers.SentenceTransformer"] = MagicMock()

sys.modules["chromadb"] = MagicMock()
sys.modules["chromadb.utils"] = MagicMock()
sys.modules["chromadb.utils.embedding_functions"] = MagicMock()

# Mock Requests Response
class MockResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.content = text.encode('utf-8')
        self.status_code = status_code
        self.headers = {'Content-Type': 'text/html'}
    
    def raise_for_status(self):
        pass

def mock_requests_get(url, *args, **kwargs):
    print(f"[MOCK FETCH] Fetching: {url}")
    # Return mock HTML based on URL
    if "config" in url:
        return MockResponse("""
            <html>
                <body>
                    <nav>Menu: Home | About</nav>
                    <h1>Methods Config VLAN Cisco</h1>
                    <div class='content'>
                        <p>This is the detailed content fetched from URL.</p>
                        <p>Step 1: Enter global configuration mode (conf t).</p>
                        <p>Step 2: Enter vlan id command.</p>
                        <p>Detailed steps omitted for brevity but simulated length.</p>
                    </div>
                    <footer>Copyright 2024</footer>
                </body>
            </html>
        """)
    return MockResponse("<html><body>Generic Content</body></html>")

with patch("src.chat_engine.build_vectorstore") as mock_build, \
     patch("src.chat_engine.SemanticCache") as mock_cache_cls, \
     patch("requests.get", side_effect=mock_requests_get):
    
    # 1. Setup Mock Vector Store
    mock_vs = MockVectorStore()
    mock_build.return_value = mock_vs
    
    # 2. Setup Mock Cache
    mock_cache_inst = MagicMock()
    mock_cache_inst.check.return_value = None 
    mock_cache_cls.return_value = mock_cache_inst

    # 3. Import ChatEngine (patches active)
    from src.core.chat_engine import ChatEngine
    
    def load_config(path: str):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def run_tests():
        config_path = "configs/config.yaml"
        if not os.path.exists(config_path):
            print(f"Config file not found: {config_path}")
            return

        print("Initializing ChatEngine (Mocked VectorStore & ST & Requests)...")
        cfg = load_config(config_path)
        
        try:
            engine = ChatEngine(cfg)
        except Exception as e:
            print(f"Init Error: {e}")
            return
            
        engine.cache = mock_cache_inst # Enforce
        
        test_queries = [
            # 1. Typo + HowTo -> Should trigger Fetch -> Summarize
            "confgi vlan cisco ให้หน่อย",      
            
            # 2. Typo + Contact -> Strict Contact (No Fetch)
            "snc เบอร์อะไร",                   
            
            # 3. Web Knowledge -> Should fallback to Web (Mock Fetch?)
            "อยากรู้ข่าวน้ำท่วมเชียงรายล่าสุด" 
        ]
        
        results = []
        
        print(f"\n{'='*20} Running Tests (Full Mock) {'='*20}\n")
        
        for i, q in enumerate(test_queries, 1):
            print(f"\n[{i}] Asking: {q}")
            try:
                resp = engine.process(q)
                route = resp.get("route", "unknown")
                answer = resp.get("answer", "")
                
                # Check for Read More link
                if "Read full article" in answer or "wiki/config" in answer:
                    has_read_more = "YES"
                else:
                    has_read_more = "NO"
                
                summary = answer.replace('\n', ' ').replace('**', '').strip()
                if len(summary) > 100:
                    summary = summary[:97] + "..."
                
                results.append({
                    "id": i,
                    "query": q,
                    "route": route,
                    "answer_summary": summary,
                    "read_more": has_read_more
                })
                print(f"   -> Route: {route}")
                print(f"   -> Ans: {summary}")
                print(f"   -> Read More: {has_read_more}")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"   -> ERROR: {e}\n")
                results.append({"id": i, "query": q, "route": "ERROR", "answer_summary": str(e), "read_more": "ERR"})

        # Print Final Summary Table
        print(f"\n{'='*20} Test Results Summary {'='*20}")
        print(f"{'ID':<4} | {'Query':<30} | {'Intent':<15} | {'Read More?':<10} | {'Answer Snippet'}")
        print("-" * 130)
        for r in results:
            q_disp = (r['query'][:27] + '..') if len(r['query']) > 27 else r['query']
            print(f"{r['id']:<4} | {q_disp:<30} | {r['route']:<15} | {r['read_more']:<10} | {r['answer_summary']}")

    if __name__ == "__main__":
        run_tests()
