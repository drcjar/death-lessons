"""Stripe: customers, Checkout sessions, Customer Portal, and webhook
handling. Stripe has no fixed fee — it only takes a percentage of actual
sales — so this adds no running cost.
"""
import logging
from datetime import datetime

import stripe
from sqlalchemy.orm import Session

from .config import get_settings
from .models import BespokeEnquiry, Purchase, Subscription, User

log = logging.getLogger("commercial.payments")
settings = get_settings()
stripe.api_key = settings.stripe_secret_key


def ensure_customer(db: Session, user: User) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = stripe.Customer.create(email=user.email,
                                      metadata={"user_id": user.id})
    user.stripe_customer_id = customer.id
    db.commit()
    return customer.id


def checkout_dataset(db: Session, user: User) -> str:
    customer = ensure_customer(db, user)
    session = stripe.checkout.Session.create(
        mode="payment",
        customer=customer,
        line_items=[{"price": settings.stripe_price_dataset, "quantity": 1}],
        success_url=f"{settings.base_url}/account?purchased=dataset",
        cancel_url=f"{settings.base_url}/pricing",
        metadata={"user_id": user.id, "product": "dataset"},
    )
    return session.url


def checkout_alerts(db: Session, user: User) -> str:
    customer = ensure_customer(db, user)
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer,
        line_items=[{"price": settings.stripe_price_alerts, "quantity": 1}],
        success_url=f"{settings.base_url}/account?subscribed=alerts",
        cancel_url=f"{settings.base_url}/pricing",
        metadata={"user_id": user.id, "product": "alerts"},
    )
    return session.url


def portal(db: Session, user: User) -> str:
    customer = ensure_customer(db, user)
    session = stripe.billing_portal.Session.create(
        customer=customer, return_url=f"{settings.base_url}/account")
    return session.url


def send_bespoke_invoice(db: Session, enquiry: BespokeEnquiry, amount_pence: int,
                         currency: str = "gbp", description: str | None = None) -> str:
    """Create + finalise + send a Stripe invoice for a bespoke enquiry.
    Stripe emails the customer a hosted payment page. Returns its URL."""
    customer = stripe.Customer.create(
        email=enquiry.email, metadata={"bespoke_enquiry_id": enquiry.id})
    stripe.InvoiceItem.create(
        customer=customer.id, amount=amount_pence, currency=currency,
        description=description or f"Bespoke analytical report (enquiry #{enquiry.id})")
    invoice = stripe.Invoice.create(
        customer=customer.id, collection_method="send_invoice", days_until_due=14,
        metadata={"bespoke_enquiry_id": enquiry.id})
    invoice = stripe.Invoice.finalize_invoice(invoice.id)
    stripe.Invoice.send_invoice(invoice.id)
    enquiry.status = "invoiced"
    enquiry.stripe_invoice_id = invoice.id
    enquiry.amount = amount_pence
    enquiry.currency = currency
    db.commit()
    return invoice.hosted_invoice_url


# --- webhook -------------------------------------------------------------

def _user_for_event(db: Session, obj) -> User | None:
    uid = (obj.get("metadata") or {}).get("user_id")
    if uid:
        u = db.get(User, int(uid))
        if u:
            return u
    cust = obj.get("customer")
    if cust:
        return db.query(User).filter(User.stripe_customer_id == cust).first()
    return None


def handle_webhook(db: Session, payload: bytes, sig_header: str) -> None:
    event = stripe.Webhook.construct_event(
        payload, sig_header, settings.stripe_webhook_secret)
    obj = event["data"]["object"]
    etype = event["type"]

    if etype == "checkout.session.completed":
        user = _user_for_event(db, obj)
        if not user:
            log.error("checkout.session.completed with no resolvable user")
            return
        product = (obj.get("metadata") or {}).get("product")
        if obj.get("mode") == "payment" and product == "dataset":
            # idempotent on the unique stripe_session_id
            if not db.query(Purchase).filter_by(stripe_session_id=obj["id"]).first():
                db.add(Purchase(user_id=user.id, product="dataset",
                                stripe_session_id=obj["id"],
                                amount_total=obj.get("amount_total"),
                                currency=obj.get("currency")))
                db.commit()
                log.info("dataset purchase recorded for user %s", user.id)

    elif etype in ("customer.subscription.created",
                   "customer.subscription.updated",
                   "customer.subscription.deleted"):
        user = _user_for_event(db, obj)
        if not user:
            return
        sub = db.query(Subscription).filter_by(
            stripe_subscription_id=obj["id"]).first()
        period_end = (datetime.utcfromtimestamp(obj["current_period_end"])
                      if obj.get("current_period_end") else None)
        if sub is None:
            sub = Subscription(user_id=user.id, product="alerts",
                               stripe_subscription_id=obj["id"],
                               status=obj["status"],
                               current_period_end=period_end)
            db.add(sub)
        else:
            sub.status = obj["status"]
            sub.current_period_end = period_end
        db.commit()
        log.info("subscription %s -> %s for user %s", obj["id"], obj["status"], user.id)

    elif etype == "invoice.paid":
        eid = (obj.get("metadata") or {}).get("bespoke_enquiry_id")
        enquiry = (db.get(BespokeEnquiry, int(eid)) if eid
                   else db.query(BespokeEnquiry)
                   .filter_by(stripe_invoice_id=obj["id"]).first())
        if enquiry:
            enquiry.status = "paid"
            db.commit()
            log.info("bespoke enquiry %s marked paid", enquiry.id)
