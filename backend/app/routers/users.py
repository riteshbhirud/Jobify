# backend/app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.auth import get_current_user
from app.database import get_supabase
from app.services.user_service import update_user_embedding, should_update_embedding, MATCHING_FIELDS

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
    # Basic info (no embedding update needed)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    phone_country_code: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None

    # Address (no embedding update needed)
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None

    # These fields WILL trigger embedding update
    target_role: Optional[str] = None
    target_type: Optional[str] = None
    locations: Optional[List[str]] = None
    remote_preference: Optional[str] = None
    experience_level: Optional[str] = None
    skills: Optional[List[str]] = None
    education: Optional[List[dict]] = None
    experience: Optional[List[dict]] = None
    projects: Optional[List[dict]] = None

    # Other fields (no embedding update needed)
    needs_visa_sponsorship: Optional[bool] = None
    min_salary: Optional[int] = None
    excluded_companies: Optional[List[str]] = None
    preferred_companies: Optional[List[str]] = None
    start_date: Optional[str] = None
    security_clearance: Optional[str] = None
    is_us_citizen: Optional[bool] = None
    willing_to_relocate: Optional[bool] = None
    military_experience: Optional[bool] = None
    demographics: Optional[dict] = None
    common_answers: Optional[dict] = None
    portal_password: Optional[str] = None
    max_daily_applications: Optional[int] = None

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
    """
    Update current user's profile.
    Automatically regenerates embedding if matching-relevant fields change.
    """

    supabase = get_supabase()

    # Filter out None values
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")

    result = supabase.table("users")\
        .update(update_data)\
        .eq("id", user.id)\
        .execute()

    # Check if we need to regenerate embedding
    embedding_updated = False
    if should_update_embedding(update_data):
        # Only regenerate if onboarding is complete
        profile = supabase.table("users")\
            .select("onboarding_completed")\
            .eq("id", user.id)\
            .single()\
            .execute()

        if profile.data.get("onboarding_completed"):
            embedding_updated = await update_user_embedding(user.id)

    return {
        "success": True,
        "data": result.data,
        "updated_fields": list(update_data.keys()),
        "embedding_updated": embedding_updated
    }


# ============================================================
# COMPLETE ONBOARDING (generates embedding)
# ============================================================

@router.post("/me/complete-onboarding")
async def complete_onboarding(user = Depends(get_current_user)):
    """
    Mark onboarding as complete and generate user embedding.
    Call this after the final onboarding step.
    """

    supabase = get_supabase()

    # Verify user has minimum required data
    result = supabase.table("users")\
        .select("target_role, skills")\
        .eq("id", user.id)\
        .single()\
        .execute()

    profile = result.data

    if not profile.get("target_role"):
        raise HTTPException(
            status_code=400,
            detail="Target role is required to complete onboarding"
        )

    if not profile.get("skills") or len(profile.get("skills", [])) < 1:
        raise HTTPException(
            status_code=400,
            detail="At least one skill is required to complete onboarding"
        )

    # Mark onboarding complete
    supabase.table("users").update({
        "onboarding_completed": True,
        "onboarding_step": 8
    }).eq("id", user.id).execute()

    # Generate embedding
    embedding_success = await update_user_embedding(user.id)

    if not embedding_success:
        # Log error but don't fail - embedding can be retried
        print(f"Warning: Embedding generation failed for user {user.id}")

    return {
        "success": True,
        "onboarding_completed": True,
        "embedding_generated": embedding_success
    }


# ============================================================
# MANUALLY REGENERATE EMBEDDING
# ============================================================

@router.post("/me/regenerate-embedding")
async def regenerate_embedding(user = Depends(get_current_user)):
    """
    Manually trigger embedding regeneration.
    Useful if embedding failed during onboarding or profile update.
    """

    supabase = get_supabase()

    # Check onboarding is complete
    result = supabase.table("users")\
        .select("onboarding_completed")\
        .eq("id", user.id)\
        .single()\
        .execute()

    if not result.data.get("onboarding_completed"):
        raise HTTPException(
            status_code=400,
            detail="Complete onboarding before generating embedding"
        )

    success = await update_user_embedding(user.id)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate embedding. Please try again."
        )

    return {"success": True, "message": "Embedding regenerated successfully"}


# ============================================================
# GET EMBEDDING STATUS
# ============================================================

@router.get("/me/embedding-status")
async def get_embedding_status(user = Depends(get_current_user)):
    """Check if user has embedding and when it was last updated."""

    supabase = get_supabase()

    result = supabase.table("users")\
        .select("embedding, embedding_updated_at, onboarding_completed")\
        .eq("id", user.id)\
        .single()\
        .execute()

    data = result.data

    return {
        "has_embedding": data.get("embedding") is not None,
        "embedding_updated_at": data.get("embedding_updated_at"),
        "onboarding_completed": data.get("onboarding_completed", False)
    }


# ============================================================
# ACTIVATION ENDPOINTS
# ============================================================

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
