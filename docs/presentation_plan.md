# Outline: NT Knowledge Assistant Presentation

เอกสารนี้รวบรวมโครงสร้าง Slide (Storyline) สำหรับนำเสนอผลงาน โดยเน้นจุดเด่นที่พัฒนาเสร็จแล้ว (RAG + Directory + Smart Confirmation)

---

## Slide 1: Title (หน้าปก)
- **Header:** NT Knowledge Assistant (AI Chatbot)
- **Sub-header:** พลิกโฉมการค้นหาข้อมูลองค์กรด้วย Hybrid RAG Intelligence
- **Presenter:** [ชื่อของคุณ]
- **Visual (รูปภาพ):** 
  - Logo องค์กร (NT)
  - รูป Background สไตล์ Tech/Network ที่ดูสะอาดตา

## Slide 2: The Pain Points (ปัญหาเดิมที่เราเจอ)
- **Text:**
  1. **Information Silos:** ข้อมูลกระจายหลายที่ (ไฟล์ Excel, เว็บ SMC, สมุดโทรศัพท์เล่มหนาๆ)
  2. **Strict Keywords:** ต้องจำชื่อไฟล์หรือชื่อคนให้แม่นยำ 100% พิมพ์ผิดนิดเดียวหาไม่เจอ
  3. **No "Best Guess":** ระบบค้นหาเดิมไม่ฉลาดพอที่จะถามกลับเมื่อสงสัย
- **Visual:**
  - ภาพ Collage ของหน้าจอค้นหาแบบเก่าที่ขึ้นว่า "Not Found" หรือภาพคนทำหน้างงกับกองเอกสาร

## Slide 3: Our Solution (ทางออกใหม่)
- **Text:**
  - **"Hybrid Intelligence":** ผสานพลังการค้นหา 2 ระบบในหนึ่งเดียว
    - 📚 **Knowledge Base RAG:** ค้นหาคู่มือ/บทความ (Unstructured Data)
    - 👥 **Smart Directory:** ค้นหาข้อมูลบุคคล/หน่วยงาน (Structured Data)
  - **Natural Language:** พิมพ์ภาษาไทยคุยได้เหมือนคุยกับคน
- **Visual:**
  - Diagram ง่ายๆ: [User] <-> [AI Brain (Router)] <-> [Docs DB] / [Directory DB]

## Slide 4: Feature Highlight 1 - Smart Person Lookup (ค้นหาคนสุดแม่น)
- **Text:**
  - ค้นหาได้แม้พิมพ์ชื่อย่อ หรือพิมพ์ไม่ครบ
  - **Auto-Correction:** แก้คำผิดให้ (เช่น "เบอรโทร" -> "เบอร์โทร")
- **Visual:**
  - **Screenshot:** หน้าจอแชทที่ User พิมพ์คำย่อ แล้วระบบตอบถูก

## Slide 5: Feature Highlight 2 - Interactive Confirmation (ฟีเจอร์เด็ด!)
- **Text:**
  - "ระบบที่ไม่เดามั่ว" (Anti-Hallucination)
  - เมื่อเจอคำกำกวม ระบบจะสร้าง **Suggestions** และรอการ **Confirm** จากผู้ใช้
  - รองรับการตอบ "ใช่" / "ไม่ใช่" เพื่อความต่อเนื่องของการสนทนา
- **Visual:**
  - **Screenshot Sequence (สำคัญ):**
    1. User: "ใครคือผจ"
    2. AI: "ไม่พบ... คุณหมายถึง 'ผจ.สบลตน.' ใช่ไหม?"
    3. User: "ใช่"
    4. AI: [แสดงข้อมูลเบอร์โทร/อีเมล]

## Slide 6: Feature Highlight 3 - Knowledge Extraction (ค้นหาคู่มือ)
- **Text:**
  - ดึงข้อมูลจากบทความ SMC / ทะเบียนสินทรัพย์
  - สรุปเนื้อหาให้สั้น กระชับ แต่อ้างอิงแหล่งที่มาเสมอ (Source Link)
- **Visual:**
  - **Screenshot:** ผลลัพธ์การค้นหา "ทะเบียนสินทรัพย์" ที่แสดงรายการอุปกรณ์ + ลิงก์

## Slide 7: Security & Compliance (ความปลอดภัย)
- **Text:**
  - **Sensitive Data Guard:** ระบบรู้ว่าข้อมูลไหนเป็น "ความลับ" (เช่น Password, Credential)
  - ไม่แสดง Plain text ผ่านแชท แต่จะส่ง Link ให้ไปดูในระบบที่มี Permission เท่านั้น
- **Visual:**
  - **Screenshot:** ผลลัพธ์คำถาม "ont password" ที่ขึ้นเตือน ⚠️ Restricted Content

## Slide 8: Business Impact (ประโยชน์ที่ได้รับ)
- **Text:**
  - ⚡ **Faster:** ลดเวลาค้นหาข้อมูลจาก 5 นาที เหลือ 5 วินาที
  - 🎯 **Accurate:** ลดความผิดพลาดจากการเดา หรือข้อมูลไม่อัปเดต
  - 😊 **User Friendly:** ใครๆ ก็ใช้ได้ ไม่ต้องเรียนรู้คำสั่งซับซ้อน
- **Visual:**
  - Icons: รูปนาฬิกา (เวลาลดลง), รูปเป้าหมาย (แม่นยำ), รูปยิ้ม (ใช้ง่าย)

## Slide 9: Future Roadmap & Q/A
- **Text:**
  - ขยายฐานข้อมูล Knowledge Pack
  - เชื่อมต่อระบบ Ticket / Incident Management
- **Visual:**
  - Timeline สั้นๆ แสดงแผนพัฒนาเฟสต่อไป

---
**Tip:** 
สำหรับ Screenshot แนะนำให้แคปจากหน้าจอ `Langflow Chat` หรือ `Web UI` ที่เราเพิ่งเทสผ่าน เพื่อให้เห็นความ Real-time และความสำเร็จล่าสุดครับ
