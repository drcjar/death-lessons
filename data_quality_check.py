#!/usr/bin/env python3
"""Data-quality audit of the judiciary.uk PFD data as scraped into
report_pages.json. Produces a markdown report (data_quality_report.md)
of issues worth feeding back to the judiciary.

Checks:
  1. Duplicate reference numbers across different report pages
  2. URL-slug name vs published "Deceased name" mismatches (typos)
  3. Multiple report pages for the same deceased (URL variants)
  4. Missing PDFs on a report page
  5. Missing published metadata fields (ref/date/coroner/area/category/name)
  6. Reference number in filename disagreeing with the page's Ref field
  7. Empty (0-byte) PDFs served by the site
"""
from __future__ import annotations
import json
import os
import re
import glob
from collections import defaultdict, Counter
from difflib import SequenceMatcher

from bs4 import BeautifulSoup

CACHE = "report_pages.json"
DOWNLOADS = "downloads"
OUT = "data_quality_report.md"

LABELS = [("date_of_report", r"date of report"), ("name_of_deceased", r"deceased name"),
          ("coroner_name", r"coroner'?s? name"), ("coroner_area", r"coroner'?s? area"),
          ("category", r"category"), ("ref", r"ref"),
          ("_b", r"this report is being sent to")]
LABEL_RE = re.compile("(?:" + "|".join(f"(?P<{k}>{p})" for k, p in LABELS) + r")\s*:", re.I)
REF_RE = re.compile(r"\b(20\d{2})[-/ ]?(\d{4})\b")


def clean(t):
    return re.sub(r"[\xa0​\n\r]+", " ", t).strip()


def parse_fields(paras):
    out = {}
    for html in paras:
        text = clean(BeautifulSoup(html, "html.parser").get_text())
        ms = list(LABEL_RE.finditer(text))
        for i, m in enumerate(ms):
            k = m.lastgroup
            if k == "_b":
                continue
            end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
            val = text[m.start():end]
            val = re.sub(r"^[a-z'\s]+:\s*", "", val, flags=re.I).strip()
            out.setdefault(k, val)
    return out


def norm_name(s):
    s = re.sub(r"\bprevention[- ]of[- ]future[- ]deaths?[- ]report\b", "", s, flags=re.I)
    s = re.sub(r"\bregulation 28\b|\breport\b", "", s, flags=re.I)
    s = re.sub(r"[-_]\d+$", "", s.strip("-/ "))           # trailing -2/-3 variant
    s = re.sub(r"\b20\d{2}[-/ ]?\d{4}\b", "", s)           # ref numbers
    s = re.sub(r"[^a-z ]", " ", s.lower())
    return " ".join(s.split())


def slug_of(url):
    return url.rstrip("/").split("/")[-1]


def token_typos(slug_name, meta_name):
    """Slug tokens that are a near-miss spelling of a published-name token
    (same first letter, similar, not an exact match) — high-confidence typos.
    Ignores plain omissions (middle names) and multi-person reports."""
    st, mt = slug_name.split(), meta_name.split()
    out = []
    for t in st:
        if len(t) < 4 or t in mt:
            continue
        best = max(((SequenceMatcher(None, t, u).ratio(), u) for u in mt
                    if u and u[0] == t[0]), default=(0, ""))
        if best[1] and 0.6 <= best[0] < 1.0 and best[1] not in st:
            out.append((t, best[1]))
    return out


def main():
    cache = json.load(open(CACHE, encoding="utf-8"))
    pages = {}
    for url, rec in cache.items():
        paras = rec.get("paras", [])
        pdfs = [os.path.basename(h.split("?")[0]) for h in rec.get("pdfs", [])]
        f = parse_fields(paras)
        ref = f.get("ref", "")
        m = REF_RE.search(ref)
        ref_norm = f"{m.group(1)}-{m.group(2)}" if m else ""
        pages[url] = {"pdfs": pdfs, "ref": ref_norm,
                      "name": f.get("name_of_deceased", ""), "fields": f}

    n = len(pages)
    L = []
    def w(s=""): L.append(s)

    w("# deathlessons.org — data-quality audit of judiciary.uk PFD reports\n")
    w(f"Scope: **{n} report pages** scraped from the judiciary.uk Prevention of "
      "Future Deaths listing. Findings below are issues in the *published* data "
      "(URLs, titles, metadata) that may be worth correcting at source.\n")

    # 1. duplicate refs
    by_ref = defaultdict(list)
    for url, p in pages.items():
        if p["ref"]:
            by_ref[p["ref"]].append(url)
    dup_refs = {r: us for r, us in by_ref.items() if len(us) > 1}
    w(f"## 1. Duplicate reference numbers ({len(dup_refs)} refs on >1 page)\n")
    w("The same PFD reference number appears on multiple distinct report pages "
      "(different deceased). This may be legitimate (one report covering several "
      "co-reported deaths) or a reference-number collision / duplicate "
      "publication — worth reviewing.\n")
    for r in sorted(dup_refs)[:25]:
        w(f"- **{r}** → " + " , ".join(slug_of(u) for u in dup_refs[r]))
    if len(dup_refs) > 25:
        w(f"- …and {len(dup_refs) - 25} more")
    w()

    # 2. high-confidence spelling typos: slug token vs deceased-name token
    typos = []
    for url, p in pages.items():
        if not p["name"] or " and " in p["name"].lower() or "," in p["name"]:
            continue  # skip multi-person reports
        tt = token_typos(norm_name(slug_of(url)), norm_name(p["name"]))
        for slug_tok, name_tok in tt:
            typos.append((slug_of(url), p["name"], slug_tok, name_tok))
    w(f"## 2. Name disagreements between URL and page ({len(typos)})\n")
    w("The name in the page URL disagrees with the page's own published "
      "*Deceased name* field (e.g. `linda-books` vs *Linda Brooks*). In most "
      "cases the URL appears to be the misspelling, but either field could be "
      "wrong — worth reconciling, as the URL is the permanent shareable link.\n")
    w("| URL slug | Published name | URL token | name-field token |")
    w("|---|---|---|---|")
    for slug, name, bad, good in typos[:50]:
        w(f"| `{slug}` | {name} | {bad} | {good} |")
    if len(typos) > 50:
        w(f"\n…and {len(typos) - 50} more.")
    w()

    # 3. multiple pages per deceased
    by_name = defaultdict(list)
    for url, p in pages.items():
        nn = norm_name(p["name"])
        if nn and "redacted" not in nn:          # redacted names aren't one person
            by_name[nn].append((url, p["ref"]))
    multi = {k: v for k, v in by_name.items() if len(v) > 1}
    same_ref_multi = sum(1 for v in multi.values()
                         if len({r for _, r in v if r}) < len([r for _, r in v if r]))
    w(f"## 3. Same deceased on multiple report pages ({len(multi)} names)\n")
    w("Often legitimate (several reports about one death, refs differ), but worth "
      "checking for true duplicates. Examples:\n")
    for k in list(multi)[:12]:
        entries = multi[k]
        w(f"- **{k.title()}**: " + " , ".join(f"{slug_of(u)} ({r or '?'})" for u, r in entries))
    w()

    # 4 & 5. missing pieces
    no_pdf = [u for u, p in pages.items() if not p["pdfs"]]
    miss = Counter()
    for u, p in pages.items():
        for fld in ("ref", "name_of_deceased", "date_of_report",
                    "coroner_name", "coroner_area", "category"):
            if not p["fields"].get(fld, "").strip():
                miss[fld] += 1
    w(f"## 4. Report pages with no attached PDF ({len(no_pdf)})\n")
    for u in no_pdf[:20]:
        w(f"- {slug_of(u)}")
    w()
    w("## 5. Missing published metadata fields\n")
    w("| Field | Pages missing it | % |")
    w("|---|---|---|")
    for fld, c in miss.most_common():
        w(f"| {fld} | {c} | {100*c/n:.1f}% |")
    w()

    # 6. filename ref vs page ref
    ref_mismatch = []
    for url, p in pages.items():
        if not p["ref"]:
            continue
        for fn in p["pdfs"]:
            if "response" in fn.lower():
                continue
            m = REF_RE.search(fn)
            if m and f"{m.group(1)}-{m.group(2)}" != p["ref"]:
                ref_mismatch.append((slug_of(url), p["ref"], fn))
                break
    w(f"## 6. Filename ref ≠ page Ref field ({len(ref_mismatch)})\n")
    w("The reference baked into the PDF filename disagrees with the page's Ref.\n")
    for slug, ref, fn in ref_mismatch[:20]:
        w(f"- {slug}: page says **{ref}**, file is `{fn}`")
    w()

    # 7. empty PDFs on disk
    zero = [os.path.basename(p) for p in glob.glob(os.path.join(DOWNLOADS, "*.pdf"))
            if os.path.getsize(p) == 0]
    w(f"## 7. Empty (0-byte) PDFs served ({len(zero)})\n")
    for z in zero[:20]:
        w(f"- `{z}`")
    w()

    # 8. inconsistent "prevention of future deaths report" phrasing in URLs
    variants = Counter()
    malformed = []
    canon = "prevention-of-future-deaths-report"
    for url in pages:
        s = slug_of(url)
        m = re.search(r"prevent[a-z-]*future[a-z-]*report", s)
        if m:
            ph = m.group(0)
            variants[ph] += 1
            if ph != canon:
                malformed.append((s, ph))
    w(f"## 8. Inconsistent report-phrase spelling in URLs ({len(variants)} variants)\n")
    w(f"The canonical phrase is `{canon}`, but URLs use several spellings "
      "(missing “of”, singular “death”, etc.):\n")
    w("| phrase in URL | # URLs |")
    w("|---|---|")
    for ph, c in variants.most_common():
        flag = "" if ph == canon else "  ⚠"
        w(f"| `{ph}`{flag} | {c} |")
    w()

    w("---\n")
    w("### Summary counts\n")
    w(f"- report pages: {n}")
    w(f"- duplicate reference numbers: {len(dup_refs)}")
    w(f"- likely URL-name typos: {len(typos)}")
    w(f"- deceased names on multiple pages: {len(multi)}")
    w(f"- pages with no PDF: {len(no_pdf)}")
    w(f"- filename/Ref mismatches: {len(ref_mismatch)}")
    w(f"- empty PDFs: {len(zero)}")
    w(f"- malformed report-phrase URLs: {len(malformed)}")

    open(OUT, "w", encoding="utf-8").write("\n".join(L))
    # console summary
    print(f"report pages              : {n}")
    print(f"duplicate reference numbers: {len(dup_refs)}")
    print(f"likely URL-name typos     : {len(typos)}")
    print(f"deceased on multiple pages : {len(multi)}")
    print(f"pages with no PDF         : {len(no_pdf)}")
    print(f"filename/Ref mismatches   : {len(ref_mismatch)}")
    print(f"empty PDFs                : {len(zero)}")
    print(f"malformed phrase URLs     : {len(malformed)}")
    print(f"\n[written] {OUT}")


if __name__ == "__main__":
    main()
