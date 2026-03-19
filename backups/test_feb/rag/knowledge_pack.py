
from typing import List, Dict, Any, Optional
import json
from pathlib import Path
import random

class KnowledgePackManager:
    """
    Manages structured knowledge packs for fast deterministic lookup.
    Phase 23.
    """
    def __init__(self, pack_dir: str = "data/records/knowledge_packs"):
        self.pack_dir = pack_dir
        self.facts: List[Dict[str, Any]] = []
        self.categories: Dict[str, List[Dict[str, Any]]] = {}
        self.load_packs()
        
    def load_packs(self):
        """Load all JSONL packs."""
        path = Path(self.pack_dir)
        if not path.exists():
            print(f"[KnowledgePack] Directory not found: {self.pack_dir}")
            return
            
        count = 0
        for f in path.glob("*.jsonl"):
            try:
                for line in f.read_text(encoding="utf-8").splitlines():
                    if not line.strip(): continue
                    fact = json.loads(line)
                    self.facts.append(fact)
                    
                    cat = fact.get("category", "general")
                    if cat not in self.categories:
                        self.categories[cat] = []
                    self.categories[cat].append(fact)
                    count += 1
            except Exception as e:
                print(f"[KnowledgePack] Error loading {f}: {e}")
                
        print(f"[KnowledgePack] Loaded {count} facts.")
        
    def lookup(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Lookup relevant facts based on query.
        Returns: { "answer": str, "hits": list } or None
        """
        q_lower = query.lower()
        
        # Check for "All" intent (Phase 26.5)
        force_all = any(w in q_lower for w in ["all", "ทั้งหมด", "ทุกรายการ"])
        
        # Determine Category
        target_cats = []
        if any(w in q_lower for w in ["dns", "smtp", "mail", "name server"]):
            target_cats.append("network_config")
        if any(w in q_lower for w in ["bras", "ippgw", "gateway", "router"]):
            target_cats.append("bras_info")
        if any(w in q_lower for w in ["sip", "vpbx", "ipphone", "voip", "proxy"]):
            target_cats.append("voice_config")
        if any(w in q_lower for w in ["noc", "rnoc", "เวร", "operation center"]):
            target_cats.append("contact_internal")
            
        if not target_cats:
            return None
            
        # Filter facts
        hits = []
        known_regions = ["nt1", "nt2", "hyi", "ppn", "bkk", "surat", "phuket", "kk", "cmi", "isp", "region", "ภูมิภาค"]
        
        for cat in target_cats:
            facts = self.categories.get(cat, [])
            for fact in facts:
                score = 0
                val_str = str(fact.get("value", "")).lower()
                key_str = str(fact.get("key", "")).lower()
                src_title = str(fact.get("source_title", "")).lower()
                
                # Boost if query contains known regions that match the fact
                # This fixes "DNS NT1" being treated as generic DNS
                for reg in known_regions:
                    if reg in q_lower and (reg in val_str or reg in key_str or reg in src_title):
                         score += 10 # High boost for explicit scope match
                
                # Category Specific Logic
                if fact["category"] == "bras_info":
                    if "surat" in q_lower and "surat" in str(fact.get("value", "")).lower(): score += 5
                    if "phuket" in q_lower and "phuket" in str(fact.get("value", "")).lower(): score += 5
                    # If query is generic "bras ip", return many? limit 5?
                    if "bras" in q_lower: score += 1
                    
                elif fact["category"] == "network_config":
                    if "smtp" in q_lower and "smtp" in fact["key"]: score += 5
                    if "dns" in q_lower and "dns" in fact["key"]: score += 5
                    
                elif fact["category"] == "voice_config":
                    if "sip" in q_lower and "sip" in fact["key"]: score += 5
                    if "proxy" in q_lower and "proxy" in fact["key"]: score += 5
                    
                elif fact["category"] == "contact_internal":
                    if "noc" in q_lower and "noc" in fact["key"]: score += 5
                    
                if score > 0:
                    hits.append((fact, score))
        
        if not hits:
            return None
            
        # Conflict Resolution & Scope Detection (Phase 24)
        
        if not hits:
            return None
            
        # Conflict Resolution & Scope Detection (Phase 24)
        
        # 0. True Scope Filtering (Phase 26.6)
        # Check if query implies a specific scope
        detected_scope = None
        for reg in known_regions:
            if reg in q_lower:
                # Map to standard Scope Names used in Build
                # "NT1" -> "NT1", "Region" -> "Region"
                if reg in ["nt1", "nt-1", "bkk"]: detected_scope = "NT1"
                elif reg in ["region", "ภูมิภาค", "hyi", "surat", "phuket", "kk", "cmi"]: detected_scope = "Region"
                elif reg in ["isp"]: detected_scope = "ISP"
                break
        
        # If scope detected and NOT force_all, filter hits
        filtered_hits = []
        warning_msg = None
        
        if detected_scope and not force_all:
            # Filter strictly
            filtered_hits = [
                (f, s) for f, s in hits 
                if f.get("scope") == detected_scope
            ]
            
            if not filtered_hits:
                # Fallback
                warning_msg = f"ไม่พบข้อมูลในขอบเขต {detected_scope} จึงแสดงผลรวมทั้งหมดแทน"
                filtered_hits = hits # Restore all
            else:
                hits = filtered_hits # Replace with filtered
        
        # 1. Broad Query Detection
        # If query is short (e.g. "dns", "smtp") and we have MANY divergent hits
        # we should ask for clarification.
        # Skip if force_all is True OR if explicit scope is in query (detected_scope is set)
        is_broad = (len(q_lower.split()) <= 3 and len(hits) > 3) and not force_all and not detected_scope
        
        # Sort by updated_at DESC, then Score DESC, then Confidence DESC
        hits.sort(key=lambda x: (x[1], x[0].get("updated_at", 0), x[0].get("confidence", 1.0)), reverse=True)
        
        # Deduplicate
        seen_values = set()
        unique_hits = []
        for fact, score in hits:
            v_norm = str(fact["value"]).lower().strip()
            if v_norm in seen_values: continue
            seen_values.add(v_norm)
            unique_hits.append(fact)
            
        if not unique_hits:
            return None

        # 2. Scope Clarification Logic
        # If broad and multiple distinct values remain -> Ask Scope
        if is_broad and len(unique_hits) >= 3:
             # Extract potential scopes from BRAS names or Source titles
             scopes = set()
             for h in unique_hits[:10]:
                 # Try to extract scope from Key or Value
                 # E.g. "BRAS_NODE: Surat-BRAS1" -> Scope: Surat
                 val = str(h.get("value", ""))
                 key = str(h.get("key", ""))
                 
                 # Simple Heuristic: First word of Value or Key?
                 # Or check for known region codes: NT1, NT2, HYI, PPN, BKK, SURAT
                 # Let's try to find known region strings in the value/key
                 
                 known_regions = ["NT1", "NT2", "HYI", "PPN", "BKK", "SURAT", "PHUKET", "KK", "CMI"]
                 for region in known_regions:
                     if region.lower() in val.lower() or region.lower() in key.lower():
                         scopes.add(region.upper())
                         
             # Hardcoded fallback for DNS/SMTP if extraction fails but we know they exist
             if ("dns" in q_lower or "smtp" in q_lower) and not scopes:
                 scopes = {"NT1", "ภูมิภาค (Region)", "ISP"}

             if scopes:
                  # Sort scopes
                  sorted_scopes = sorted(list(scopes))
                  options_str = " ".join([f"[{s}]" for s in sorted_scopes])
                  return {
                      "answer": f"ข้อมูลมีหลายรายการ กรุณาเลือกขอบเขต:\n{options_str} หรือพิมพ์ 'ทั้งหมด'",
                      "hits": [],
                      "signal": "CLARIFY_SCOPE",
                      "options": sorted_scopes
                  }
        
                  sorted_scopes = sorted(list(scopes))
                  options_str = " ".join([f"[{s}]" for s in sorted_scopes])
                  return {
                      "answer": f"ข้อมูลมีหลายรายการ กรุณาเลือกขอบเขต:\n{options_str} หรือพิมพ์ 'ทั้งหมด'",
                      "hits": [],
                      "signal": "CLARIFY_SCOPE",
                      "options": sorted_scopes
                  }
        
        # Limit hits for display
        # If force_all, show up to 20, else 5
        limit = 20 if force_all else 5
        display_hits = unique_hits[:limit]
            
        # Format Answer with Provenance (Phase 24)
        header = f"พบข้อมูล {len(display_hits)} รายการ (จากทั้งหมด {len(unique_hits)} Records):"
        if warning_msg:
            header = f"{warning_msg}\n\n{header}"
            
        ans_lines = [header]
        
        sources_map = {} # url -> title
        
        for fact in display_hits:
            key = fact.get("key", "Info").upper()
            val = fact.get("value", "")
            
            # Security Masking (Phase 23/24)
            if fact.get("sensitivity") == "credential":
                 # Mask passwords
                 if "pass" in str(val).lower() or "pwd" in str(val).lower():
                     val = "****** (Hidden)"
            
            line = f"- {key}: {val}"
            ans_lines.append(line)
            
            src = fact.get("source_url")
            if src:
                sources_map[src] = fact.get("source_title", "Source")
        
        # Add Provenance Footer
        if sources_map:
             ans_lines.append("\nแหล่งข้อมูลอ้างอิง:")
             # Show top 3 unique sources
             for i, (url, title) in enumerate(sources_map.items()):
                 if i >= 3: break
                 ans_lines.append(f"{i+1}. {title} ({url})")
                 
        return {
            "answer": "\n".join(ans_lines),
            "hits": display_hits
        }

