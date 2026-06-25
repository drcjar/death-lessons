# deathlessons data pipeline

How `data.json` (the file the tantivy search index is built from) is
produced, and how to refresh it next time.

## What it does

Scrapes every Preventing Future Death (PFD) report PDF published on
judiciary.uk, extracts the text (with OCR fallback for scanned PDFs),
attaches the metadata shown on each report page, and writes one
newline-delimited JSON record per document to `data.json`.

`data.json` schema (10 string fields — must match `server/meta.json`):

```
person, date_of_report, ref, name_of_deceased, coroner_name,
coroner_area, category, filename, text, url
```

## Stages

| Stage | Script | Input → Output |
|-------|--------|----------------|
| 1. Fetch | `fetch_links.py` | judiciary.uk → `cached_pdf_links.json`, `people_data.json`, `urls.csv`, `report_pages.json` |
| 2. Download | `robust_download.py` | `cached_pdf_links.json` → `downloads/*.pdf` |
| 3. Extract | `extract_parallel.py` | `downloads/*.pdf` → `texts/*.txt` (+ `extraction_source.json`) |
| 4. OCR | `ocr_parallel.py` | scanned `downloads/*.pdf` → `texts/*.txt` |
| 5. Build | `build_data.py` | `texts/*.txt` + `people_data.json` → `data.json` |
| 6. Verify | `verify_data.py` | checks `data.json` is tantivy-ready |

Every stage is **resumable** — re-running only does outstanding work
(new reports, un-downloaded PDFs, un-OCR'd scans). State lives in the
files above, so you can stop/restart anytime.

## Why this exists (the bug it fixes)

The original notebook downloaded PDFs with `urllib.urlretrieve` — no
User-Agent, no delay, no retry. judiciary.uk rate-limits that, so ~90%
of downloads failed silently while the pipeline still marked itself
complete. Result: only ~1,500 of ~13,800 PDFs were fetched and searches
(e.g. asthma) missed most reports. Every script here uses a browser
User-Agent, retries with backoff, throttling, and **logs failures
instead of swallowing them** (`download_failures.json`).

## Requirements

```
# one-time
sudo apt install -y poppler-utils tesseract-ocr   # OCR system deps
make setup                                         # venv + python deps
```

Python deps are pinned in `requirements.txt`. Note the repo's original
`.venv` is broken (built against a Python that was later removed) and
`pyproject.toml` omits `requests`/`beautifulsoup4`; `make setup` builds
a clean `../.venv-work` that has everything.

## Refresh the data (next time)

```
make update      # fetch -> download -> extract -> ocr -> build -> verify
```

or run stages individually: `make fetch`, `make download`, `make
extract`, `make ocr`, `make build`, `make verify`.

`make fetch` re-scrapes the listing and only pulls report pages it
hasn't seen (tracked in `report_pages.json`), so updates are quick.

## Deploy

`verify_data.py` must pass first. Then publish `data.json` to the search
box and re-index:

```
# copy data.json to the tantivy working dir on the server, then:
sudo systemctl restart tantiivy.service   # ExecStartPre re-indexes data.json
```

The service (`server/tantiivy.service`) runs
`tantivy index -i . -f data.json` before serving, so restarting rebuilds
the index from the new file.

## Notebook

`deathlessons.ipynb` contains the original end-to-end pipeline. Its
`download_pdfs()` has been patched to the same robust logic used here, so
running the notebook no longer silently drops reports. The standalone
scripts above are the recommended path for refreshes (parallel, faster,
clearer logs).
