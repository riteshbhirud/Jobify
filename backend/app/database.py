# backend/app/database.py

from supabase import create_client, Client
from app.config import get_settings

settings = get_settings()

def get_supabase() -> Client:
    """Service role client - bypasses RLS"""
    return create_client(settings.supabase_url, settings.supabase_service_key)

def get_supabase_anon() -> Client:
    """Anon client - respects RLS"""
    return create_client(settings.supabase_url, settings.supabase_anon_key)