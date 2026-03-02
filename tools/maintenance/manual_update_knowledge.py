import requests
from bs4 import BeautifulSoup
import time
import re
from typing import Set
from urllib.parse import urljoin, unquote

# --- CONFIGURATION (REAL) ---
# URL ของหน้า "คลังความรู้" จากระบบจริง
TARGET_URL = "http://10.192.133.33/smc/index.php?option=com_content&view=category&id=43&Itemid=81"

# Folder ที่เก็บข้อมูล (จำลอง)
DB_PATH = "./data/processed"

def get_links_from_menu(url: str) -> Set[str]:
    """
    ดึงลิงก์บทความทั้งหมดจากหน้าเมนูหลัก (Joomla Category View)
    """
    print(f"🔍 Crawling menu: {url}...")
    headers = {
        "User-Agent": "rag-web-crawler/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = response.apparent_encoding # แก้ปัญหาภาษาไทยต่างด้าว
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = set()
        
        # Joomla Table Category View
        # ปกติลิงก์บทความจะอยู่ใน <td class="list-title"> <a href="...">
        # หรือ <a href="/smc/index.php?option=com_content&view=article...">
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # กรองเฉพาะลิงก์ที่เป็นบทความ (view=article)
            if "view=article" in href or "id=" in href:
                full_url = urljoin(url, href)
                
                # กรองลิงก์ขยะ (Print/Email)
                if "print=1" in full_url or "format=pdf" in full_url or "mailto:" in full_url:
                    continue
                    
                links.add(full_url)
        
        print(f"✅ Found {len(links)} article links.")
        return links
        
    except Exception as e:
        print(f"❌ Error crawling menu: {e}")
        return set()

def process_new_article(url: str):
    """
    ประมวลผลบทความใหม่
    """
    print(f"   ⬇️ Processing: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ดึงหัวข้อ (Joomla Title)
        title_tag = soup.find('h2', class_='contentheading') or soup.find('td', class_='contentheading')
        title = title_tag.get_text(strip=True) if title_tag else soup.title.string.strip()
        
        # ดึงเนื้อหา (Joomla Content is usually in <div class="article-content"> or <table>)
        # ปรับ Selector ตามโครงสร้างเว็บจริง
        content_div = soup.find('div', class_='article-content') or soup.find('table', class_='contentpaneopen')
        
        if content_div:
            text = content_div.get_text(separator="\n", strip=True)
            # ลบ Noise ทั่วไป
            text = re.sub(r'\n+', '\n', text)
            print(f"      📄 Fetched: '{title}' ({len(text)} chars)")
            
            # --- (จำลอง) Save to DB ---
            # ตรงนี้คือจุดที่เรียก RAG Pipeline จริงๆ
            # from src.ingest.processor import process_text
            # process_text(text, metadata={"url": url, "title": title})
            
            print(f"      ✅ Saved to Knowledge Base")
        else:
            print(f"      ⚠️ No content found (Login required?)")

    except Exception as e:
        print(f"      ❌ Failed: {e}")

def manual_update():
    print("🚀 Starting Knowledge Update (Target: 10.192.133.33)...")
    print("="*60)
    
    # 1. Get Links
    current_links = get_links_from_menu(TARGET_URL)
    if not current_links:
        print("❌ Could not fetch links. Check VPN/Intranet connection.")
        return

    # 2. Mock Existing Links (ของจริงต้อง Load จาก DB)
    existing_links = set() 
    
    # 3. Find New
    new_links = current_links - existing_links
    
    print(f"📊 Found {len(new_links)} new articles to process.")
    
    # 4. Process (limit 5 for testing)
    for i, link in enumerate(list(new_links)[:5], 1):
        print(f"\n[{i}/5] Crawling...")
        process_new_article(link)
        time.sleep(0.5)

    print("\n✅ Simulated Update Complete!")

if __name__ == "__main__":
    manual_update()
