# backend/app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.auth import get_current_user
from app.database import get_supabase

router = APIRouter()

# ============================================================
# MODELS
# ============================================================

class UserProfile(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    target_role: Optional[str] = None
    target_type: Optional[str] = None
    locations: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    onboarding_completed: bool = False
    onboarding_step: int = 1
    is_active: bool = False
    plan: str = "free"

class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    target_role: Optional[str] = None
    target_type: Optional[str] = None
    locations: Optional[List[str]] = None
    remote_preference: Optional[str] = None
    needs_visa_sponsorship: Optional[bool] = None
    experience_level: Optional[str] = None
    skills: Optional[List[str]] = None
    education: Optional[List[dict]] = None
    experience: Optional[List[dict]] = None

# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/me")
async def get_my_profile(user = Depends(get_current_user)):
    """Get current user's profile"""
    
    supabase = get_supabase()
    
    result = supabase.table("users")\
        .select("*")\
        .eq("id", user.id)\
        .single()\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return result.data


@router.patch("/me")
async def update_my_profile(
    data: ProfileUpdate,
    user = Depends(get_current_user)
):
    """Update current user's profile"""
    
    supabase = get_supabase()
    
    # Filter out None values
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    result = supabase.table("users")\
        .update(update_data)\
        .eq("id", user.id)\
        .execute()
    
    return {"success": True, "data": result.data}


@router.post("/me/activate")
async def activate_automation(user = Depends(get_current_user)):
    """Activate automation for user"""
    
    supabase = get_supabase()
    
    # Check if onboarding is complete
    profile = supabase.table("users")\
        .select("onboarding_completed")\
        .eq("id", user.id)\
        .single()\
        .execute()
    
    if not profile.data.get("onboarding_completed"):
        raise HTTPException(
            status_code=400, 
            detail="Please complete onboarding before activating"
        )
    
    result = supabase.table("users")\
        .update({"is_active": True})\
        .eq("id", user.id)\
        .execute()
    
    return {"success": True, "is_active": True}


@router.post("/me/deactivate")
async def deactivate_automation(user = Depends(get_current_user)):
    """Deactivate automation for user"""
    
    supabase = get_supabase()
    
    result = supabase.table("users")\
        .update({"is_active": False})\
        .eq("id", user.id)\
        .execute()
    
    return {"success": True, "is_active": False}