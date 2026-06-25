#!/usr/bin/env python3
"""Stage 1: scrape judiciary.uk for PFD report pages, their PDF links and
metadata. Robust + incremental.

Walks the paginated PFD listing to collect report-page URLs, then visits
each report page to pull (a) every .pdf link and (b) the metadata
paragraphs. Pages already processed in report_pages.json are skipped, so
routine updates only fetch what's new.

Outputs (consumed by later stages):
  report_pages.json     - cache: {report_url: {"pdfs": [...], "paras": [...]}}
  cached_pdf_links.json - flat list of all PDF urls (download stage input)
  people_data.json      - {pdf_filename: [paragraph_html, ...]} (build stage input)
  urls.csv              - report-page urls

Use --refresh to re-scrape the listing for new reports (default). The
per-report cache means it is safe to re-run anytime.
"""
import os
import csv
import json
import time
import argparse

import requests
from bs4 import BeautifulSoup

LISTING = ("https://www.judiciary.uk/page/{}/"
           "?s&pfd_report_type&post_type=pfd&order=date")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

CACHE = "report_pages.json"
PDF_LINKS = "cached_pdf_links.json"
PEOPLE = "people_data.json"
URLS_CSV = "urls.csv"


def get(session, url, timeout=20, retries=4):
    last = None
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, headers={"User-Agent": UA}, timeout=timeout)
            if r.status_code in (429, 503):
                time.sleep(min(60, 2 ** attempt * 2))
                last = f"HTTP {r.status_code}"
                continue
            return r
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(min(30, 2 ** attempt))
    raise RuntimeError(last)


def collect_report_urls(session, delay):
    urls = []
    page = 0
    while True:
        r = get(session, LISTING.format(page))
        if r.status_code == 404:
            break
        soup = BeautifulSoup(r.content, "html.parser")
        links = [a["href"] for a in soup.find_all("a", class_="card__link")
                 if a.has_attr("href")]
        if not links:
            break
        urls.extend(links)
        print(f"[listing page {page}] +{len(links)} (total {len(urls)})", flush=True)
        page += 1
        time.sleep(delay)
    # de-dupe, preserve order
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=0.5)
    args = ap.parse_args()

    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    session = requests.Session()

    report_urls = collect_report_urls(session, args.delay)
    print(f"[listing] {len(report_urls)} report pages; "
          f"{len(cache)} already cached")

    new = [u for u in report_urls if u not in cache]
    print(f"[scrape] {len(new)} new report pages to fetch")
    for i, url in enumerate(new, 1):
        try:
            r = get(session, url)
            soup = BeautifulSoup(r.content, "html.parser")
            pdfs = [a["href"] for a in soup.find_all("a")
                    if a.get("href", "").lower().endswith(".pdf")]
            paras = [str(p) for p in soup.find_all("p")]
            cache[url] = {"pdfs": pdfs, "paras": paras}
            if not pdfs:
                print(f"[WARN] no pdf on {url}")
        except Exception as e:
            print(f"[ERROR] {url}: {e}")
            cache[url] = {"pdfs": [], "paras": []}
        if i % 50 == 0:
            print(f"[scrape {i}/{len(new)}]", flush=True)
            json.dump(cache, open(CACHE, "w"))
        time.sleep(args.delay)
    json.dump(cache, open(CACHE, "w"))

    # rebuild the flat outputs the rest of the pipeline expects
    all_pdfs, people = [], {}
    for url, rec in cache.items():
        for href in rec["pdfs"]:
            all_pdfs.append(href)
        # key metadata by every pdf filename on the page (matches build stage)
        for href in rec["pdfs"]:
            fn = os.path.basename(href.split("?")[0])
            people.setdefault(fn, rec["paras"])
    # de-dupe pdf links by basename, preserve order
    seen, flat = set(), []
    for u in all_pdfs:
        bn = os.path.basename(u.split("?")[0])
        if bn not in seen:
            seen.add(bn)
            flat.append(u)

    json.dump(flat, open(PDF_LINKS, "w"), indent=2)
    json.dump(people, open(PEOPLE, "w"), indent=2, ensure_ascii=False)
    with open(URLS_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["urls"])
        for u in cache:
            w.writerow([u])
    print(f"[DONE] {len(flat)} pdf links, {len(people)} metadata entries, "
          f"{len(cache)} report pages")


if __name__ == "__main__":
    main()
