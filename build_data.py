#!/usr/bin/env python3
"""Extract text from downloaded PDFs and rebuild data.json.

Replicates the notebook's extract_text_from_pdfs() and
combine_text_and_metadata_to_json() exactly, so the output schema is
unchanged. Runs standalone because the notebook kernel venv is broken.

OCR note: tesseract is not installed, so scanned/image-only PDFs (those
that yield no text from pdfminer/pdfplumber) are logged as "ocr" with no
text, exactly as before. They are listed at the end so they can be OCR'd
once tesseract is available.
"""
import os
import io
import glob
import json
import re

import pdfplumber
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from bs4 import BeautifulSoup

DOWNLOAD_DIR = "downloads"
TEXT_DIR = "texts"
LOG_PATH = "extraction_source.json"
METADATA_PATH = "people_data.json"
OUTPUT_PATH = "data.json"


def extract_text_smart(pdf_path, min_length=200, min_space_ratio=0.05):
    def space_ratio(text):
        if not text:
            return 0
        return text.count(" ") / len(text)

    try:
        resource_manager = PDFResourceManager()
        fake_file_handle = io.StringIO()
        converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
        page_interpreter = PDFPageInterpreter(resource_manager, converter)
        with open(pdf_path, 'rb') as fh:
            for page in PDFPage.get_pages(fh, caching=True, check_extractable=False):
                page_interpreter.process_page(page)
            text = fake_file_handle.getvalue()
        converter.close()
        fake_file_handle.close()
        if text and len(text.strip()) >= min_length:
            if space_ratio(text) >= min_space_ratio:
                return text, 'pdfminer'
    except Exception as e:
        print(f"[PDFMINER ERROR] {os.path.basename(pdf_path)}: {e}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        if text and len(text.strip()) >= min_length:
            return text, 'pdfplumber'
    except Exception as e:
        print(f"[PDFPLUMBER ERROR] {os.path.basename(pdf_path)}: {e}")

    return "", "ocr"


def extract_text_from_pdfs():
    os.makedirs(TEXT_DIR, exist_ok=True)
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            source_log = json.load(f)
    else:
        source_log = {}

    pdfs = glob.glob(os.path.join(DOWNLOAD_DIR, '*.pdf'))
    total = len(pdfs)
    for i, filepath in enumerate(pdfs, 1):
        filename = os.path.basename(filepath)
        output_path = os.path.join(TEXT_DIR, filename + '.txt')
        if filename in source_log and os.path.exists(output_path):
            continue
        try:
            text, source = extract_text_smart(filepath)
            if text:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text)
                source_log[filename] = source
            else:
                source_log[filename] = "ocr"
        except Exception as e:
            print(f"[ERROR] Failed to extract {filename}: {e}")
        if i % 200 == 0:
            print(f"[EXTRACT {i}/{total}]")
            with open(LOG_PATH, "w") as f:
                json.dump(source_log, f, indent=2)

    with open(LOG_PATH, "w") as f:
        json.dump(source_log, f, indent=2)

    from collections import Counter
    print("[EXTRACT DONE]", Counter(source_log.values()))
    return source_log


# C0 control chars except tab/newline/carriage-return. PDF text extraction
# occasionally emits NUL (e.g. a mangled "fi" ligature) or form-feed; these
# can break the tantivy indexer, so strip them from the indexed text.
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_text(text):
    return _CTRL.sub(" ", text)


# The judiciary metadata block comes in two shapes: separate paragraphs
# (one label each) and a single concatenated blob where labels are glued
# onto the previous value ("...27/02/2023Ref: 2023-0076Deceased name:...").
# So we locate each label by phrase (no word boundary — labels can be glued
# to letters/digits) and take the text up to the next label. "Coroners"/
# "Coroner" and "This report is being sent to" (a value terminator) are both
# handled. Order in _LABELS only affects regex alternation, not output.
_LABELS = [
    ("date_of_report", r"date of report"),
    ("name_of_deceased", r"deceased name"),
    ("coroner_name", r"coroner'?s? name"),
    ("coroner_area", r"coroner'?s? area"),
    ("category", r"category"),
    ("ref", r"ref"),
    ("_boundary", r"this report is being sent to"),
]
_LABEL_RE = re.compile(
    "(?:" + "|".join(f"(?P<{k}>{p})" for k, p in _LABELS) + r")\s*:",
    re.IGNORECASE)


def combine_text_and_metadata_to_json():
    def clean(text):
        return re.sub(r"[\xa0​\n\r]+", " ", text).strip()

    def extract_fields(paragraphs):
        fields = {"date_of_report": "", "ref": "", "name_of_deceased": "",
                  "coroner_name": "", "coroner_area": "", "category": ""}
        for html in paragraphs:
            text = clean(BeautifulSoup(html, "html.parser").get_text())
            matches = list(_LABEL_RE.finditer(text))
            for i, m in enumerate(matches):
                key = m.lastgroup
                if key == "_boundary":
                    continue
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                value = text[m.start():end].strip()
                if not fields[key]:            # first occurrence wins
                    fields[key] = value
        # ref is stored bare (no "Ref:" prefix), matching the existing format
        if fields["ref"]:
            fields["ref"] = re.sub(r"^ref\s*:?\s*", "", fields["ref"],
                                   flags=re.IGNORECASE).strip()
        return fields

    with open(METADATA_PATH, encoding='utf-8') as f:
        metadata_dict = json.load(f)
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            extraction_source = json.load(f)
    else:
        extraction_source = {}

    data = []
    for text_file in glob.glob(os.path.join(TEXT_DIR, '*.txt')):
        filename = os.path.basename(text_file).replace('.txt', '')
        pdf_filename = filename.replace('.pdf', '') + '.pdf'
        with open(text_file, encoding='utf-8') as f:
            content = sanitize_text(f.read())
        raw_meta = metadata_dict.get(pdf_filename, [])
        fields = extract_fields(raw_meta)
        # Most docs (responses + many reports) aren't keyed in people_data.json,
        # so their scraped ref is empty. The judiciary ref (YYYY-NNNN) is almost
        # always present in the filename, so fall back to it when missing.
        if not fields["ref"].strip():
            m = re.search(r'(20\d{2})[-_ ](\d{4})', pdf_filename)
            if m:
                fields["ref"] = f"{m.group(1)}-{m.group(2)}"
        base_slug = os.path.splitext(pdf_filename)[0].lower().replace(" ", "-")
        clean_slug = re.sub(r'-\d{4}-\d{4}(_.*)?$', '', base_slug)
        entry = {
            "person": base_slug,
            **fields,
            "filename": filename,
            "text": content,
            "url": f"https://www.judiciary.uk/prevention-of-future-death-reports/{clean_slug}/",
        }
        data.append(entry)

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        for entry in data:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    print(f"[DONE] Combined {len(data)} entries into {OUTPUT_PATH}")


if __name__ == "__main__":
    extract_text_from_pdfs()
    combine_text_and_metadata_to_json()
