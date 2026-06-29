#!/usr/bin/env python3
"""Parallel OCR pass for PDFs that yielded no extractable text.

Targets every file marked 'ocr' in extraction_source.json that lacks a
real texts/*.txt. Renders pages with poppler (pdf2image) and runs
tesseract via pytesseract, mirroring the notebook's
extract_ocr_text_for_missing(). Resumable: a PDF with an existing
txt > 50 bytes is skipped. Each worker pins tesseract/poppler to a
single thread so the process pool isn't oversubscribed.
"""
import os
os.environ.setdefault("OMP_THREAD_LIMIT", "1")  # keep tesseract single-threaded per worker

import json
import glob
from concurrent.futures import ProcessPoolExecutor, as_completed

from pdf2image import convert_from_path
import pytesseract

DOWNLOAD_DIR = "downloads"
TEXT_DIR = "texts"
LOG_PATH = "extraction_source.json"
WORKERS = 12
DPI = 200


def ocr_one(filename):
    pdf_path = os.path.join(DOWNLOAD_DIR, filename)
    txt_path = os.path.join(TEXT_DIR, filename + ".txt")
    if os.path.exists(txt_path) and os.path.getsize(txt_path) > 50:
        return filename, "skip", 0
    try:
        images = convert_from_path(pdf_path, dpi=DPI, thread_count=1)
        chunks = [pytesseract.image_to_string(img) for img in images]
        text = "\n".join(chunks).strip()
        if text:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            return filename, "ocr_ok", len(text)
        return filename, "empty", 0
    except Exception as e:
        return filename, f"error:{type(e).__name__}", 0


def main():
    os.makedirs(TEXT_DIR, exist_ok=True)
    source_log = json.load(open(LOG_PATH))

    todo = []
    for fn, method in source_log.items():
        if method != "ocr":
            continue
        txt = os.path.join(TEXT_DIR, fn + ".txt")
        if os.path.exists(txt) and os.path.getsize(txt) > 50:
            continue
        if os.path.exists(os.path.join(DOWNLOAD_DIR, fn)):
            todo.append(fn)
    total = len(todo)
    print(f"[START] OCR for {total} pdfs", flush=True)

    done = ok = empty = err = 0
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(ocr_one, fn): fn for fn in todo}
        for fut in as_completed(futs):
            fn, status, _ = fut.result()
            done += 1
            if status == "ocr_ok":
                ok += 1
                source_log[fn] = "ocr_done"
            elif status == "empty":
                empty += 1
            elif status.startswith("error"):
                err += 1
            if done % 100 == 0:
                print(f"[{done}/{total}] ok={ok} empty={empty} err={err}", flush=True)
                json.dump(source_log, open(LOG_PATH, "w"), indent=2)

    json.dump(source_log, open(LOG_PATH, "w"), indent=2)
    print(f"[DONE] processed={done} text_recovered={ok} still_empty={empty} errors={err}", flush=True)


if __name__ == "__main__":
    main()
