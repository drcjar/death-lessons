"""Configuration, loaded from environment / a .env file.

No secret has a usable default — secrets are supplied on the server via
environment variables (see .env.example). The app refuses to start if a
required secret is missing in production.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",
                                      extra="ignore")

    # Core
    base_url: str = "http://localhost:8000"        # public origin of this app
    secret_key: str = "dev-insecure-change-me"     # signs sessions + tokens
    database_url: str = "sqlite:///./data/commercial.db"
    dev_mode: bool = True                          # True => log emails instead of sending

    # Email (Resend)
    resend_api_key: str = ""
    email_from: str = "deathlessons.org <noreply@deathlessons.org>"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_dataset: str = ""                 # one-off price id (dataset download)
    stripe_price_alerts: str = ""                  # recurring price id (saved-query alerts)

    # Pricing copy (display only; real amounts live in the Stripe prices above)
    price_dataset_label: str = "£49 one-off"
    price_alerts_label: str = "£19 / month"
    price_bespoke_label: str = "from £300"

    # Dataset artifact served to buyers
    dataset_path: str = "./data/deathlessons-corpus.jsonl.gz"
    download_ttl_seconds: int = 24 * 3600          # signed download link lifetime

    # Bespoke report intake notifications go here
    bespoke_inbox: str = "hello@deathlessons.org"


@lru_cache
def get_settings() -> Settings:
    return Settings()
