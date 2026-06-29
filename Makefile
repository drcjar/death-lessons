# deathlessons data pipeline — reproducible refresh.
# See PIPELINE.md for details. Every stage is resumable: re-running only
# does outstanding work (new reports, un-downloaded PDFs, un-extracted text).
#
# Usage:
#   make setup      # one-time: create venv + install deps
#   make update     # full refresh: fetch -> download -> extract -> ocr -> build -> verify
#   make <stage>    # run a single stage (fetch/download/extract/ocr/build/verify)

PY := ../.venv-work/bin/python
UV := uv

.PHONY: setup update fetch download extract ocr build verify clean-derived

setup:
	$(UV) venv --python 3.14 ../.venv-work
	$(UV) pip install --python ../.venv-work/bin/python -r requirements.txt
	@echo "Also ensure system packages: sudo apt install -y poppler-utils tesseract-ocr"

# Full pipeline in order. Each target depends on the previous conceptually,
# but they read/write files on disk so we just run them in sequence.
update: fetch download extract ocr build verify
	@echo "== refresh complete: data.json ready to deploy =="

fetch:
	$(PY) fetch_links.py

download:
	$(PY) robust_download.py

extract:
	$(PY) extract_parallel.py

ocr:
	$(PY) ocr_parallel.py

build:
	$(PY) build_data.py
	$(PY) -c "import pandas as pd; pd.read_json('data.json', lines=True).to_csv('data.csv', index=False)"

verify:
	$(PY) verify_data.py

# Remove derived artifacts (keeps downloads/ and texts/ caches).
clean-derived:
	rm -f data.json data.csv pipeline_checkpoint.json
