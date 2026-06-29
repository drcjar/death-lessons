from __future__ import annotations
#!/usr/bin/env python3
"""Build the downloadable corpus artifact sold via the dataset offering.

Takes the pipeline's data.json (newline-delimited JSON) and writes a
gzipped JSONL plus a small README/licence note into the same archive
directory. Run after each `make update` refresh.

Usage:
  python build_dataset_artifact.py /path/to/data.json /path/to/out/deathlessons-corpus.jsonl.gz
"""
import gzip
import json
import os
import shutil
import sys


def build(src: str, dst: str) -> None:
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    n = 0
    # stream-copy line by line so we never hold the whole corpus in memory,
    # and validate each line is JSON on the way through.
    with open(src, "rb") as fin, gzip.open(dst, "wb") as fout:
        for line in fin:
            if not line.strip():
                continue
            json.loads(line)  # validate
            fout.write(line if line.endswith(b"\n") else line + b"\n")
            n += 1
    note = os.path.join(os.path.dirname(dst) or ".", "README.txt")
    with open(note, "w") as f:
        f.write(
            "deathlessons.org corpus\n"
            f"{n} documents (PFD reports + agency responses), full extracted text\n"
            "(OCR where needed) plus metadata fields.\n\n"
            "Source documents are public Prevention of Future Death reports from\n"
            "judiciary.uk (Crown copyright). This product is the cleaned, OCR'd,\n"
            "de-duplicated, metadata-tagged compilation; you are paying for that\n"
            "value-add, not the underlying public records.\n"
        )
    print(f"[DONE] wrote {n} docs to {dst} ({os.path.getsize(dst):,} bytes)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    build(sys.argv[1], sys.argv[2])
