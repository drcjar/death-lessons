#!/usr/bin/env python3
"""Run one saved-query alert cycle. Invoke after the pipeline refresh and
tantivy re-index, e.g. from the deploy/refresh script:

    make update                       # rebuild data.json
    sudo systemctl restart tantiivy   # re-index
    .venv/bin/python run_alerts.py    # email subscribers about new matches

Safe to run repeatedly: each document only ever alerts once.
"""
import logging

from app.alerts import run_alert_cycle
from app.db import SessionLocal, init_db


def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    db = SessionLocal()
    try:
        summary = run_alert_cycle(db)
        print("[ALERTS]", summary)
    finally:
        db.close()


if __name__ == "__main__":
    main()
