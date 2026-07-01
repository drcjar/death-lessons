#!/usr/bin/env python3
"""Create the Stripe products, prices, webhook and Customer Portal config for
the commercial app, then print the values to paste into the server .env.

Run locally with your Stripe TEST key first (nothing here is destructive):

    STRIPE_SECRET_KEY=sk_test_... BASE_URL=https://app.deathlessons.org \
        python setup_stripe.py

Re-runnable: existing products/prices are reused (keyed by metadata), so it
won't create duplicates. The webhook signing secret is only shown the first
time the endpoint is created — save it.

Amount overrides (minor units): DATASET_AMOUNT (default 4900 = £49.00),
ALERTS_AMOUNT (default 1900 = £19.00/mo), CURRENCY (default gbp).
"""
from __future__ import annotations
import os
import sys

import stripe

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
BASE_URL = os.environ.get("BASE_URL", "https://app.deathlessons.org")
DATASET_AMOUNT = int(os.environ.get("DATASET_AMOUNT", "4900"))
ALERTS_AMOUNT = int(os.environ.get("ALERTS_AMOUNT", "1900"))
CURRENCY = os.environ.get("CURRENCY", "gbp")

EVENTS = ["checkout.session.completed", "customer.subscription.created",
          "customer.subscription.updated", "customer.subscription.deleted",
          "invoice.paid"]


def _dl_key(obj):
    """Read obj.metadata['dl_key'] safely across stripe object versions."""
    try:
        return obj.metadata["dl_key"]
    except Exception:
        return None


def get_or_create_product(name, key):
    for p in stripe.Product.list(active=True, limit=100).auto_paging_iter():
        if _dl_key(p) == key:
            return p
    return stripe.Product.create(name=name, metadata={"dl_key": key})


def get_or_create_price(product, *, amount, recurring=None):
    for pr in stripe.Price.list(product=product.id, active=True, limit=100).auto_paging_iter():
        same_kind = bool(pr.recurring) == bool(recurring)
        same_int = (not recurring) or (pr.recurring and pr.recurring.interval == recurring["interval"])
        if pr.unit_amount == amount and pr.currency == CURRENCY and same_kind and same_int:
            return pr
    kw = {"product": product.id, "unit_amount": amount, "currency": CURRENCY}
    if recurring:
        kw["recurring"] = recurring
    return stripe.Price.create(**kw)


def ensure_webhook(url):
    for e in stripe.WebhookEndpoint.list(limit=100).auto_paging_iter():
        if e.url == url:
            return e, None  # exists; signing secret is not retrievable again
    e = stripe.WebhookEndpoint.create(url=url, enabled_events=EVENTS)
    return e, e.secret


def ensure_portal():
    if stripe.billing_portal.Configuration.list(limit=1).data:
        return
    stripe.billing_portal.Configuration.create(
        business_profile={"headline": "deathlessons.org"},
        features={"invoice_history": {"enabled": True},
                  "subscription_cancel": {"enabled": True},
                  "payment_method_update": {"enabled": True}})


def main():
    if not stripe.api_key:
        sys.exit("Set STRIPE_SECRET_KEY (use a sk_test_... key first).")
    mode = "TEST" if stripe.api_key.startswith("sk_test_") else "LIVE"
    dataset = get_or_create_product("deathlessons.org — corpus dataset", "dataset")
    alerts = get_or_create_product("deathlessons.org — saved-query alerts", "alerts")
    p_dataset = get_or_create_price(dataset, amount=DATASET_AMOUNT)
    p_alerts = get_or_create_price(alerts, amount=ALERTS_AMOUNT,
                                   recurring={"interval": "month"})
    hook_url = BASE_URL.rstrip("/") + "/stripe/webhook"
    hook, secret = ensure_webhook(hook_url)
    ensure_portal()

    print(f"\n# ---- Stripe ({mode}) — paste into the server .env ----")
    print(f"STRIPE_PRICE_DATASET={p_dataset.id}")
    print(f"STRIPE_PRICE_ALERTS={p_alerts.id}")
    if secret:
        print(f"STRIPE_WEBHOOK_SECRET={secret}")
    else:
        print(f"# webhook already exists at {hook_url} ({hook.id}); its secret is")
        print(f"# only shown once. Reuse your saved STRIPE_WEBHOOK_SECRET, or delete")
        print(f"# the endpoint in the dashboard and re-run to mint a fresh one.")
    print("# Customer Portal: configured.")
    print(f"# amounts: dataset {DATASET_AMOUNT/100:.2f} {CURRENCY.upper()}, "
          f"alerts {ALERTS_AMOUNT/100:.2f} {CURRENCY.upper()}/mo "
          f"(override with DATASET_AMOUNT / ALERTS_AMOUNT)")


if __name__ == "__main__":
    main()
