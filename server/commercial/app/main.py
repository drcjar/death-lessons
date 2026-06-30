"""deathlessons.org commercial app — accounts, Stripe checkout, and the
bulk dataset download. Runs as a small FastAPI service behind nginx on
the existing server (no extra hosting cost).

Public search stays on the static site + tantivy; this app only handles
the paid offerings.
"""
from __future__ import annotations
import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import (FileResponse, HTMLResponse, PlainTextResponse,
                               RedirectResponse, Response)
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import auth, payments
from .config import get_settings
from .db import get_db, init_db
from .downloads import make_download_token, verify_download_token
from .emailer import send_magic_link
from .models import Purchase, Subscription, SavedQuery, BespokeEnquiry
from .emailer import send_email
from sqlalchemy import func

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_url.startswith("sqlite"):
        path = settings.database_url.split("sqlite:///", 1)[-1]
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    init_db()
    yield


app = FastAPI(title="deathlessons.org commercial", lifespan=lifespan)
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


def _user(request: Request, db: Session):
    return auth.current_user(request, db)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/")
def home():
    # The app subdomain has no landing page; send visitors to the main site.
    return RedirectResponse("https://deathlessons.org/", status_code=302)


# --- pricing / marketing -------------------------------------------------

@app.get("/pricing", response_class=HTMLResponse)
def pricing(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "pricing.html", {
        "user": _user(request, db), "s": settings,
    })


# --- auth ----------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "login.html",
                                      {"user": _user(request, db)})


@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, email: str = Form(...), db: Session = Depends(get_db)):
    raw = auth.issue_login_token(db, email)
    link = f"{settings.base_url}/auth?token={raw}"
    send_magic_link(email.strip().lower(), link)
    return templates.TemplateResponse(request, "login_sent.html",
                                      {"email": email})


@app.get("/auth")
def auth_verify(token: str, db: Session = Depends(get_db)):
    user = auth.consume_login_token(db, token)
    if not user:
        return RedirectResponse("/login?error=expired", status_code=303)
    resp = RedirectResponse("/account", status_code=303)
    resp.set_cookie(auth.SESSION_COOKIE, auth.make_session_cookie(user),
                    max_age=auth.SESSION_MAX_AGE, httponly=True,
                    secure=not settings.dev_mode, samesite="lax")
    return resp


@app.get("/logout")
def logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(auth.SESSION_COOKIE)
    return resp


# --- account -------------------------------------------------------------

@app.get("/account", response_class=HTMLResponse)
def account(request: Request, db: Session = Depends(get_db)):
    user = _user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    has_dataset = bool(db.query(Purchase).filter_by(user_id=user.id, product="dataset").first())
    alerts_sub = (db.query(Subscription)
                  .filter_by(user_id=user.id, product="alerts")
                  .order_by(Subscription.id.desc()).first())
    saved = db.query(SavedQuery).filter_by(user_id=user.id).all()
    download_url = (f"/download?token={make_download_token(user.id, 'dataset')}"
                    if has_dataset else None)
    return templates.TemplateResponse(request, "account.html", {
        "user": user, "s": settings,
        "has_dataset": has_dataset, "download_url": download_url,
        "alerts_active": bool(alerts_sub and alerts_sub.is_active),
        "saved_queries": saved,
    })


# --- saved queries (alerts) ----------------------------------------------

def _alerts_active(db: Session, user) -> bool:
    sub = (db.query(Subscription)
           .filter_by(user_id=user.id, product="alerts")
           .order_by(Subscription.id.desc()).first())
    return bool(sub and sub.is_active)


@app.post("/saved-queries")
def add_saved_query(request: Request, query: str = Form(...),
                    include_responses: str = Form(default=""),
                    db: Session = Depends(get_db)):
    user = _user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    query = query.strip()
    # Only subscribers can save queries, and only up to the cap.
    if query and _alerts_active(db, user):
        count = db.query(func.count(SavedQuery.id)).filter_by(user_id=user.id).scalar()
        if count < settings.max_saved_queries:
            db.add(SavedQuery(user_id=user.id, query=query,
                              include_responses=bool(include_responses)))
            db.commit()
    return RedirectResponse("/account", status_code=303)


@app.post("/saved-queries/{sq_id}/delete")
def delete_saved_query(sq_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    sq = db.get(SavedQuery, sq_id)
    if sq and sq.user_id == user.id:      # only your own
        db.delete(sq)
        db.commit()
    return RedirectResponse("/account", status_code=303)


# --- checkout / portal ---------------------------------------------------

def _require_user(request: Request, db: Session):
    user = _user(request, db)
    if not user:
        return None
    return user


@app.post("/buy/dataset")
def buy_dataset(request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse(payments.checkout_dataset(db, user), status_code=303)


@app.post("/buy/alerts")
def buy_alerts(request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse(payments.checkout_alerts(db, user), status_code=303)


@app.get("/portal")
def billing_portal(request: Request, db: Session = Depends(get_db)):
    user = _require_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse(payments.portal(db, user), status_code=303)


# --- bespoke report intake ----------------------------------------------

@app.post("/bespoke", response_class=HTMLResponse)
def bespoke(request: Request, email: str = Form(...), brief: str = Form(...),
            db: Session = Depends(get_db)):
    enquiry = BespokeEnquiry(email=email.strip().lower(), brief=brief.strip())
    db.add(enquiry)
    db.commit()
    db.refresh(enquiry)
    send_email(settings.bespoke_inbox,
               f"New bespoke report enquiry #{enquiry.id}",
               f"<p>#{enquiry.id} from {email}</p><pre>{brief}</pre>"
               f"<p>Send an invoice: "
               f"<code>python bespoke_invoice.py {enquiry.id} &lt;amount_pence&gt;</code></p>",
               text=f"#{enquiry.id} from {email}\n\n{brief}\n\n"
                    f"Send an invoice: python bespoke_invoice.py {enquiry.id} <amount_pence>")
    return templates.TemplateResponse(request, "bespoke_sent.html", {})


# --- dataset download ----------------------------------------------------

@app.get("/download")
def download(token: str, db: Session = Depends(get_db)):
    parsed = verify_download_token(token)
    if not parsed:
        return PlainTextResponse("Link expired. Sign in and download again.", status_code=403)
    uid, product = parsed
    # Re-check entitlement at download time (not just at link-mint time).
    if product != "dataset" or not db.query(Purchase).filter_by(
            user_id=uid, product="dataset").first():
        return PlainTextResponse("Not entitled.", status_code=403)
    if not os.path.exists(settings.dataset_path):
        return PlainTextResponse("Dataset not available yet.", status_code=503)
    return FileResponse(settings.dataset_path,
                        filename=os.path.basename(settings.dataset_path),
                        media_type="application/gzip")


# --- stripe webhook ------------------------------------------------------

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        payments.handle_webhook(db, payload, sig)
    except Exception as e:  # signature failure or processing error
        logging.getLogger("commercial").error("webhook error: %s", e)
        return Response(status_code=400)
    return Response(status_code=200)
