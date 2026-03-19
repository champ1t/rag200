
import sys
import json
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.ingest.process_one import process_raw_html_file

def test_reprocess():
    raw_path = "data/raw/10.192.133.33_smc_index.php_option_com_content_view_article_id_645_sbc-ip_catid_43_2011-11-14-08-37-12_Itemid_81.html"
    out_dir = "data/processed"
    url = "http://10.192.133.33/smc/index.php?option=com_content&view=article&id=645:sbc-ip&catid=43:2011-11-14-08-37-12&Itemid=81"
    
    print(f"Reprocessing {raw_path}...")
    out_file, _ = process_raw_html_file(raw_path, out_dir, url)
    print(f"Output: {out_file}")
    
    # Verify Content
    data = json.loads(Path(out_file).read_text())
    text = data["text"]
    
    print("-" * 40)
    print(text[:500])
    print("-" * 40)
    
    # Check for Noise
    noise_markers = ["Today |", "Visitors Counter", "We have:", "Joomla 1.5 Templates"]
    found_noise = [m for m in noise_markers if m in text]
    
    if found_noise:
        print(f"FAILED: Found noise markers: {found_noise}")
    else:
        print("PASSED: No sidebar noise found.")
        
    # Check for Content
    if "- hyi sbc" in text:
        print("PASSED: Found content '- hyi sbc'")
    else:
        print("FAILED: Main content missing")

if __name__ == "__main__":
    test_reprocess()
