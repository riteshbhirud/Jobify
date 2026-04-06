# backend/app/config.py

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    openai_api_key: str = ""
    environment: str = "development"

    # Encryption key for portal passwords (Fernet)
    portal_password_key: str = ""

    # BrowserBase settings for cloud browser automation
    browserbase_api_key: Optional[str] = None
    browserbase_project_id: Optional[str] = None
    browserbase_webshare_proxy_enabled: bool = False
    browserbase_webshare_proxy_scheme: str = "http"
    browserbase_webshare_proxy_host: Optional[str] = None
    browserbase_webshare_proxy_port: Optional[int] = None
    browserbase_webshare_proxy_username: Optional[str] = None
    browserbase_webshare_proxy_password: Optional[str] = None
    browserbase_webshare_proxy_domain_pattern: Optional[str] = None
    webshare_api_key: Optional[str] = None
    webshare_proxy_mode: str = "direct"
    webshare_proxy_country_code: Optional[str] = None
    webshare_proxy_plan_id: Optional[str] = None
    local_browser_channel: Optional[str] = None
    local_browser_executable_path: Optional[str] = None
    local_browser_cdp_url: Optional[str] = None
    local_browser_persistent_profile_enabled: bool = True
    local_browser_user_data_dir: Optional[str] = None

    # Stripe settings
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""

    # Parallel processing settings
    max_concurrent_sessions: int = 5  # BrowserBase concurrent session limit
    delay_between_batches: float = 2.0  # Seconds between batch completions

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
