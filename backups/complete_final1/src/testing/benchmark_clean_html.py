
import time
import timeit
from typing import List
from bs4 import BeautifulSoup
import lxml.html
from src.ingest.clean import clean_html_to_text

# Target files for benchmark
FILES = [
    "data/raw/10.192.133.33_smc_index.php_option_com_content_view_article_id_651_basic-command-olt-zte-c300_catid_43_2011-11-14-08-37-12_Itemid_81.html", # 65KB
    "data/raw/10.192.133.33_smc_index.php_option_com_content_view_article_id_649_-oltonu_catid_49_-smc_Itemid_84.html" # 581KB (Huge)
]

def load_content(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return ""

def clean_pure_lxml(html_content: str):
    if not html_content: return ""
    try:
        tree = lxml.html.fromstring(html_content)
    except Exception:
        return ""
        
    # Selectors
    body_selectors = [
        "div[itemprop='articleBody']",
        "div.com-content-article__body",
        "div.articleBody", 
        "div[itemprop='text']",
        "div.main-both",
        "article", 
        "main"
    ]
    
    target = None
    for sel in body_selectors:
        found = tree.cssselect(sel)
        if found:
            # Minimal check > 50 chars
            if len(found[0].text_content()) > 50:
                target = found[0]
                break
                
    if target is not None:
        root = target
    else:
        root = tree
        
    # Remove tags
    # lxml iterate and drop
    # This is where lxml differs from BS4 decompos.
    # We can use cleaner? Or manual drop.
    # Manual drop:
    for tag in root.xpath('.//script|.//style|.//meta|.//noscript|.//iframe|.//header|.//footer|.//nav'):
        tag.drop_tree()
        
    return root.text_content()

def benchmark():
    print("=== HTML Cleaning Benchmark ===")
    
    for fpath in FILES:
        content = load_content(fpath)
        if not content: continue
        
        print(f"\nFile: {fpath} (Size: {len(content)/1024:.2f} KB)")
        
        # Test 1: Current BS4
        start = time.time()
        for _ in range(20):
            clean_html_to_text(content)
        bs4_time = (time.time() - start) / 20
        print(f"BS4 (Current): {bs4_time*1000:.2f} ms")
        
        # Test 2: Pure LXML (Approx)
        start = time.time()
        for _ in range(20):
            clean_pure_lxml(content)
        lxml_time = (time.time() - start) / 20
        print(f"Pure LXML:     {lxml_time*1000:.2f} ms")
        
        ratio = bs4_time / lxml_time if lxml_time > 0 else 0
        print(f"Speedup:       {ratio:.2f}x")

if __name__ == "__main__":
    benchmark()
