import time
import random
import datetime

# ==============================================================================
# HONEST SIMULATION SCRIPT
# ==============================================================================
# This script generates presentation logs that strictly reflect the ACTUAL 
# capabilities of the RAG system as defined in src/ and configs/config.yaml.
#
# RULES:
# 1. NO PDF/DOCX support (Config: deny_extensions).
# 2. NO Semantic Chunking (Code: chunker.py uses fixed size).
# 3. NO Reranking (Code: No reranker module found).
# 4. ACTUAL IP/DOMAINS ONLY (Config: 10.192.133.33).
# ==============================================================================

class HonestLogger:
    def __init__(self):
        self.start_time = time.time()
        # Standard ANSI colors for terminal output
        self.BLUE = "\033[94m"
        self.GREEN = "\033[92m"
        self.YELLOW = "\033[93m"
        self.CYAN = "\033[96m" 
        self.RESET = "\033[0m"
        self.DIM = "\033[90m"

    def log(self, level, module, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
        color = self.GREEN if level == "INFO" else self.YELLOW if level == "WARN" else self.RESET
        print(f"{self.DIM}{timestamp}{self.RESET} | {color}{level:<5}{self.RESET} | {self.CYAN}{module:<15}{self.RESET} | {message}")
        time.sleep(random.uniform(0.05, 0.2)) # Realistic jitter

    def section(self, title):
        print(f"\n{self.BLUE}== {title} =={self.RESET}")
        time.sleep(0.5)

logger = HonestLogger()

def run_honest_simulation():
    # ----------------------------------------------------
    # 1. INITIALIZATION (Actual Config)
    # ----------------------------------------------------
    logger.section("SYSTEM INITIALIZATION")
    logger.log("INFO", "main", "Starting RAG Web Crawler (Env: Production)")
    logger.log("INFO", "config", "Loaded config from configs/config.yaml")
    logger.log("INFO", "config", "Domain Policy: Allow [10.192.133.33]")
    logger.log("INFO", "db", "Connected to ChromaDB at 10.0.4.20:8000 (Collection: smc_web)")
    
    # ----------------------------------------------------
    # 2. CRAWLING (Internal IP: 10.192.133.33)
    # ----------------------------------------------------
    logger.section("PHASE 1: WEB CRAWL & DISCOVERY")
    logger.log("INFO", "crawler", "Seed URL: http://10.192.133.33/smc")
    time.sleep(0.5)
    
    # Page 1: Index Page
    logger.log("INFO", "fetch", "GET http://10.192.133.33/smc (200 OK) - 14kb")
    logger.log("INFO", "discover", "Found 12 internal links, 0 external skipped")
    
    # Page 2: Manual (HTML)
    logger.log("INFO", "fetch", "GET http://10.192.133.33/smc/docs/installation (200 OK) - 45kb")
    logger.log("INFO", "process", "Cleaning HTML content (sections: main, removed: nav, footer)")
    logger.log("INFO", "process", "Preserving Table: 'Hardware Requirements'")
    logger.log("INFO", "state", "Hash mismatch (new content detected) -> Processing")

    # Page 3: Troubleshooting (With Images)
    logger.log("INFO", "fetch", "GET http://10.192.133.33/smc/kb/error_codes (200 OK) - 32kb")
    logger.log("INFO", "process", "Extracting images for OCR...")
    logger.log("INFO", "ocr", "Extracted text from 'screen_error_503.png' (12 chars)")
    
    # Page 4: PDF (SKIPPED by Config)
    logger.log("WARN", "crawler", "Skipping denied extension: http://10.192.133.33/smc/manual.pdf")
    
    # ----------------------------------------------------
    # 3. CHUNKING (Fixed-Size Only)
    # ----------------------------------------------------
    logger.section("PHASE 2: TEXT PROCESSING")
    # Emulating chunk/chunker.py logic
    logger.log("INFO", "chunker", "Processing 'Installation Guide' (Content Length: 12,400 chars)")
    logger.log("INFO", "chunker", "Strategy: Fixed-Size (Size=700, Overlap=100)")
    logger.log("INFO", "chunker", "Generated 19 chunks")
    
    logger.log("INFO", "chunker", "Processing 'Error Codes' (Content Length: 8,200 chars)")
    logger.log("INFO", "chunker", "Generated 13 chunks")

    # ----------------------------------------------------
    # 4. EMBEDDING & INDEXING
    # ----------------------------------------------------
    logger.section("PHASE 3: VECTOR INDEXING")
    logger.log("INFO", "embed", "Model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    logger.log("INFO", "chroma", "Upserting 32 vectors to 'smc_web'")
    logger.log("INFO", "state", "Saving crawl state to state.json")
    
    # ----------------------------------------------------
    # 5. SUMMARY
    # ----------------------------------------------------
    print("\n------------------------------------------------")
    print("✅ CRAWL COMPLETE (HONEST MODE)")
    print("   - Duration: 2.1s")
    print("   - Pages Fetched: 3")
    print("   - Pages Skipped: 1 (PDF Policy)")
    print("   - Total Vectors: 32")
    print("------------------------------------------------")

if __name__ == "__main__":
    run_honest_simulation()
