# backend/app/auth.py

from fastapi import Depends, HTTPException, Header
from typing import Optional
from supabase import create_client
from app.config import get_settings

settings = get_settings()

async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Verify Supabase JWT and return user.
    Frontend sends: Authorization: Bearer <access_token>
    """
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        # Create client and verify token
        supabase = create_client(settings.supabase_url, settings.supabase_anon_key)
        
        # Get user from token
        response = supabase.auth.get_user(token)
        
        if not response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return response.user
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


async def get_current_user_optional(authorization: Optional[str] = Header(None)):
    """Optional auth - returns None if not authenticated"""
    
    if not authorization:
        return None
    
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None