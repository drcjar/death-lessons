from __future__ import annotations
#!/usr/bin/env python3
"""Send a Stripe invoice for a bespoke enquiry once you've scoped the price.

    python bespoke_invoice.py            # list open enquiries + their ids
    python bespoke_invoice.py <id> <amount_pence> ["description"]

Bespoke reports are custom-priced, so you capture the brief first
(/bespoke on the site), agree a price, then run this. Stripe emails the
customer a hosted payment page; the invoice.paid webhook marks the
enquiry paid automatically.

Example: python bespoke_invoice.py 3 45000 "Asthma PFD analysis 2013-2026"
         (45000 pence = £450.00)
"""
import sys

from app.db import SessionLocal, init_db
from app.models import BespokeEnquiry
from app import payments


def list_enquiries(db):
    rows = db.query(BespokeEnquiry).order_by(BespokeEnquiry.id.desc()).all()
    if not rows:
        print("No enquiries yet.")
        return
    for e in rows:
        amt = f"{e.amount/100:.2f} {e.currency}" if e.amount else "-"
        print(f"#{e.id:<4} {e.status:<9} {e.email:<30} {amt}  "
              f"{e.brief[:50].replace(chr(10), ' ')}")


def main():
    init_db()
    db = SessionLocal()
    try:
        if len(sys.argv) < 3:
            list_enquiries(db)
            print("\nUsage: python bespoke_invoice.py <id> <amount_pence> [\"description\"]")
            return
        eid, amount = int(sys.argv[1]), int(sys.argv[2])
        description = sys.argv[3] if len(sys.argv) > 3 else None
        enquiry = db.get(BespokeEnquiry, eid)
        if not enquiry:
            print(f"No enquiry #{eid}")
            return
        url = payments.send_bespoke_invoice(db, enquiry, amount, description=description)
        print(f"Invoiced enquiry #{eid} for {amount/100:.2f} GBP.")
        print(f"Hosted invoice: {url}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
