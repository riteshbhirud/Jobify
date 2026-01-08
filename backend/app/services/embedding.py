# backend/app/services/embedding.py

import openai
from typing import List
from app.config import get_settings

settings = get_settings()
client = openai.AsyncOpenAI(api_key=settings.openai_api_key)


async def get_embedding(text: str) -> List[float]:
    """
    Generate embedding vector using OpenAI.
    Returns a list of 1536 floats.
    """

    # Clean text
    text = text.replace("\n", " ").strip()
    if not text:
        text = "empty"

    # Truncate to avoid token limits (max ~8000 chars to be safe)
    text = text[:8000]

    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
        dimensions=1536
    )

    return response.data[0].embedding


async def generate_user_embedding(user: dict) -> List[float]:
    """
    Generate embedding for a user profile.

    This creates a text representation of the user's profile
    and converts it to a vector for similarity matching.
    """

    parts = []

    # Target role (most important for matching)
    if user.get("target_role"):
        parts.append(f"Looking for: {user['target_role']}")

    # Job type preference
    target_type = user.get("target_type", "both")
    if target_type == "internship":
        parts.append("Seeking internship positions")
    elif target_type == "full_time":
        parts.append("Seeking full-time positions")

    # Skills (very important for matching)
    skills = user.get("skills", [])
    if skills:
        parts.append(f"Skills: {', '.join(skills[:25])}")

    # Experience
    experience = user.get("experience", [])
    if experience:
        exp_parts = []
        for exp in experience[:3]:
            title = exp.get("title", "")
            company = exp.get("company", "")
            bullets = exp.get("bullets", [])

            if title or company:
                exp_text = f"{title} at {company}"
                if bullets:
                    exp_text += f" - {'; '.join(bullets[:2])}"
                exp_parts.append(exp_text)

        if exp_parts:
            parts.append(f"Experience: {' | '.join(exp_parts)}")

    # Education
    education = user.get("education", [])
    if education:
        # Get current education first, or most recent
        current_edu = next(
            (e for e in education if e.get("current")),
            education[0]
        )
        degree = current_edu.get("degree", "")
        discipline = current_edu.get("discipline", "")
        school = current_edu.get("school", "")
        parts.append(f"Education: {degree} in {discipline} from {school}")

    # Experience level
    if user.get("experience_level"):
        parts.append(f"Experience level: {user['experience_level']}")

    # Location preferences
    locations = user.get("locations", [])
    if locations:
        parts.append(f"Preferred locations: {', '.join(locations[:5])}")

    # Remote preference
    remote_pref = user.get("remote_preference")
    if remote_pref and remote_pref != "any":
        pref_map = {
            "remote": "Prefers remote work",
            "hybrid": "Open to hybrid work",
            "onsite": "Prefers on-site work"
        }
        parts.append(pref_map.get(remote_pref, ""))

    # Projects (if notable)
    projects = user.get("projects", [])
    if projects:
        proj_parts = []
        for proj in projects[:2]:
            name = proj.get("name", "")
            technologies = proj.get("technologies", [])
            if name:
                proj_text = name
                if technologies:
                    proj_text += f" ({', '.join(technologies[:3])})"
                proj_parts.append(proj_text)
        if proj_parts:
            parts.append(f"Projects: {', '.join(proj_parts)}")

    # Combine all parts
    embedding_text = " | ".join(filter(None, parts))

    # Fallback if empty
    if not embedding_text:
        embedding_text = user.get("target_role", "software engineer")

    # Debug logging - show exactly what's being used for embedding
    print("\n" + "=" * 60)
    print("EMBEDDING GENERATION DEBUG")
    print("=" * 60)
    print(f"User ID: {user.get('id', 'unknown')}")
    print(f"Email: {user.get('email', 'unknown')}")
    print("-" * 60)
    print("EXTRACTED PARTS:")
    for i, part in enumerate(parts, 1):
        print(f"  {i}. {part}")
    print("-" * 60)
    print("FULL EMBEDDING TEXT:")
    print(embedding_text)
    print("-" * 60)
    print(f"Character count: {len(embedding_text)}")
    print("=" * 60 + "\n")

    return await get_embedding(embedding_text)
