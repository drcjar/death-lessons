#!/usr/bin/env python3
"""Robust, resumable downloader for PFD report PDFs.

Fixes the silent ~90% failure of the notebook's download_pdfs():
 - real browser User-Agent (judiciary.uk rate-limits the default urllib UA)
 - retries with exponential backoff, extra backoff on 429/503
 - polite throttling via a small thread pool
 - skips files already on disk (resumable: just re-run to continue)
 - validates the response is actually a PDF before saving
 - logs permanent failures to download_failures.json so nothing is silently lost
"""
import os
import sys
import json
import time
import glob
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

DOWNLOAD_DIR = "downloads"
CACHE_FILE = "cached_pdf_links.json"
FAIL_LOG = "download_failures.json"
WORKERS = 4
PER_REQUEST_DELAY = 0.15   # seconds, applied inside each worker before a request
MAX_RETRIES = 4
TIMEOUT = 45

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_print_lock = threading.Lock()
_counter_lock = threading.Lock()
_done = 0
_ok = 0
_fail = 0


def log(msg):
    with _print_lock:
        print(msg, flush=True)


def download_one(session, url, total):
    global _done, _ok, _fail
    filename = os.path.basename(url.split("?")[0])
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.isfile(filepath) and os.path.getsize(filepath) > 0:
        with _counter_lock:
            _done += 1
        return ("skip", url, None)

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(PER_REQUEST_DELAY)
            r = session.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
            if r.status_code in (429, 503):
                wait = min(60, 2 ** attempt * 2)
                last_err = f"HTTP {r.status_code}"
                time.sleep(wait)
                continue
            r.raise_for_status()
            content = r.content
            if not (content[:5] == b"%PDF-" or
                    "pdf" in r.headers.get("content-type", "").lower()):
                last_err = f"not a pdf (ctype={r.headers.get('content-type')})"
                break
            tmp = filepath + ".part"
            with open(tmp, "wb") as f:
                f.write(content)
            os.replace(tmp, filepath)
            with _counter_lock:
                _done += 1
                _ok += 1
                n = _done
            if n % 100 == 0:
                log(f"[{n}/{total}] ok={_ok} fail={_fail}  last={filename[:60]}")
            return ("ok", url, None)
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(min(30, 2 ** attempt))

    with _counter_lock:
        _done += 1
        _fail += 1
    return ("fail", url, last_err)


def main():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    with open(CACHE_FILE) as f:
        links = json.load(f)

    # dedupe by basename (download uses basename as the filename)
    seen = set()
    urls = []
    for l in links:
        bn = os.path.basename(l.split("?")[0])
        if bn.lower().endswith(".pdf") and bn not in seen:
            seen.add(bn)
            urls.append(l)

    on_disk = {os.path.basename(p) for p in glob.glob(os.path.join(DOWNLOAD_DIR, "*.pdf"))}
    todo = [u for u in urls if os.path.basename(u.split("?")[0]) not in on_disk]
    total = len(todo)
    log(f"[START] {len(urls)} unique pdf urls, {len(on_disk)} already on disk, {total} to fetch")

    failures = []
    session = requests.Session()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(download_one, session, u, total) for u in todo]
        for fut in as_completed(futs):
            status, url, err = fut.result()
            if status == "fail":
                failures.append({"url": url, "error": err})

    with open(FAIL_LOG, "w") as f:
        json.dump(failures, f, indent=2)

    final = len(glob.glob(os.path.join(DOWNLOAD_DIR, "*.pdf")))
    log(f"[DONE] ok={_ok} failed={_fail} -> {len(failures)} permanent failures "
        f"logged to {FAIL_LOG}. {final} pdfs now on disk.")


if __name__ == "__main__":
    main()
