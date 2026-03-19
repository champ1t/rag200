"""
Build Knowledge Packs
Extracts high-value facts from processed articles into structured JSONL packs.
Run this during ingestion or manually.
"""
import json
import re
import os
from pathlib import Path
from typing import List, Dict, Any

# CONFIG
PROCESSED_DIR = "data/processed"
OUTPUT_DIR = "data/records/knowledge_packs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# PATTERNS
PATTERNS = {
    "dns_smtp": {
        "keywords": ["dns", "smtp", "domain name", "outgoing mail", "mail server"],
        "regex": [
            (r'(?:DNS|Name)\s*(?:Server)?.*?(?:[:=]|::)\s*([\d\.]+)', "dns_server"),
            (r'SMTP\s*(?:Server|new)?.*?(?:[:=]|::)\s*([a-zA-Z0-9\.\-]+)', "smtp_server"),
             # Capture standard IP if context suggests DNS
            (r'([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}).*?DNS', "dns_server"),
        ],
        "category": "network_config"
    },
    "bras_ippgw": {
        "keywords": ["bras", "ippgw", "ip-pgw", "gateway", "router"],
        "regex": [
             # Capture Name : IP format commonly found in tables
            (r'([A-Za-z0-9\-\_]+BRAS[A-Za-z0-9\-\_]*).*?([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3})', "bras_node"),
            # Capture Name (IP) format
            (r'([A-Za-z0-9\-\_]+BRAS[A-Za-z0-9\-\_]*)\s*\(([\d\.]+)\)', "bras_node"),
            # Capture simple IP if line has 'BRAS'
            (r'BRAS.*?([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3})', "bras_node_ip"),
        ],
        "category": "bras_info"
    },
    "sip_vpbx": {
        "keywords": ["sip", "vpbx", "ipphone", "ip phone", "voip"],
        "regex": [
            (r'([a-zA-Z0-9\.\-]+\.tot\.co\.th)', "sip_domain"),
            (r'Server\s*IP\s*[:\s]+([\d\.]+)', "sip_ip"),
            (r'SIP\s*(?:Server)?.*?(?:[:=]|::)\s*([\d\.]+)', "sip_ip"),
             # Proxy IP extraction
            (r'Proxy\s*(?:IP)?.*?([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3})', "proxy_ip"),
        ],
        "category": "voice_config"
    },
    "noc_contact": {
        "keywords": ["noc", "rnoc", "network operation center", "เวร", "ติดต่อ"],
        "regex": [
            (r'(NOC\s*[A-Za-z0-9\s]+).*?(0\d{8,9})', "contact_noc"),
            (r'(RNOC\s*[A-Za-z0-9\s]+).*?(0\d{8,9})', "contact_rnoc"),
            (r'(เวร\s*[A-Za-z0-9\s]+).*?(0\d{8,9})', "contact_shift"),
        ],
        "category": "contact_internal"
    }
}

def extract_facts(text: str, context_keywords: List[str], patterns: List[tuple]) -> List[Dict[str, str]]:
    facts = []
    text_lower = text.lower()
    
    # Check if context matches
    if not any(kw in text_lower for kw in context_keywords):
        return []
    
    lines = text.split('\n')
    for line in lines:
        for pat, key_type in patterns:
            matches = re.findall(pat, line, re.IGNORECASE)
            for m in matches:
                val = m
                if isinstance(m, tuple):
                    # For patterns identifying Name + Value, combine or pick value
                    # Heuristic: if tuple has 2 items, usually (Name, Value) or (Context, Value)
                    # Let's verify specific pattern logic
                    if key_type == "bras_node":
                         val = f"{m[0]}: {m[1]}"
                    elif key_type.startswith("contact_"):
                         val = f"{m[0]}: {m[1]}"
                    else:
                        # Default to first capturing group if multiple
                        val = m[0] if m[0] else m[1]
                
                if len(str(val)) > 3:
                    facts.append({
                        "key": key_type,
                        "value": str(val).strip(),
                        "raw": line.strip()
                    })
    return facts


def process_files():
    print(f"Scanning {PROCESSED_DIR}...")
    knowledge = []
    
    processed_files = list(Path(PROCESSED_DIR).glob("*.json"))
    print(f"Found {len(processed_files)} files.")
    
    for fpath in processed_files:
        try:
            data = json.loads(fpath.read_text(encoding='utf-8'))
            content = data.get("content") or data.get("text", "")
            title = data.get("title", "")
            url = data.get("url", "")
            
            # Combine title and content for extraction context
            full_text = f"{title}\n{content}"
            
            # Extract date if possible (processed_at is float timestamp)
            updated_at = data.get("processed_at", 0.0)
            
            file_facts = []
            
            for k_type, config in PATTERNS.items():
                facts = extract_facts(full_text, config["keywords"], config["regex"])
                for f in facts:
                    col = {
                        "type": k_type,
                        "category": config["category"],
                        "key": f["key"],
                        "value": f["value"],
                        "raw_line": f["raw"],
                        "source_title": title,
                        "source_url": url,
                        "updated_at": updated_at,
                        "confidence": 1.0, # Base high confidence for regex hits
                        "sensitivity": "public" # Default
                    }
                    
                    # Detect credentials
                    if "pass" in f["raw"].lower() or "pwd" in f["raw"].lower():
                         col["sensitivity"] = "credential"
                         col["confidence"] = 0.9 # Slightly lower for sensitive info to encourage verification? Or keep 1.0.
                    
                    # Infer Scope (Phase 26.6)
                    col["scope"] = "General" # Default
                    scope_keywords = {
                        "NT1": ["nt1", "nt-1", "bkk", "metropolitan"],
                        "Region": ["region", "ภูมิภาค", "province", "provincial", "hyi", "kk", "cmi", "surat", "phuket"],
                        "ISP": ["isp", "internet", "gateway", "bras"]
                    }
                    
                    # check source_title and raw_line
                    check_text = (title + " " + f["raw"]).lower()
                    for scope_name, kws in scope_keywords.items():
                        if any(kw in check_text for kw in kws):
                            col["scope"] = scope_name
                            break
                            
                    file_facts.append(col)
            
            knowledge.extend(file_facts)
            
        except Exception as e:
            print(f"Error reading {fpath}: {e}")
            
    # Save to JSONL
    out_path = Path(OUTPUT_DIR) / "knowledge_main.jsonl"
    print(f"Saving {len(knowledge)} facts to {out_path}...")
    
    with open(out_path, "w", encoding="utf-8") as f:
        for item in knowledge:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print("Done.")

if __name__ == "__main__":
    process_files()
