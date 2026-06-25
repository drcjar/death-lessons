#!/usr/bin/env python3
"""Parallel text extraction over downloads/*.pdf -> texts/*.txt.

Same extract_text_smart logic as the notebook (pdfminer -> pdfplumber ->
mark 'ocr'), but run across a process pool. Resumable: skips PDFs that
already have a txt and a log entry. Updates extraction_source.json.
"""
import os
import io
import glob
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed

import pdfplumber
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter

DOWNLOAD_DIR = "downloads"
TEXT_DIR = "texts"
LOG_PATH = "extraction_source.json"
WORKERS = 12


def extract_text_smart(pdf_path, min_length=200, min_space_ratio=0.05):
    def space_ratio(text):
        return text.count(" ") / len(text) if text else 0
    try:
        rm = PDFResourceManager()
        buf = io.StringIO()
        conv = TextConverter(rm, buf, laparams=LAParams())
        interp = PDFPageInterpreter(rm, conv)
        with open(pdf_path, 'rb') as fh:
            for page in PDFPage.get_pages(fh, caching=True, check_extractable=False):
                interp.process_page(page)
            text = buf.getvalue()
        conv.close()
        buf.close()
        if text and len(text.strip()) >= min_length and space_ratio(text) >= min_space_ratio:
            return text, 'pdfminer'
    except Exception:
        pass
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join([p.extract_text() or "" for p in pdf.pages])
        if text and len(text.strip()) >= min_length:
            return text, 'pdfplumber'
    except Exception:
        pass
    return "", "ocr"


def worker(filepath):
    filename = os.path.basename(filepath)
    try:
        text, source = extract_text_smart(filepath)
        if text:
            with open(os.path.join(TEXT_DIR, filename + '.txt'), "w", encoding="utf-8") as f:
                f.write(text)
        return filename, source
    except Exception as e:
        return filename, f"error:{type(e).__name__}"


def main():
    os.makedirs(TEXT_DIR, exist_ok=True)
    source_log = json.load(open(LOG_PATH)) if os.path.exists(LOG_PATH) else {}

    todo = []
    for fp in glob.glob(os.path.join(DOWNLOAD_DIR, '*.pdf')):
        fn = os.path.basename(fp)
        txt = os.path.join(TEXT_DIR, fn + '.txt')
        if fn in source_log and os.path.exists(txt):
            continue
        todo.append(fp)
    total = len(todo)
    print(f"[START] {total} pdfs to extract ({len(source_log)} already logged)")

    done = 0
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(worker, fp): fp for fp in todo}
        for fut in as_completed(futs):
            fn, source = fut.result()
            source_log[fn] = source
            done += 1
            if done % 500 == 0:
                print(f"[{done}/{total}] {Counter(source_log.values())}")
                json.dump(source_log, open(LOG_PATH, "w"), indent=2)

    json.dump(source_log, open(LOG_PATH, "w"), indent=2)
    print("[DONE]", Counter(source_log.values()))


if __name__ == "__main__":
    main()
