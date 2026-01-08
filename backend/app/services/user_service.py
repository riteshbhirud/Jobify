# backend/app/services/user_service.py

from app.database import get_supabase
from app.services.embedding import generate_user_embedding


# Fields that affect job matching - if these change, regenerate embedding
MATCHING_FIELDS = {
    'skills',
    'experience',
    'education',
    'projects',
    'target_role',
    'target_type',
    'locations',
    'experience_level',
    'remote_preference'
}


async def update_user_embedding(user_id: str) -> bool:
    """
    Generate and save user embedding.

    Call this when:
    1. User completes onboarding
    2. User updates any field in MATCHING_FIELDS
    """

    supabase = get_supabase()

    # Get full user data
    result = supabase.table("users")\
        .select("*")\
        .eq("id", user_id)\
        .single()\
        .execute()

    if not result.data:
        print(f"User {user_id} not found")
        return False

    user = result.data

    try:
        # Generate embedding
        embedding = await generate_user_embedding(user)

        # Save to database
        supabase.table("users").update({
            "embedding": embedding,
            "embedding_updated_at": "now()"
        }).eq("id", user_id).execute()

        print(f"Embedding updated for user {user_id}")
        return True

    except Exception as e:
        print(f"Error generating embedding for user {user_id}: {e}")
        return False


def should_update_embedding(updated_fields: dict) -> bool:
    """Check if any matching-relevant fields were updated."""
    return bool(MATCHING_FIELDS.intersection(updated_fields.keys()))
