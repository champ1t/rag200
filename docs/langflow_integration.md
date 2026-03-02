# Langflow Integration Guide

## การเชื่อมต่อ RAG System กับ Langflow

### Overview
Langflow เป็น low-code tool สำหรับสร้าง LLM applications ด้วย visual interface
คู่มือนี้จะแสดงวิธีเชื่อม RAG system ของเราเข้ากับ Langflow

---

## วิธีที่ 1: ใช้ API Endpoint (แนะนำ)

### ขั้นตอนที่ 1: รัน RAG API Server

**บนเครื่อง production:**

```bash
cd /opt/rag_web  # หรือ C:\rag_web
source venv/bin/activate  # Windows: venv\Scripts\activate

# ติดตั้ง dependencies เพิ่ม (ครั้งแรกเท่านั้น)
pip install fastapi uvicorn

# รัน API server
uvicorn src.api_server:app --host 0.0.0.0 --port 8000
```

**ทดสอบ API:**
```bash
# Health check
curl http://localhost:8000/health

# Query test
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "รายชื่อทีมทั้งหมด"}'
```

---

### ขั้นตอนที่ 2: เพิ่ม API Call ใน Langflow

#### 2.1 เปิด Langflow
```bash
# ติดตั้ง Langflow (ถ้ายังไม่มี)
pip install langflow

# รัน Langflow
langflow run
```

เปิดเบราว์เซอร์: `http://localhost:7860`

#### 2.2 สร้าง Flow ใหม่

1. **New Flow** → เลือก "Blank"
2. ลาก Component เหล่านี้:

**Components:**
```
[User Input] → [API Request] → [Text Output]
```

#### 2.3 ตั้งค่า API Request Component

**URL:**
```
http://localhost:8000/query
```

**Method:** `POST`

**Headers:**
```json
{
  "Content-Type": "application/json"
}
```

**Body (Template):**
```json
{
  "query": "{input_value}",
  "bypass_cache": false
}
```

**Response Path:** `answer`

---

## วิธีที่ 2: Custom Component (Advanced)

### สร้าง Custom Langflow Component

สร้างไฟล์ `langflow_rag_component.py`:

```python
from langflow import CustomComponent
from langflow.field_typing import Text
import requests
from typing import Optional


class RAGSystemComponent(CustomComponent):
    display_name = "RAG System"
    description = "Internal organizational RAG system"
    
    def build_config(self):
        return {
            "api_url": {
                "display_name": "API URL",
                "info": "RAG API endpoint",
                "value": "http://localhost:8000/query"
            },
            "query": {
                "display_name": "Query",
                "info": "User question",
            },
            "bypass_cache": {
                "display_name": "Bypass Cache",
                "info": "Skip cache for this query",
                "value": False
            }
        }
    
    def build(
        self,
        api_url: str,
        query: str,
        bypass_cache: bool = False
    ) -> Text:
        """Call RAG API and return answer"""
        
        response = requests.post(
            api_url,
            json={
                "query": query,
                "bypass_cache": bypass_cache
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "No answer")
            route = data.get("route", "unknown")
            
            # Return formatted response
            return f"[Route: {route}]\n\n{answer}"
        else:
            return f"Error: {response.status_code}"
```

**การใช้งาน:**
1. บันทึก `langflow_rag_component.py` ในโฟลเดอร์ Langflow components
2. Restart Langflow
3. Component จะปรากฏใน sidebar

---

## วิธีที่ 3: Direct Integration (No API)

### สร้าง Python Component ที่เรียกใช้โดยตรง

```python
from langflow import CustomComponent
from langflow.field_typing import Text
import yaml
import sys
sys.path.append("/opt/rag_web")  # Path to your RAG system

from src.chat_engine import ChatEngine


class DirectRAGComponent(CustomComponent):
    display_name = "Direct RAG"
    description = "Direct RAG system integration"
    
    def __init__(self):
        super().__init__()
        # Load engine once
        if not hasattr(self.__class__, '_engine'):
            with open("/opt/rag_web/configs/config.yaml") as f:
                cfg = yaml.safe_load(f)
            self.__class__._engine = ChatEngine(cfg)
    
    def build_config(self):
        return {
            "query": {
                "display_name": "Query",
                "info": "User question"
            }
        }
    
    def build(self, query: str) -> Text:
        """Process query through RAG engine"""
        result = self._engine.process(query)
        return result.get("answer", "No answer")
```

**⚠️ หมายเหตุ:** วิธีนี้ต้อง Langflow รันบนเครื่องเดียวกับ RAG system

---

## Architecture Diagram

```
┌─────────────┐
│   Langflow  │
│   (UI)      │
└──────┬──────┘
       │ HTTP Request
       ↓
┌─────────────────┐
│  RAG API Server │ :8000
│  (FastAPI)      │
└──────┬──────────┘
       │
       ↓
┌────────────────────┐
│  ChatEngine        │
│  - Router          │
│  - Handlers        │
│  - Vector Search   │
└────────────────────┘
       │
       ↓
┌────────────────────┐
│  Data Sources      │
│  - BM25 Index      │
│  - Vector Store    │
│  - Records         │
└────────────────────┘
```

---

## Example Flow Scenarios

### Scenario 1: Simple Q&A

```
[Text Input] → [RAG API] → [Text Output]
```

**Langflow Configuration:**
- Input: "รายชื่อทีมทั้งหมด"
- API: POST http://localhost:8000/query
- Output: Display answer

---

### Scenario 2: With Context Memory

```
[Chat Input] → [RAG API] → [Memory] → [Chat Output]
```

**Features:**
- Maintains conversation history
- RAG provides factual answers
- Memory stores context

---

### Scenario 3: Hybrid RAG + LLM

```
[User Input] → [RAG API] → [LLM (GPT-4)] → [Output]
                    ↓
              [Pass context]
```

**Workflow:**
1. RAG retrieves relevant info
2. Pass to LLM for summarization
3. LLM generates natural response

**Prompt Template:**
```
Based on this information from our database:

{rag_answer}

Answer the user's question naturally:
{user_query}
```

---

## Production Deployment

### 1. Run API as systemd service

Create `/etc/systemd/system/rag-api.service`:

```ini
[Unit]
Description=RAG API Server
After=network.target

[Service]
Type=simple
User=raguser
WorkingDirectory=/opt/rag_web
Environment="PATH=/opt/rag_web/venv/bin"
ExecStart=/opt/rag_web/venv/bin/uvicorn src.api_server:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable rag-api
sudo systemctl start rag-api
sudo systemctl status rag-api
```

---

### 2. Use Nginx reverse proxy

```nginx
server {
    listen 80;
    server_name rag.company.local;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

### 3. Langflow Configuration

In Langflow API Request component:
- **URL**: `http://rag.company.local/query`
- **Timeout**: 30 seconds (for complex queries)

---

## Testing

### Manual Test

```bash
# Start API
uvicorn src.api_server:app --reload

# Test in another terminal
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "สมาชิกงาน HelpDesk",
    "bypass_cache": false
  }' | jq .
```

**Expected Response:**
```json
{
  "answer": "ทีม: HelpDesk (X คน)\n- ชื่อ 1\n- ชื่อ 2...",
  "route": "team_hit",
  "latency_ms": 123.45,
  "sources": null,
  "metadata": {...}
}
```

---

### Automated Test

Create `test_api.py`:

```python
import requests

API_URL = "http://localhost:8000"

def test_health():
    r = requests.get(f"{API_URL}/health")
    assert r.status_code == 200
    print("✓ Health check passed")

def test_query():
    r = requests.post(
        f"{API_URL}/query",
        json={"query": "รายชื่อทีมทั้งหมด"}
    )
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    print(f"✓ Query test passed: {data['route']}")

if __name__ == "__main__":
    test_health()
    test_query()
    print("\n✓ All tests passed!")
```

Run: `python test_api.py`

---

## Monitoring

### Logs

```bash
# Check API logs
tail -f logs/api.log

# Check request metrics
grep "POST /query" logs/api.log | wc -l
```

### Performance

```bash
# Average latency
grep "latency_ms" logs/api.log | \
  awk '{sum+=$NF; count++} END {print sum/count}'
```

---

## Troubleshooting

### Issue 1: API Won't Start

**Error:** `Address already in use`

**Solution:**
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn src.api_server:app --port 8001
```

---

### Issue 2: Langflow Can't Connect

**Error:** `Connection refused`

**Check:**
1. API is running: `curl http://localhost:8000/health`
2. Firewall allows port 8000
3. Use correct IP (not localhost if different machines)

---

### Issue 3: Slow Response

**Cause:** Large data retrieval

**Solution:**
- Enable caching in RAG
- Increase Langflow timeout
- Optimize vector search

---

## Security Considerations

### 1. Authentication

Add API key authentication:

```python
from fastapi import Header, HTTPException

API_KEY = "your-secret-key"

@app.post("/query")
async def process_query(
    request: QueryRequest,
    x_api_key: str = Header(None)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    # ... rest of code
```

### 2. Rate Limiting

```bash
pip install slowapi

# In api_server.py
from slowapi import Limiter
limiter = Limiter(key_func=lambda: "global")

@app.post("/query")
@limiter.limit("10/minute")
async def process_query(...):
    ...
```

---

## Next Steps

1. **Deploy API** to production server
2. **Install Langflow** on same/different server
3. **Create flows** for common use cases
4. **Monitor** performance and errors
5. **Scale** if needed (load balancer, replicas)

---

## Support

- API Docs: http://localhost:8000/docs (Swagger UI)
- Langflow Docs: https://docs.langflow.org/
- Internal Wiki: [Add your wiki link]
