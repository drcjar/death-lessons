"""Saved-query alerts.

After each pipeline refresh + tantivy re-index, run_alert_cycle():
  1. reads the current corpus filenames,
  2. finds documents not seen before (new since the last run),
  3. for each active subscriber's saved queries, asks tantivy which docs
     match and intersects with the new docs,
  4. emails each subscriber one digest of their new matches.

Matching reuses the live tantivy index, so alert relevance is identical
to the website search. The first run seeds the "seen" set silently so
subscribers aren't alerted about the entire back-catalogue.
"""
import json
import logging
from datetime import datetime
from urllib.parse import quote

import requests

from .config import get_settings
from .emailer import send_email
from .models import SavedQuery, SeenDoc, Subscription, User

log = logging.getLogger("commercial.alerts")
settings = get_settings()


def corpus_filenames(path: str | None = None) -> list[str]:
    path = path or settings.corpus_path
    names = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                names.append(json.loads(line)["filename"])
    return names


def _is_response(filename: str) -> bool:
    return "response" in filename.lower()


def tantivy_search(query: str, include_responses: bool) -> list[dict]:
    """Return matching docs (filename, ref, url) from the live tantivy index."""
    url = f"{settings.tantivy_url}/api?q={quote(query)}&nhits={settings.alert_nhits}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    out = []
    for hit in r.json().get("hits", []):
        doc = hit["doc"]
        fn = doc["filename"][0]
        if not include_responses and _is_response(fn):
            continue
        out.append({"filename": fn,
                    "ref": (doc.get("ref") or [""])[0],
                    "url": (doc.get("url") or [""])[0]})
    return out


def _alert_email_html(digest: list[tuple[SavedQuery, list[dict]]]) -> tuple[str, str]:
    html = ["<p>New Prevention of Future Death reports matched your saved searches:</p>"]
    text = ["New PFD reports matched your saved searches:\n"]
    for q, docs in digest:
        html.append(f'<h4>{len(docs)} new for &ldquo;{q.query}&rdquo;</h4><ul>')
        text.append(f"\n{len(docs)} new for \"{q.query}\":")
        for d in docs:
            label = d["ref"] or d["filename"]
            html.append(f'<li><a href="{d["url"]}">{label}</a></li>')
            text.append(f"  - {label}: {d['url']}")
        html.append("</ul>")
    html.append('<p style="color:#888"><small>Manage your saved searches at '
                f'{settings.base_url}/account</small></p>')
    text.append(f"\nManage your saved searches: {settings.base_url}/account")
    return "\n".join(html), "\n".join(text)


def run_alert_cycle(db, get_filenames=corpus_filenames, search=tantivy_search) -> dict:
    """Run one alert cycle. Returns a small summary dict (for logging/CLI)."""
    seen = {f for (f,) in db.query(SeenDoc.filename).all()}
    current = list(get_filenames())
    new_docs = set(current) - seen

    # First ever run: seed silently, never alert on the back-catalogue.
    if not seen:
        db.add_all([SeenDoc(filename=f) for f in current])
        db.commit()
        log.info("alerts seeded with %d docs (no emails on first run)", len(current))
        return {"seeded": len(current), "new": 0, "emails": 0}

    summary = {"new": len(new_docs), "emails": 0, "matches": 0}
    if new_docs:
        active_user_ids = {
            s.user_id for s in db.query(Subscription)
            .filter(Subscription.product == "alerts",
                    Subscription.status.in_(("active", "trialing"))).all()
        }
        for uid in active_user_ids:
            user = db.get(User, uid)
            digest = []
            for q in db.query(SavedQuery).filter_by(user_id=uid).all():
                try:
                    matched = {d["filename"]: d for d in search(q.query, q.include_responses)}
                except Exception as e:
                    log.error("search failed for query %r: %s", q.query, e)
                    continue
                hit_docs = [matched[f] for f in matched.keys() & new_docs]
                if hit_docs:
                    digest.append((q, hit_docs))
                    summary["matches"] += len(hit_docs)
                q.last_checked = datetime.utcnow()
            if digest:
                html, text = _alert_email_html(digest)
                send_email(user.email,
                           "New PFD reports matched your saved searches", html, text)
                summary["emails"] += 1
        db.commit()

    # Mark the new docs as seen only after alerting succeeded for this run.
    db.add_all([SeenDoc(filename=f) for f in new_docs])
    db.commit()
    log.info("alerts: %d new docs, %d matches, %d emails sent",
             summary["new"], summary["matches"], summary["emails"])
    return summary
