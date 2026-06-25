#!/usr/bin/env python3
"""Careful pre-deploy verification of data.json for tantivy.

Checks structure/format compatibility against the previous data.json,
flags anything that could break or degrade the tantivy index, and
reports content stats. Read-only: makes no changes.
"""
import json
import glob
import os
import sys

NEW = "data.json"
EXPECTED_KEYS = ["person", "date_of_report", "ref", "name_of_deceased",
                 "coroner_name", "coroner_area", "category", "filename",
                 "text", "url"]

problems = []
warnings = []


def check(cond, msg):
    if not cond:
        problems.append(msg)


def warn(cond, msg):
    if not cond:
        warnings.append(msg)


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception as e:
                problems.append(f"line {i}: invalid JSON: {e}")
    return rows


print("=" * 60)
print("VERIFYING", NEW)
print("=" * 60)

rows = load_jsonl(NEW)
n = len(rows)
print(f"records: {n}")

# --- schema: keys present, order, types, no nulls ---
bad_keys = bad_order = nonstr = nullv = 0
for r in rows:
    keys = list(r.keys())
    if set(keys) != set(EXPECTED_KEYS):
        bad_keys += 1
    if keys != EXPECTED_KEYS:
        bad_order += 1
    for k in EXPECTED_KEYS:
        v = r.get(k)
        if v is None:
            nullv += 1
        elif not isinstance(v, str):
            nonstr += 1
check(bad_keys == 0, f"{bad_keys} records have wrong key set")
warn(bad_order == 0, f"{bad_order} records have keys in a different order (tantivy reads by name; cosmetic)")
check(nonstr == 0, f"{nonstr} non-string field values")
check(nullv == 0, f"{nullv} null field values (old file had some null urls)")
print(f"schema: wrong_keys={bad_keys} non_str={nonstr} null={nullv}")

# --- content health ---
empty_text = sum(1 for r in rows if not r.get("text", "").strip())
tiny_text = sum(1 for r in rows if 0 < len(r.get("text", "").strip()) < 50)
has_nul = sum(1 for r in rows if "\x00" in r.get("text", ""))
print(f"empty text records: {empty_text}")
print(f"very short (<50 char) text records: {tiny_text}")
check(has_nul == 0, f"{has_nul} records contain NUL bytes (can break indexing)")

# --- uniqueness ---
filenames = [r.get("filename", "") for r in rows]
dupes = len(filenames) - len(set(filenames))
warn(dupes == 0, f"{dupes} duplicate filenames")
print(f"duplicate filenames: {dupes}")

# --- urls ---
bad_url = sum(1 for r in rows if not r.get("url", "").startswith("https://www.judiciary.uk/"))
warn(bad_url == 0, f"{bad_url} urls not under judiciary.uk")
print(f"non-judiciary urls: {bad_url}")

# --- encoding round-trips (ensure_ascii=False, valid utf-8) ---
try:
    with open(NEW, "rb") as f:
        raw = f.read()
    raw.decode("utf-8")
    print("utf-8 decode: OK")
except Exception as e:
    problems.append(f"file is not valid utf-8: {e}")

# --- compare to previous data.json backup ---
baks = sorted(glob.glob("data.json.bak*"))
if baks:
    old = load_jsonl(baks[-1])
    old_fn = {r.get("filename") for r in old}
    new_fn = set(filenames)
    print(f"\nvs {baks[-1]}: old={len(old)} new={n}")
    print(f"  added filenames:   {len(new_fn - old_fn)}")
    print(f"  removed filenames: {len(old_fn - new_fn)}")
    lost = old_fn - new_fn
    if lost:
        warnings.append(f"{len(lost)} filenames in old file are missing from new "
                        f"(e.g. {sorted(lost)[:3]})")

# --- content stats ---
asthma = sum(1 for r in rows if "asthma" in r.get("text", "").lower())
print(f"\nrecords mentioning 'asthma': {asthma}")

# --- cross-check against on-disk texts ---
txt_count = len(glob.glob(os.path.join("texts", "*.txt")))
print(f"texts/*.txt on disk: {txt_count}  (records: {n})")
warn(txt_count == n, f"record count {n} != txt file count {txt_count}")

print("\n" + "=" * 60)
if problems:
    print(f"❌ {len(problems)} PROBLEM(S):")
    for p in problems:
        print("  -", p)
else:
    print("✅ no blocking problems")
if warnings:
    print(f"⚠️  {len(warnings)} warning(s):")
    for w in warnings:
        print("  -", w)
print("=" * 60)
sys.exit(1 if problems else 0)
