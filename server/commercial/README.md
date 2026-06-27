# deathlessons.org — commercial app

A small FastAPI service for the paid offerings, built to run **on the
existing Lightsail box** alongside nginx + tantivy. **No extra hosting
cost**; Stripe charges only a percentage of actual sales; email fits
Resend's free tier (or AWS SES).

The free public search is unaffected — it stays on the static site +
tantivy. This app only handles:

1. **Bulk dataset download** — one-off Stripe payment → signed download link.
2. **Saved-query alerts** — subscription (matcher ships in Phase 2).
3. **Bespoke report** — enquiry form → email (manual fulfilment).

## Architecture

```
nginx ──/api──────────────► tantivy serve  :3000   (free public search)
      └─app.deathlessons.org► this FastAPI :8000   (accounts, Stripe, downloads)
                                   └── SQLite file (users, purchases, subs)
```

- **Auth:** passwordless magic links (no passwords stored).
- **DB:** SQLite (one file; no DB server).
- **Secrets:** all from `.env` (gitignored) — nothing in the repo.

## Local run (no secrets needed)

```
cd server/commercial
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # leave secrets blank for dev
# DEV_MODE defaults true: emails print to the console, cookies non-secure
uvicorn app.main:app --reload
```

Visit http://localhost:8000/pricing. Sign in at `/login`; the magic-link
URL is printed to the console (since `DEV_MODE=true`).

## Stripe setup (one-off)

In the Stripe dashboard:
1. Create two **Products/Prices**: a one-off price (dataset) and a
   recurring price (alerts). Put the price IDs in `.env`
   (`STRIPE_PRICE_DATASET`, `STRIPE_PRICE_ALERTS`).
2. Add a **webhook** endpoint → `https://app.deathlessons.org/stripe/webhook`,
   subscribe to `checkout.session.completed` and
   `customer.subscription.*`. Copy the signing secret into
   `STRIPE_WEBHOOK_SECRET`.
3. Put your secret key in `STRIPE_SECRET_KEY`.
4. Enable the **Customer Portal** (Settings → Billing) so `/portal` works.

> Note: you can reuse your existing Stripe account, but consider a
> separate **product**/statement-descriptor (or a separate account) to
> keep the data product distinct from the medical business for
> accounting/VAT. Worth a word with your accountant.

Test with Stripe **test mode** keys first (card `4242 4242 4242 4242`).
Use the Stripe CLI to replay webhooks locally:
`stripe listen --forward-to localhost:8000/stripe/webhook`.

## Email

Default is **Resend** (free tier: ample for magic links + alerts). Set
`RESEND_API_KEY` and verify your sending domain. Since you're on AWS,
**SES** is an alternative (fractions of a cent); swap the one HTTP call
in `app/emailer.py` for a boto3 `send_email` if you prefer.

## Deploy to Lightsail

```
# on the box, as ubuntu
sudo mkdir -p /home/ubuntu/commercial && sudo chown ubuntu /home/ubuntu/commercial
# copy server/commercial/* there (rsync), then:
cd /home/ubuntu/commercial
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env            # fill in secrets
mkdir -p data

# build the dataset artifact from the latest data.json
.venv/bin/python build_dataset_artifact.py \
    /home/ubuntu/search/data.json data/deathlessons-corpus.jsonl.gz

# service + reverse proxy
sudo cp deploy/commercial.service /etc/systemd/system/
sudo systemctl enable --now commercial
sudo cp deploy/nginx-commercial.conf /etc/nginx/sites-available/commercial
sudo ln -s /etc/nginx/sites-available/commercial /etc/nginx/sites-enabled/
sudo certbot --nginx -d app.deathlessons.org   # free TLS
sudo systemctl reload nginx
```

Point `app.deathlessons.org` DNS at the Lightsail static IP first.

## Refresh (run after each dataset update)

After each pipeline refresh (`make update` in the notebooks dir):

```
# 1. rebuild the buyer artifact so downloads are current
.venv/bin/python build_dataset_artifact.py /home/ubuntu/search/data.json \
    data/deathlessons-corpus.jsonl.gz

# 2. re-index tantivy (so alert matching sees the new docs)
sudo systemctl restart tantiivy.service

# 3. email subscribers about new docs matching their saved searches
.venv/bin/python run_alerts.py
```

Order matters: alerts query the live tantivy index, so step 3 must run
after step 2. `run_alerts.py` is safe to re-run — each document only ever
alerts once (tracked in the `seen_docs` table; the very first run seeds
silently so nobody is emailed the back-catalogue).

A simple cron/systemd-timer wrapping these three steps automates the
whole refresh.

## Status

- [x] Phase 0 — foundation (auth, Stripe, account, webhook)
- [x] Phase 1 — bulk dataset download
- [x] Phase 2 — saved-query alerts (management UI + matcher, `run_alerts.py`)
- [ ] Phase 3 — bespoke flow is enquiry-only; add Stripe payment if desired
