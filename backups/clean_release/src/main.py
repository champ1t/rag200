from __future__ import annotations

import argparse
import yaml
import json
import os
import re
import requests
from pathlib import Path

from src.utils.runlog import make_run_id, ensure_run_dir, append_jsonl, now_ts

from src.vectorstore import build_vectorstore
from src.chunk.chunker import make_chunks
from src.ingest.fetch import fetch_url, save_raw_html
from src.ingest.process_one import process_raw_html_file

# ✅ ใช้ import เดียวเพื่อกัน generate.py ซ้ำ






def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--config",
        default="configs/config.yaml",
        help="Path to config file"
    )
    ap.add_argument(
        "command",
        choices=["crawl", "index", "chat", "models", "stats", "records"],
        help="Pipeline step to run"
    )

    args = ap.parse_args()
    cfg = load_config(args.config)

    print(f"[INFO] Project: {cfg['project']['name']}")
    print(f"[INFO] Command: {args.command}")

    # --------------------------------------------------
    # models
    # --------------------------------------------------
    if args.command == "models":
        llm_cfg = cfg.get("llm", {})
        base_url = llm_cfg.get("base_url", "http://localhost:11434").rstrip("/")
        try:
            r = requests.get(f"{base_url}/api/tags", timeout=10)
            r.raise_for_status()
            data = r.json()
            models = data.get("models", []) or []
            if not models:
                print("[MODELS] No models found.")
                return
            print("[MODELS] Available Ollama models:")
            for m in models:
                name = m.get("name")
                size = m.get("size")
                modified = m.get("modified_at")
                print(f"- {name} | size={size} | modified={modified}")
        except Exception as e:
            print(f"[MODELS] Error: {e}")
        return

    # --------------------------------------------------
    # stats
    # --------------------------------------------------
    if args.command == "stats":
        from collections import Counter

        vs = build_vectorstore(cfg)

        processed_dir = Path("data/processed")
        docs = []
        for jf in sorted(processed_dir.glob("*.json")):
            try:
                docs.append(json.loads(jf.read_text(encoding="utf-8")))
            except Exception:
                pass

        print(f"[STATS] processed_docs={len(docs)}")

        ct_counts = Counter(d.get("content_type", "unknown") for d in docs)
        if ct_counts:
            print("[STATS] content_type breakdown:")
            for k, v in ct_counts.most_common():
                print(f"  - {k}: {v}")

        try:
            count = vs.collection.count()  # type: ignore[attr-defined]
            print(f"[STATS] vector_chunks={count}")
        except Exception as e:
            print(f"[STATS] vector_chunks=unknown ({e})")

        urls = sorted({d.get("url", "") for d in docs if d.get("url")})
        print(f"[STATS] unique_urls={len(urls)}")
        for u in urls:
            print(f"  - {u}")

        return

    # --------------------------------------------------
    # records (build directory records once)
    # --------------------------------------------------
    elif args.command == "records":
        from src.directory.build_records import build_directory_records

        processed_dir = "data/processed"
        out_path = "data/records/directory.jsonl"
        n = build_directory_records(processed_dir, "id=64&", out_path)
        print(f"[RECORDS] built={n} -> {out_path}")
        return

    # --------------------------------------------------
    # crawl (BFS + state hash skip)
    # --------------------------------------------------
    if args.command == "crawl":
        web_cfg = cfg.get("web", {})
        start_urls = web_cfg.get("start_urls", [])
        allowed_domain = web_cfg.get("domain", "")
        depth_limit = int(web_cfg.get("crawl_depth", 1))
        rate_limit = float(web_cfg.get("rate_limit_sec", 1.0))
        timeout_sec = int(web_cfg.get("timeout_sec", 20))
        deny_extensions = web_cfg.get("deny_extensions", [])

        ingest_cfg = cfg.get("ingest", {})
        save_raw = bool(ingest_cfg.get("save_raw_html", True))
        save_clean = bool(ingest_cfg.get("save_clean_text", True))

        print(f"[CRAWL] start_urls = {start_urls}")
        if not start_urls:
            print("[CRAWL] No start_urls configured. Edit configs/config.yaml")
            return

        from collections import deque
        from src.ingest.discover import extract_links
        from src.ingest.state import load_state, save_state, get_page_hash, set_page_hash
        import time

        raw_dir = "data/raw"
        processed_dir = "data/processed"

        state = load_state()
        changed = 0
        skipped = 0

        q = deque([(u, 0) for u in start_urls])
        visited = set()

        while q:
            url, depth = q.popleft()
            if url in visited:
                continue
            visited.add(url)

            # Check deny extensions
            if any(url.lower().endswith(ext) for ext in deny_extensions):
                print(f"[CRAWL] d={depth} {url} -> SKIPPED (deny_extension)")
                continue

            res = fetch_url(url, timeout_sec=timeout_sec)

            msg = f"[CRAWL] d={depth} {url} -> {res.status_code} ({res.content_type})"
            if getattr(res, "error", ""):
                 msg += f" err={res.error}"
            print(msg)

            # (Auth Required handling is now done inside fetch_url by returning synthetic 200 OK page)

            if res.status_code != 200 or not res.html:
                continue

            saved = save_raw_html(raw_dir, url, res.html) if save_raw else ""
            if saved:
                print(f"[CRAWL] saved: {saved}")

            if save_clean:
                out_json, new_hash = process_raw_html_file(saved, processed_dir, url)

                old_hash = get_page_hash(state, url)
                if old_hash == new_hash:
                    skipped += 1
                else:
                    changed += 1
                    set_page_hash(state, url, new_hash, meta={"last_seen": time.time()})

                print(f"[CRAWL] processed: {out_json} (changed={old_hash != new_hash})")

            if depth < depth_limit:
                links = extract_links(url, res.html, allowed_domain)
                for nxt in links:
                    if nxt not in visited:
                        q.append((nxt, depth + 1))

            if rate_limit > 0:
                time.sleep(rate_limit)

        save_state(state)
        print(f"[CRAWL] done. visited={len(visited)} changed={changed} skipped={skipped}")
        return

    # --------------------------------------------------
    # index (incremental)
    # --------------------------------------------------
    elif args.command == "index":
        from src.ingest.state import (
            load_state, save_state, get_page_hash,
            get_indexed_hash, set_indexed_hash
        )

        vs = build_vectorstore(cfg)
        state = load_state()

        processed_dir = Path("data/processed")
        chunk_size = int(cfg["chunk"]["chunk_size"])
        overlap = int(cfg["chunk"]["overlap"])

        json_files = sorted(processed_dir.glob("*.json"))
        if not json_files:
            print("[INDEX] No processed json found. Run crawl first.")
            return

        total_upsert = 0
        total_skipped = 0
        total_deleted = 0

        for jf in json_files:
            doc = json.loads(jf.read_text(encoding="utf-8"))
            url = doc.get("url", "")
            if not url:
                continue

            content_hash = doc.get("content_hash") or get_page_hash(state, url)
            indexed_hash = get_indexed_hash(state, url)

            if indexed_hash and content_hash and indexed_hash == content_hash:
                total_skipped += 1
                continue

            try:
                vs.delete_by_url(url)
                total_deleted += 1
            except Exception:
                pass

            chunks = make_chunks(doc, chunk_size=chunk_size, overlap=overlap)

            ids = [c.chunk_id for c in chunks]
            texts = [c.text for c in chunks]
            metas = [c.metadata for c in chunks]

            if ids:
                vs.upsert(ids=ids, texts=texts, metadatas=metas)
                total_upsert += len(ids)

            if content_hash:
                set_indexed_hash(state, url, content_hash)

        vs.persist()
        save_state(state)

        print(f"[INDEX] done. upsert_chunks={total_upsert} deleted_urls={total_deleted} skipped_docs={total_skipped}")
        return

    # --------------------------------------------------
    # chat (warmup + filter + org prompt + cache + logging)
    # --------------------------------------------------
    # --------------------------------------------------
    # chat (Refactored to use ChatEngine)
    # --------------------------------------------------
    # --------------------------------------------------
    # records (Rebuild directory.jsonl)
    # --------------------------------------------------
    elif args.command == "records":
        from src.directory.build_records import build_directory_records
        
        print("[RECORDS] Rebuilding directory records...")
        processed_dir = "data/processed"
        out_path = "data/records/directory.jsonl"
        # Use common substring for directory page
        target_substr = "Itemid=81" # Based on logs or assumption. Or "id=64" logic?
        # Wait, previous build_records logic mentioned id=64?
        # Let's use valid substring often seen. "Itemid=81" observed in crawl logs?
        # Or checking 'directory_home'?
        # Let's try "Itemid=81" or "content&view=article&id=56".
        # Safe bet: "phone" or "directory"?
        # Actually build_records.py comment said "(id=64)". I will use "id=64".
        
        try:
             # Try id=64 first
             count = build_directory_records(processed_dir, "view=article&id=64", out_path)
             print(f"[RECORDS] Built {count} records to {out_path}")
        except Exception as e:
             print(f"[RECORDS] Error: {e}")
             # specific fail
             
        return

    # --------------------------------------------------
    # chat (Refactored to use ChatEngine)
    # --------------------------------------------------
    elif args.command == "chat":
        from src.core.chat_engine import ChatEngine

        run_id = os.environ.get("RUN_ID") or make_run_id()
        run_dir = ensure_run_dir(run_id)
        log_path = run_dir / "chat_log.jsonl"

        print(f"[CHAT] run_id={run_id}")
        
        engine = ChatEngine(cfg)
        engine.warmup()
        
        print("[CHAT] Type your question (Ctrl+C to exit)")

        while True:
            try:
                q = input("\nQ> ").strip()
            except EOFError:
                break
            if not q:
                continue

            resp = engine.process(q)
            
            # Print Route / Latency Debug
            route = resp.get("route", "unknown")
            lat = resp.get("latencies", {})
            total_ms = lat.get("total", 0.0)
            
            # Contact hits have their own printing logic inside process? 
            # actually process returns structure, we should print it here.
            # But process() currently formats the answer text fully.
            
            print(f"[DEBUG] route={route} latency={total_ms:.2f}ms "
                  f"(routing={lat.get('routing',0):.2f}ms, vs={lat.get('vector_search',0):.2f}ms, llm={lat.get('llm',0):.2f}ms)")

            print("\n[ANSWER]")
            print(resp["answer"])
            
            if resp.get("context"):
                print(f"\n[CONTEXT]\n{resp['context']}\n")

            # Log
            if engine.save_log:
                log_entry = {
                    "ts": now_ts(),
                    "question": q,
                    "answer": resp["answer"],
                    "route": route,
                    "latencies": lat
                }
                append_jsonl(log_path, log_entry)


    else:
        print("[INFO] Unknown command.")
        return


if __name__ == "__main__":
    main()
