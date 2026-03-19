# วิธีรันระบบ RAG และเชื่อมกับ Frontend
> สำหรับเครื่อง Linux Ubuntu — ไฟล์ระบบมีครบแล้ว

---

## ส่วนที่ 1 — รันระบบ RAG บน Ubuntu

### ขั้น 1 — เข้าโฟลเดอร์โปรเจกต์
```bash
cd ~/Internal_RAG
```

### ขั้น 2 — ติดตั้ง Python Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_linux.txt
```

### ขั้น 3 — ติดตั้ง Ollama (ครั้งแรกครั้งเดียว)
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
```

### ขั้น 4 — รันระบบ (ต้องรันทั้ง 2 Terminal)

**Terminal ที่ 1** — รัน AI model:
```bash
ollama serve
```

**Terminal ที่ 2** — รัน API Server:
```bash
cd ~/Internal_RAG
source venv/bin/activate
uvicorn src.api_server:app --host 0.0.0.0 --port 8000
```

### ขั้น 5 — ทดสอบว่าระบบพร้อม
```bash
curl http://localhost:8000/health
```
ถ้าได้ `{"status":"healthy"}` = ✅ ระบบพร้อมแล้ว

---

## ส่วนที่ 2 — เชื่อมกับ Frontend

### ขั้น 6 — รู้ IP ของเครื่อง Ubuntu
```bash
hostname -I
```
ตัวอย่าง: `192.168.1.50`

### ขั้น 7 — เปิด Port (ถ้า Frontend อยู่คนละเครื่อง)
```bash
sudo ufw allow 8000/tcp
```

### ขั้น 8 — ทดสอบจากเครื่อง Frontend
```bash
curl http://192.168.1.50:8000/health
```
ได้ `{"status":"healthy"}` = เชื่อมได้แล้ว ✅

### ขั้น 9 — เรียก API จาก Frontend

**URL ที่ใช้:** `POST http://192.168.1.50:8000/query`

**ข้อมูลที่ส่ง:**
```json
{
  "query": "คำถามของผู้ใช้",
  "session_id": "unique-id-ต่อ-user"
}
```

**คำตอบที่ได้กลับ:**
```json
{
  "answer": "คำตอบจากระบบ",
  "route": "ประเภทการตอบ",
  "latency_ms": 45.2
}
```

---

## ตัวอย่างโค้ด Frontend (HTML พร้อมใช้)

บันทึกเป็น `chat.html` เปิดเบราว์เซอร์ได้เลย:

```html
<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <title>NT RAG Chatbot</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; padding: 20px; }
    input { width: 80%; padding: 10px; font-size: 16px; }
    button { padding: 10px 20px; font-size: 16px; cursor: pointer; }
    #answer { margin-top: 20px; padding: 15px; background: #f0f0f0;
              border-radius: 8px; white-space: pre-wrap; line-height: 1.6; }
  </style>
</head>
<body>
  <h2>🤖 ถามระบบ RAG</h2>
  <input id="question" type="text" placeholder="พิมพ์คำถาม เช่น ขอเบอร์ OMC หาดใหญ่">
  <button onclick="sendQuestion()">ถาม</button>
  <div id="answer">คำตอบจะแสดงที่นี่...</div>

  <script>
    // ⚠️ เปลี่ยน IP ตรงนี้เป็น IP เครื่อง Ubuntu ที่รัน RAG
    const RAG_URL = "http://192.168.1.50:8000";

    // สร้าง session ต่อ user ไว้จำบริบทการสนทนา
    const SESSION_ID = "user_" + Math.random().toString(36).slice(2, 10);

    async function sendQuestion() {
      const question = document.getElementById("question").value.trim();
      if (!question) return;
      document.getElementById("answer").innerText = "⏳ กำลังคิด...";

      try {
        const res = await fetch(`${RAG_URL}/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: question, session_id: SESSION_ID })
        });
        const data = await res.json();
        document.getElementById("answer").innerText = data.answer;
      } catch (err) {
        document.getElementById("answer").innerText = "❌ เชื่อมต่อ API ไม่ได้";
      }
    }

    document.getElementById("question")
      .addEventListener("keydown", e => { if (e.key === "Enter") sendQuestion(); });
  </script>
</body>
</html>
```

> แก้แค่บรรทัดนี้บรรทัดเดียว:
> ```js
> const RAG_URL = "http://192.168.1.50:8000";  // ← IP เครื่อง Ubuntu
> ```

---

## สรุปภาพรวม

```
เครื่อง Ubuntu                    เครื่อง Frontend (ใดก็ได้)
─────────────────                  ───────────────────────────
ollama serve          ←  AI model
uvicorn :8000         ←  API       →   chat.html / React / Vue
                                       POST /query → data.answer
```

---

## ถ้าเจอปัญหา

| ปัญหา | วิธีแก้ |
|---|---|
| `curl` ไม่ตอบ | ตรวจสอบว่า uvicorn รันอยู่ |
| ตอบช้าหรือ error | ตรวจสอบว่า `ollama serve` รันอยู่ |
| Frontend เชื่อมไม่ได้ | รัน `sudo ufw allow 8000/tcp` บน Ubuntu |
| ตอบผิดบริบท | ส่ง `session_id` ทุก request ให้ตรงกัน |
