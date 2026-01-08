# backend/app/database.py

from supabase import create_client, Client
from app.config import get_settings
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

def get_supabase() -> Client:
    """Service role client - bypasses RLS"""
    # Debug: Check if service key is loaded (print first 20 chars only for security)
    logger.info(f"Service key loaded: {settings.supabase_service_key[:20]}...")
    return create_client(settings.supabase_url, settings.supabase_service_key)

def get_supabase_anon() -> Client:
    """Anon client - respects RLS"""
    return create_client(settings.supabase_url, settings.supabase_anon_key)