"""Database models. Deliberately small — accounts, magic-link tokens,
one-off purchases, subscriptions, and saved queries (Phase 2)."""
from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.orm import relationship

from .db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    stripe_customer_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    purchases = relationship("Purchase", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")
    saved_queries = relationship("SavedQuery", back_populates="user")


class LoginToken(Base):
    """Single-use, expiring magic-link token. We store only a hash."""
    __tablename__ = "login_tokens"
    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, index=True)
    token_hash = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Purchase(Base):
    """A one-off purchase (e.g. dataset download)."""
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product = Column(String, nullable=False)            # e.g. "dataset"
    stripe_session_id = Column(String, unique=True, nullable=False)
    amount_total = Column(Integer, nullable=True)       # minor units (pence)
    currency = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="purchases")


class Subscription(Base):
    """A recurring subscription (e.g. saved-query alerts)."""
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product = Column(String, nullable=False)            # e.g. "alerts"
    stripe_subscription_id = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False)             # active, past_due, canceled...
    current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="subscriptions")

    @property
    def is_active(self) -> bool:
        return self.status in ("active", "trialing")


class SavedQuery(Base):
    """A full-text query a subscriber wants to be alerted on (Phase 2)."""
    __tablename__ = "saved_queries"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    query = Column(Text, nullable=False)
    include_responses = Column(Boolean, default=False)
    last_checked = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="saved_queries")


class SeenDoc(Base):
    """Every corpus document the alert matcher has already considered, so a
    document only ever triggers an alert once (the run after it appears)."""
    __tablename__ = "seen_docs"
    id = Column(Integer, primary_key=True)
    filename = Column(String, unique=True, index=True, nullable=False)
    first_seen = Column(DateTime, default=datetime.utcnow)


class BespokeEnquiry(Base):
    """A request for a bespoke analytical report. Custom-priced, so the flow
    is: capture brief -> scope it -> send a Stripe invoice -> mark paid."""
    __tablename__ = "bespoke_enquiries"
    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, index=True)
    brief = Column(Text, nullable=False)
    status = Column(String, default="new")              # new, invoiced, paid, done, cancelled
    stripe_invoice_id = Column(String, nullable=True, index=True)
    amount = Column(Integer, nullable=True)             # minor units (pence)
    currency = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
