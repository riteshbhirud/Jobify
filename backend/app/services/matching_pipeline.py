# backend/app/services/matching_pipeline.py

"""
Matching Pipeline Service

This service handles the complete flow of:
1. Matching all active users to their top N job matches
2. Creating application records for each match
3. Queueing applications for automation
4. Processing the queue in batches via BrowserBase

Can be run manually via API or scheduled periodically.
"""

import asyncio
import logging
import math
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from app.database import get_supabase
from app.config import get_settings
from app.services.automation_service import (
    run_application_pipeline,
    detect_ats_platform,
    is_browserbase_configured
)

# Get settings for parallel processing
settings = get_settings()
MAX_CONCURRENT_SESSIONS = settings.max_concurrent_sessions
DELAY_BETWEEN_BATCHES = settings.delay_between_batches

logger = logging.getLogger(__name__)


def cosine_similarity(vec1, vec2) -> float:
    """
    Calculate cosine similarity between two vectors.
    Handles both list and string formats (from Supabase vector type).
    """
    # Parse string embeddings if needed
    if isinstance(vec1, str):
        try:
            vec1 = json.loads(vec1)
        except:
            return 0.0

    if isinstance(vec2, str):
        try:
            vec2 = json.loads(vec2)
        except:
            return 0.0

    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


# Metro area mappings for location expansion
METRO_AREAS = {
    "sf bay area": ["san francisco", "san jose", "oakland", "palo alto", "mountain view",
                   "sunnyvale", "santa clara", "fremont", "redwood city", "menlo park",
                   "cupertino", "berkeley", "san mateo", "hayward", "south san francisco"],
    "nyc metro": ["new york", "manhattan", "brooklyn", "queens", "jersey city",
                  "hoboken", "newark", "stamford"],
    "la metro": ["los angeles", "santa monica", "pasadena", "burbank", "long beach",
                 "glendale", "culver city", "irvine", "anaheim"],
    "seattle metro": ["seattle", "bellevue", "redmond", "kirkland", "tacoma"],
    "boston metro": ["boston", "cambridge", "somerville", "brookline", "quincy"],
    "chicago metro": ["chicago", "evanston", "oak park", "naperville", "schaumburg"],
    "dc metro": ["washington", "arlington", "alexandria", "bethesda", "silver spring"],
    "austin metro": ["austin", "round rock", "cedar park", "georgetown"],
    "denver metro": ["denver", "boulder", "aurora", "lakewood", "littleton"],
}

# Experience level ordering for comparison (unified for both user and job formats)
EXPERIENCE_LEVELS = {
    # User profile formats
    "entry": 0,
    "junior": 1,
    "mid": 2,
    "mid-level": 2,
    "senior": 3,
    "lead": 4,
    "principal": 5,
    "staff": 5,
    "director": 6,
    "executive": 7,
    # Job listing formats (years of experience)
    "0-2": 0,      # Entry level
    "2-5": 2,      # Mid level
    "5-10": 3,     # Senior level
    "10+": 4,      # Lead/Principal level
}

# Role categories for matching specializations
ROLE_CATEGORIES = {
    "ml_ai": [
        "machine learning", "ml engineer", "deep learning", "artificial intelligence",
        "ai engineer", "nlp", "computer vision", "neural network", "llm", "generative ai"
    ],
    "data_science": [
        "data scientist", "data science", "data analyst", "analytics", "statistician",
        "business intelligence", "bi analyst"
    ],
    "research": [
        "research scientist", "research engineer", "researcher", "applied scientist",
        "research intern"
    ],
    "frontend": [
        "frontend", "front-end", "front end", "ui engineer", "ui developer",
        "react developer", "vue developer", "angular developer"
    ],
    "backend": [
        "backend", "back-end", "back end", "server engineer", "api engineer",
        "platform engineer", "infrastructure engineer"
    ],
    "fullstack": [
        "full stack", "fullstack", "full-stack"
    ],
    "devops_infra": [
        "devops", "sre", "site reliability", "infrastructure", "platform",
        "cloud engineer", "systems engineer"
    ],
    "mobile": [
        "mobile engineer", "ios engineer", "android engineer", "mobile developer"
    ],
    "embedded": [
        "embedded", "firmware", "hardware engineer", "systems programming"
    ],
    "security": [
        "security engineer", "cybersecurity", "appsec", "infosec"
    ],
}


def get_role_category(text: str) -> Optional[str]:
    """Determine the role category from title or description text."""
    if not text:
        return None
    text_lower = text.lower()
    for category, keywords in ROLE_CATEGORIES.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "general"


def calculate_skill_match(user_skills: List[str], job_description: str, job_title: str) -> tuple[float, List[str]]:
    """
    Calculate how many user skills appear in the job posting.
    Returns (score, list of matched skills).
    """
    if not user_skills:
        return 0.0, []

    # Combine job title and description for matching
    job_text = f"{job_title} {job_description}".lower() if job_description else job_title.lower()

    matched_skills = []
    for skill in user_skills:
        skill_lower = skill.lower()
        # Check for exact match or common variations
        if skill_lower in job_text:
            matched_skills.append(skill)
        # Handle multi-word skills
        elif len(skill_lower.split()) > 1 and all(word in job_text for word in skill_lower.split()):
            matched_skills.append(skill)

    # Score based on percentage of skills matched (max 10% bonus)
    match_ratio = len(matched_skills) / min(len(user_skills), 10)  # Cap at 10 skills
    score = min(match_ratio * 0.12, 0.10)  # Max 10% bonus

    return score, matched_skills


def calculate_role_category_match(
    job_title: str,
    job_description: str,
    user_target_role: str,
    user_skills: List[str]
) -> tuple[float, str, str, bool]:
    """
    Compare role categories between job and user preference.
    Returns (score_adjustment, job_category, user_category, is_match).

    - Strong match: +10% bonus
    - Mismatch: -8% penalty
    - Unknown/general: no adjustment
    """
    # Determine job category
    job_category = get_role_category(job_title)
    if job_category == "general" and job_description:
        job_category = get_role_category(job_description)

    # Determine user's target category
    user_category = get_role_category(user_target_role)
    if user_category == "general" and user_skills:
        # Infer from skills
        skills_text = " ".join(user_skills)
        user_category = get_role_category(skills_text)

    # Both general = no adjustment
    if job_category == "general" or user_category == "general":
        return 0.0, job_category or "general", user_category or "general", True

    # Exact match = bonus
    if job_category == user_category:
        return 0.10, job_category, user_category, True

    # Related categories (partial match)
    related_pairs = [
        ("ml_ai", "data_science"),
        ("ml_ai", "research"),
        ("data_science", "research"),
        ("frontend", "fullstack"),
        ("backend", "fullstack"),
        ("backend", "devops_infra"),
    ]
    for pair in related_pairs:
        if (job_category in pair and user_category in pair):
            return 0.05, job_category, user_category, True  # Partial match

    # Mismatch = penalty
    return -0.08, job_category, user_category, False


def normalize_experience_level(level: str) -> int:
    """Convert experience level string to numeric value for comparison."""
    if not level:
        return 2  # Default to mid-level if unknown
    level_lower = level.lower().strip()
    return EXPERIENCE_LEVELS.get(level_lower, 2)


def get_metro_area_matches(location: str) -> list:
    """Get all cities that match a given location (including metro area expansion)."""
    location_lower = location.lower()
    matches = [location_lower]

    # Check if location is in a metro area
    for metro, cities in METRO_AREAS.items():
        if any(city in location_lower for city in cities):
            matches.extend(cities)
            break

    return list(set(matches))


def calculate_title_similarity(job_title: str, target_role: str) -> float:
    """Calculate similarity between job title and user's target role."""
    if not job_title or not target_role:
        return 0.0

    job_words = set(job_title.lower().replace("-", " ").split())
    target_words = set(target_role.lower().replace("-", " ").split())

    # Remove common filler words
    filler_words = {"the", "a", "an", "and", "or", "of", "for", "at", "in", "to", "i", "ii", "iii", "iv", "v"}
    job_words -= filler_words
    target_words -= filler_words

    if not job_words or not target_words:
        return 0.0

    # Calculate Jaccard similarity
    intersection = len(job_words & target_words)
    union = len(job_words | target_words)

    return intersection / union if union > 0 else 0.0


def calculate_match_score(
    job: Dict,
    user: Dict,
    similarity: float,
    user_skills: Optional[List[str]] = None
) -> tuple[float, Dict]:
    """
    Calculate comprehensive match score between job and user.
    Returns (score, reasons).

    Scoring breakdown:
    - Embedding similarity: 50% weight (semantic match)
    - Role category match: up to 10% bonus / -8% penalty
    - Skill match: up to 10% bonus
    - Preference bonuses: up to 20% (location, remote, company, title, salary)
    - Experience match: up to 8% bonus / -12% penalty
    - Hard filters eliminate jobs entirely (return 0)
    """
    reasons = {
        "embedding_similarity": round(similarity, 3),
        "filters_passed": [],
        "filters_failed": [],
        "preference_matches": [],
        "penalties": [],
        "bonuses": {}
    }

    filters_passed = True

    # ============== HARD FILTERS ==============

    # Job type check (internship vs full_time)
    user_target_type = user.get("target_type", "both")
    job_employment_type = (job.get("employment_type") or "").upper()

    if user_target_type == "internship":
        # User wants internship - job must have INTERN in employment_type
        if "INTERN" not in job_employment_type:
            reasons["filters_failed"].append(f"User seeking internship but job is {job_employment_type or 'unknown type'}")
            filters_passed = False
    elif user_target_type == "full_time":
        # User wants full-time - job must have FULL_TIME and NOT be intern-only
        if "FULL_TIME" not in job_employment_type or job_employment_type == "INTERN":
            reasons["filters_failed"].append(f"User seeking full-time but job is {job_employment_type or 'unknown type'}")
            filters_passed = False
    # If target_type is "both", no filtering needed

    # Visa sponsorship check
    if user.get("needs_visa_sponsorship") and job.get("visa_sponsorship") is False:
        reasons["filters_failed"].append("Requires visa sponsorship but job doesn't offer it")
        filters_passed = False

    # Minimum salary check (hard filter)
    user_min_salary = user.get("min_salary")
    job_max_salary = job.get("salary_max")
    if user_min_salary and job_max_salary and job_max_salary < user_min_salary:
        reasons["filters_failed"].append(f"Salary below minimum")
        filters_passed = False

    # Excluded companies check
    excluded_companies = user.get("excluded_companies") or []
    if excluded_companies and job.get("company"):
        job_company_lower = job.get("company", "").lower()
        for excluded in excluded_companies:
            if excluded.lower() in job_company_lower:
                reasons["filters_failed"].append(f"Company in excluded list")
                filters_passed = False
                break

    if not filters_passed:
        return 0.0, reasons

    # ============== SOFT SCORING ==============

    preference_score = 0.0
    penalty_score = 0.0

    # ============== ROLE CATEGORY MATCHING ==============

    job_title = job.get("title", "")
    job_description = job.get("description", "")
    user_target_role = user.get("target_role", "")

    role_adjustment, job_category, user_category, role_matched = calculate_role_category_match(
        job_title=job_title,
        job_description=job_description,
        user_target_role=user_target_role,
        user_skills=user_skills or []
    )

    if role_adjustment > 0:
        preference_score += role_adjustment
        reasons["preference_matches"].append(f"Role category match: {user_category}")
        reasons["bonuses"]["role_category"] = role_adjustment
    elif role_adjustment < 0:
        penalty_score += abs(role_adjustment)
        reasons["penalties"].append(f"Role mismatch: user wants {user_category}, job is {job_category}")

    reasons["role_category"] = {
        "job": job_category,
        "user": user_category,
        "matched": role_matched
    }

    # ============== SKILL MATCHING ==============

    if user_skills:
        skill_score, matched_skills = calculate_skill_match(
            user_skills=user_skills,
            job_description=job_description,
            job_title=job_title
        )
        if skill_score > 0:
            preference_score += skill_score
            reasons["preference_matches"].append(f"Skills matched: {len(matched_skills)} skills")
            reasons["bonuses"]["skill_match"] = round(skill_score, 3)
            reasons["matched_skills"] = matched_skills[:5]  # Top 5 for brevity

    # ----- 1. Remote preference (single bonus, no double-counting) -----
    user_remote_pref = user.get("remote_preference", "any")
    job_remote_type = (job.get("remote_type") or "").lower()
    job_location_lower = (job.get("location") or "").lower()
    remote_bonus_applied = False

    is_remote_job = "remote" in job_remote_type or "remote" in job_location_lower

    if user_remote_pref == "remote":
        if is_remote_job:
            preference_score += 0.08
            reasons["preference_matches"].append("Remote job matches preference")
            reasons["bonuses"]["remote_match"] = 0.08
            remote_bonus_applied = True
        elif "on-site" in job_remote_type or "onsite" in job_remote_type:
            penalty_score += 0.10
            reasons["penalties"].append("On-site only job (user prefers remote)")
    elif user_remote_pref == "hybrid":
        if "hybrid" in job_remote_type:
            preference_score += 0.05
            reasons["preference_matches"].append("Hybrid job matches preference")
            reasons["bonuses"]["hybrid_match"] = 0.05

    # ----- 2. Preferred companies -----
    preferred_companies = user.get("preferred_companies") or []
    if preferred_companies and job.get("company"):
        job_company_lower = job.get("company", "").lower()
        for preferred in preferred_companies:
            if preferred.lower() in job_company_lower:
                preference_score += 0.08
                reasons["preference_matches"].append(f"Preferred company: {job.get('company')}")
                reasons["bonuses"]["preferred_company"] = 0.08
                break

    # ----- 3. Location matching (skip remote bonus if already applied) -----
    user_locations = user.get("locations") or []
    job_location_raw = job.get("location") or ""
    location_matched = False

    # Only apply remote location bonus if not already applied via remote_preference
    if not remote_bonus_applied:
        user_wants_remote_location = any("remote" in loc.lower() for loc in user_locations)
        if user_wants_remote_location and is_remote_job:
            preference_score += 0.05
            reasons["preference_matches"].append("Remote job (user has Remote in locations)")
            reasons["bonuses"]["remote_location"] = 0.05
            location_matched = True

    if not location_matched and user_locations and job_location_raw:
        job_location_lower = job_location_raw.lower()

        for loc in user_locations:
            if "remote" in loc.lower():
                continue  # Already handled above

            # Expand user location to metro area
            metro_matches = get_metro_area_matches(loc)

            for metro_city in metro_matches:
                if metro_city in job_location_lower:
                    preference_score += 0.05
                    if metro_city != loc.lower():
                        reasons["preference_matches"].append(f"Metro area match: {loc} area")
                    else:
                        reasons["preference_matches"].append(f"Location: {loc}")
                    reasons["bonuses"]["location"] = 0.05
                    location_matched = True
                    break
            if location_matched:
                break

    # ----- 4. Job title similarity bonus (increased weight) -----
    # Note: user_target_role and job_title already defined above in role category section

    if user_target_role and job_title:
        title_sim = calculate_title_similarity(job_title, user_target_role)
        if title_sim >= 0.5:
            bonus = min(title_sim * 0.15, 0.12)  # Max 12% bonus (up from 8%)
            preference_score += bonus
            reasons["preference_matches"].append(f"Title similarity: {title_sim:.0%}")
            reasons["bonuses"]["title_similarity"] = round(bonus, 3)
        elif title_sim >= 0.25:
            bonus = title_sim * 0.08  # Increased from 0.05
            preference_score += bonus
            reasons["preference_matches"].append(f"Partial title match: {title_sim:.0%}")
            reasons["bonuses"]["title_similarity"] = round(bonus, 3)

    # ----- 5. Experience level match (softened penalties) -----
    user_exp_level = user.get("experience_level", "")
    job_exp_level = job.get("experience_level", "")

    if user_exp_level and job_exp_level:
        user_exp_num = normalize_experience_level(user_exp_level)
        job_exp_num = normalize_experience_level(job_exp_level)
        exp_diff = job_exp_num - user_exp_num

        if exp_diff == 0:
            # Perfect match
            preference_score += 0.08
            reasons["preference_matches"].append(f"Experience level match: {job_exp_level}")
            reasons["bonuses"]["experience_match"] = 0.08
        elif exp_diff == 1:
            # Job is one level higher - slight stretch, small bonus
            preference_score += 0.03
            reasons["preference_matches"].append(f"Stretch role (+1 level)")
            reasons["bonuses"]["experience_stretch"] = 0.03
        elif exp_diff == -1:
            # Job is one level lower - reduced penalty
            penalty_score += 0.03  # Reduced from 0.05
            reasons["penalties"].append(f"Job slightly below level ({job_exp_level} vs {user_exp_level})")
        elif exp_diff >= 2:
            # Job requires much more experience - graduated penalty
            penalty = 0.06 + min((exp_diff - 2) * 0.03, 0.06)  # Max -12%
            penalty_score += penalty
            reasons["penalties"].append(f"Job requires more experience ({job_exp_level} vs {user_exp_level})")
        elif exp_diff <= -2:
            # Job is significantly below user level - graduated penalty
            penalty = 0.05 + min((abs(exp_diff) - 2) * 0.02, 0.05)  # Max -10%
            penalty_score += penalty
            reasons["penalties"].append(f"Job significantly below level ({job_exp_level} vs {user_exp_level})")

    # ----- 6. Salary fit bonus -----
    job_min_salary = job.get("salary_min")
    job_max_salary = job.get("salary_max")
    user_min_salary = user.get("min_salary")

    if user_min_salary and (job_min_salary or job_max_salary):
        # If job min salary is >= user min, that's a good sign
        if job_min_salary and job_min_salary >= user_min_salary:
            preference_score += 0.05
            reasons["preference_matches"].append("Salary floor meets expectations")
            reasons["bonuses"]["salary_fit"] = 0.05
        elif job_max_salary and job_max_salary >= user_min_salary * 1.2:
            # Job max is significantly above user min - good potential
            preference_score += 0.03
            reasons["preference_matches"].append("Salary range has good potential")
            reasons["bonuses"]["salary_potential"] = 0.03

    # ============== FINAL SCORE CALCULATION ==============

    # Cap preference bonuses (increased cap to accommodate new signals)
    preference_score = min(preference_score, 0.35)

    # Calculate final score: 50% embedding + bonuses - penalties
    final_score = (similarity * 0.50) + preference_score - penalty_score

    # Ensure score is in valid range
    final_score = max(0.0, min(1.0, final_score))

    # Add summary to reasons
    reasons["preference_bonus"] = round(preference_score, 3)
    reasons["penalty_total"] = round(penalty_score, 3)
    reasons["final_score_breakdown"] = {
        "embedding_contribution": round(similarity * 0.50, 3),
        "preference_bonus": round(preference_score, 3),
        "penalty": round(penalty_score, 3)
    }

    return final_score, reasons


async def match_user_to_jobs(
    user: Dict,
    jobs: List[Dict],
    top_n: int = 3,
    min_score: float = 0.3
) -> List[Dict]:
    """
    Match a single user to their top N jobs.
    Returns list of match packages with user details, job details, and scores.
    """
    user_embedding = user.get("embedding")
    if not user_embedding:
        return []

    # Extract user skills for skill matching
    user_skills = user.get("skills") or []
    if isinstance(user_skills, str):
        user_skills = [s.strip() for s in user_skills.split(",")]

    matches = []

    for job in jobs:
        job_embedding = job.get("embedding")
        if not job_embedding:
            continue

        # Check if job URL is supported for automation
        apply_url = job.get("apply_url")
        platform = detect_ats_platform(apply_url)
        if not platform:
            continue  # Skip unsupported platforms

        # Calculate similarity and match score
        similarity = cosine_similarity(user_embedding, job_embedding)
        match_score, match_reasons = calculate_match_score(
            job, user, similarity, user_skills=user_skills
        )

        if match_score >= min_score:
            matches.append({
                "job_id": job["id"],
                "job_title": job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "apply_url": apply_url,
                "platform": platform,
                "match_score": match_score,
                "match_reasons": match_reasons
            })

    # Sort by score and take top N
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    return matches[:top_n]


async def run_matching_pipeline(
    top_matches_per_user: int = 3,
    min_match_score: float = 0.3,
    auto_queue: bool = True,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the full matching pipeline:
    1. Fetch all active users with embeddings
    2. Fetch all jobs with embeddings
    3. Match each user to top N jobs
    4. Create application records
    5. Optionally queue for automation

    Args:
        top_matches_per_user: Number of top matches per user
        min_match_score: Minimum match score threshold
        auto_queue: If True, automatically queue matches for automation
        user_id: Optional specific user ID (otherwise all active users)

    Returns:
        Summary of matching results
    """
    supabase = get_supabase()
    logger.info("Starting matching pipeline...")

    # Fetch users (including skills and target_role for improved matching)
    users_query = supabase.table("users").select(
        "id, email, first_name, last_name, embedding, min_match_score, "
        "needs_visa_sponsorship, min_salary, excluded_companies, preferred_companies, "
        "locations, remote_preference, experience_level, target_type, target_role, "
        "skills, is_active"
    ).not_.is_("embedding", "null")

    if user_id:
        users_query = users_query.eq("id", user_id)
    else:
        users_query = users_query.eq("is_active", True)

    users_result = users_query.execute()
    users = users_result.data or []

    if not users:
        return {
            "success": True,
            "message": "No active users with embeddings found",
            "users_processed": 0,
            "total_matches": 0,
            "total_queued": 0
        }

    logger.info(f"Found {len(users)} user(s) to process")

    # Fetch jobs with embeddings (including description for skill matching)
    jobs_result = supabase.table("jobs").select(
        "id, external_id, title, company, location, apply_url, description, "
        "salary_min, salary_max, visa_sponsorship, remote_type, "
        "experience_level, employment_type, embedding"
    ).not_.is_("embedding", "null").execute()

    jobs = jobs_result.data or []

    if not jobs:
        return {
            "success": True,
            "message": "No jobs with embeddings found",
            "users_processed": 0,
            "total_matches": 0,
            "total_queued": 0
        }

    logger.info(f"Found {len(jobs)} job(s) to match against")

    # Process each user
    all_matches = []
    user_summaries = []

    for user in users:
        user_min_score = min_match_score or user.get("min_match_score", 0.3)

        # Get existing applications to avoid duplicates
        existing_result = supabase.table("applications").select("job_id").eq("user_id", user["id"]).execute()
        existing_job_ids = {app["job_id"] for app in (existing_result.data or [])}

        # Filter out jobs user already applied to
        available_jobs = [j for j in jobs if j["id"] not in existing_job_ids]

        # Match user to top jobs
        matches = await match_user_to_jobs(
            user=user,
            jobs=available_jobs,
            top_n=top_matches_per_user,
            min_score=user_min_score
        )

        user_summary = {
            "user_id": user["id"],
            "email": user.get("email"),
            "matches_found": len(matches),
            "matches": []
        }

        for match in matches:
            match_package = {
                "user_id": user["id"],
                "user_email": user.get("email"),
                "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                **match
            }
            all_matches.append(match_package)
            user_summary["matches"].append({
                "job_title": match["job_title"],
                "company": match["company"],
                "match_score": round(match["match_score"], 3),
                "platform": match["platform"]
            })

        user_summaries.append(user_summary)
        logger.info(f"User {user.get('email')}: found {len(matches)} matches")

    logger.info(f"Total matches found: {len(all_matches)}")

    # Create application records and optionally queue
    created_count = 0
    queued_count = 0
    errors = []

    for match in all_matches:
        try:
            # Check for existing application
            existing = supabase.table("applications").select("id").eq(
                "user_id", match["user_id"]
            ).eq("job_id", match["job_id"]).execute()

            if existing.data:
                logger.debug(f"Application already exists for user {match['user_id']}, job {match['job_id']}")
                continue

            # Create application record
            application_data = {
                "user_id": match["user_id"],
                "job_id": match["job_id"],
                "match_score": match["match_score"],
                "match_reasons": match["match_reasons"],
                "status": "queued" if auto_queue else "matched",
                "matched_at": datetime.now(timezone.utc).isoformat(),
            }

            if auto_queue:
                application_data["queued_at"] = datetime.now(timezone.utc).isoformat()

            result = supabase.table("applications").insert(application_data).execute()

            if result.data:
                created_count += 1
                if auto_queue:
                    queued_count += 1

        except Exception as e:
            error_msg = str(e)
            if "duplicate" not in error_msg.lower():
                errors.append(f"Error for user {match['user_id']}, job {match['job_id']}: {error_msg}")
                logger.error(error_msg)

    return {
        "success": True,
        "message": f"Matching pipeline completed. Created {created_count} applications, {queued_count} queued.",
        "users_processed": len(users),
        "jobs_evaluated": len(jobs),
        "total_matches_found": len(all_matches),
        "applications_created": created_count,
        "applications_queued": queued_count,
        "auto_queue_enabled": auto_queue,
        "user_summaries": user_summaries,
        "errors": errors if errors else None
    }


async def process_application_queue(
    user_id: Optional[str] = None,
    limit: int = 10,
    dry_run: bool = False,
    use_browserbase: bool = True,
    delay_between_apps: float = 5.0,
    generate_cover_letter: bool = False
) -> Dict[str, Any]:
    """
    Process queued applications by running automation pipelines.

    Args:
        user_id: Optional specific user ID
        limit: Maximum applications to process
        dry_run: If True, fill forms but don't submit
        use_browserbase: If True, use BrowserBase cloud browsers
        delay_between_apps: Seconds to wait between applications
        generate_cover_letter: If True, generate tailored cover letter for each application

    Returns:
        Processing results summary
    """
    supabase = get_supabase()
    logger.info(f"Processing application queue (limit: {limit}, dry_run: {dry_run})")

    # Fetch queued applications
    query = supabase.table("applications").select(
        "id, user_id, job_id, match_score, "
        "jobs(title, company, apply_url)"
    ).eq("status", "queued").order("match_score", desc=True).limit(limit)

    if user_id:
        query = query.eq("user_id", user_id)

    result = query.execute()
    applications = result.data or []

    if not applications:
        return {
            "success": True,
            "message": "No queued applications found",
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "results": []
        }

    logger.info(f"Found {len(applications)} queued applications to process")

    results = []
    successful = 0
    failed = 0

    for i, app in enumerate(applications):
        job = app.get("jobs", {})
        logger.info(f"Processing {i+1}/{len(applications)}: {job.get('title')} at {job.get('company')}")

        try:
            app_result = await run_application_pipeline(
                user_id=app["user_id"],
                job_id=app["job_id"],
                application_id=app["id"],
                dry_run=dry_run,
                use_browserbase=use_browserbase,
                generate_cover_letter_flag=generate_cover_letter
            )

            results.append({
                "application_id": app["id"],
                "job_title": job.get("title"),
                "company": job.get("company"),
                "match_score": app.get("match_score"),
                **app_result
            })

            if app_result.get("success"):
                successful += 1
            else:
                failed += 1

        except Exception as e:
            logger.error(f"Error processing application {app['id']}: {e}")
            failed += 1
            results.append({
                "application_id": app["id"],
                "job_title": job.get("title"),
                "company": job.get("company"),
                "success": False,
                "error": str(e)
            })

        # Delay between applications to avoid rate limiting
        if i < len(applications) - 1:
            logger.info(f"Waiting {delay_between_apps}s before next application...")
            await asyncio.sleep(delay_between_apps)

    return {
        "success": True,
        "message": f"Processed {len(applications)} applications: {successful} successful, {failed} failed",
        "processed": len(applications),
        "successful": successful,
        "failed": failed,
        "dry_run": dry_run,
        "used_browserbase": use_browserbase and is_browserbase_configured(),
        "results": results
    }


async def process_application_queue_parallel(
    user_id: Optional[str] = None,
    limit: int = 50,
    dry_run: bool = False,
    use_browserbase: bool = True,
    max_concurrent: Optional[int] = None,
    generate_cover_letter: bool = False
) -> Dict[str, Any]:
    """
    Process queued applications in parallel using BrowserBase concurrent sessions.

    Uses asyncio.Semaphore to limit concurrent browser sessions to avoid
    overwhelming BrowserBase and to stay within plan limits.

    Args:
        user_id: Optional specific user ID
        limit: Maximum applications to process
        dry_run: If True, fill forms but don't submit
        use_browserbase: If True, use BrowserBase cloud browsers
        max_concurrent: Max concurrent sessions (defaults to config value)
        generate_cover_letter: If True, generate tailored cover letter for each application

    Returns:
        Processing results summary
    """
    supabase = get_supabase()
    concurrent_limit = max_concurrent or MAX_CONCURRENT_SESSIONS

    logger.info(f"Starting PARALLEL application queue processing")
    logger.info(f"  - Limit: {limit} applications")
    logger.info(f"  - Max concurrent sessions: {concurrent_limit}")
    logger.info(f"  - Dry run: {dry_run}")

    # Fetch queued applications
    query = supabase.table("applications").select(
        "id, user_id, job_id, match_score, "
        "jobs(title, company, apply_url)"
    ).eq("status", "queued").order("match_score", desc=True).limit(limit)

    if user_id:
        query = query.eq("user_id", user_id)

    result = query.execute()
    applications = result.data or []

    if not applications:
        return {
            "success": True,
            "message": "No queued applications found",
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "parallel_mode": True,
            "max_concurrent": concurrent_limit,
            "results": []
        }

    logger.info(f"Found {len(applications)} queued applications to process in parallel")

    # Semaphore to limit concurrent sessions
    semaphore = asyncio.Semaphore(concurrent_limit)

    # Track results thread-safely
    results_lock = asyncio.Lock()
    results = []
    successful = 0
    failed = 0

    async def process_single_application(app: Dict, worker_id: int) -> Dict:
        """Process a single application with semaphore limiting."""
        nonlocal successful, failed

        job = app.get("jobs", {})
        job_title = job.get("title", "Unknown")
        company = job.get("company", "Unknown")

        async with semaphore:
            logger.info(f"[Worker {worker_id}] Starting: {job_title} at {company}")
            start_time = datetime.now(timezone.utc)

            try:
                app_result = await run_application_pipeline(
                    user_id=app["user_id"],
                    job_id=app["job_id"],
                    application_id=app["id"],
                    dry_run=dry_run,
                    use_browserbase=use_browserbase,
                    worker_id=worker_id,
                    generate_cover_letter_flag=generate_cover_letter
                )

                duration = (datetime.now(timezone.utc) - start_time).total_seconds()

                result_data = {
                    "application_id": app["id"],
                    "job_title": job_title,
                    "company": company,
                    "match_score": app.get("match_score"),
                    "worker_id": worker_id,
                    "duration_seconds": round(duration, 1),
                    **app_result
                }

                async with results_lock:
                    results.append(result_data)
                    if app_result.get("success"):
                        successful += 1
                        logger.info(f"[Worker {worker_id}] SUCCESS: {job_title} at {company} ({duration:.1f}s)")
                    else:
                        failed += 1
                        logger.warning(f"[Worker {worker_id}] FAILED: {job_title} - {app_result.get('error', 'Unknown error')}")

                # Small delay after completing to avoid rate limiting
                await asyncio.sleep(DELAY_BETWEEN_BATCHES)

                return result_data

            except Exception as e:
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                error_msg = str(e)
                logger.error(f"[Worker {worker_id}] ERROR processing {job_title}: {error_msg}")

                result_data = {
                    "application_id": app["id"],
                    "job_title": job_title,
                    "company": company,
                    "match_score": app.get("match_score"),
                    "worker_id": worker_id,
                    "duration_seconds": round(duration, 1),
                    "success": False,
                    "error": error_msg
                }

                async with results_lock:
                    results.append(result_data)
                    failed += 1

                return result_data

    # Create all tasks with worker IDs
    tasks = [
        process_single_application(app, worker_id=i)
        for i, app in enumerate(applications)
    ]

    logger.info(f"Launching {len(tasks)} tasks with {concurrent_limit} concurrent workers...")
    pipeline_start = datetime.now(timezone.utc)

    # Run all tasks concurrently (semaphore limits actual concurrency)
    await asyncio.gather(*tasks, return_exceptions=True)

    pipeline_duration = (datetime.now(timezone.utc) - pipeline_start).total_seconds()

    # Sort results by worker_id for consistent output
    results.sort(key=lambda x: x.get("worker_id", 0))

    logger.info(f"Parallel processing complete:")
    logger.info(f"  - Total: {len(applications)}")
    logger.info(f"  - Successful: {successful}")
    logger.info(f"  - Failed: {failed}")
    logger.info(f"  - Duration: {pipeline_duration:.1f}s")
    logger.info(f"  - Avg per app: {pipeline_duration/len(applications):.1f}s")

    return {
        "success": True,
        "message": f"Processed {len(applications)} applications in parallel: {successful} successful, {failed} failed",
        "processed": len(applications),
        "successful": successful,
        "failed": failed,
        "dry_run": dry_run,
        "parallel_mode": True,
        "max_concurrent": concurrent_limit,
        "total_duration_seconds": round(pipeline_duration, 1),
        "avg_duration_per_app": round(pipeline_duration / len(applications), 1) if applications else 0,
        "used_browserbase": use_browserbase and is_browserbase_configured(),
        "results": results
    }


async def run_full_pipeline(
    top_matches_per_user: int = 3,
    min_match_score: float = 0.3,
    max_applications: int = 10,
    dry_run: bool = False,
    use_browserbase: bool = True,
    user_id: Optional[str] = None,
    generate_cover_letter: bool = False
) -> Dict[str, Any]:
    """
    Run the complete pipeline: match + queue + process.

    This is the main entry point for the scheduled job.

    Args:
        top_matches_per_user: Number of top matches per user
        min_match_score: Minimum match score threshold
        max_applications: Maximum applications to process in this run
        dry_run: If True, fill forms but don't submit
        use_browserbase: If True, use BrowserBase cloud browsers
        user_id: Optional specific user ID
        generate_cover_letter: If True, generate tailored cover letter for each application

    Returns:
        Complete pipeline results
    """
    start_time = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info("STARTING FULL MATCHING & AUTOMATION PIPELINE")
    logger.info("=" * 60)

    # Step 1: Run matching pipeline
    logger.info("Step 1: Running matching pipeline...")
    matching_result = await run_matching_pipeline(
        top_matches_per_user=top_matches_per_user,
        min_match_score=min_match_score,
        auto_queue=True,
        user_id=user_id
    )

    logger.info(f"Matching complete: {matching_result['applications_queued']} applications queued")

    # Step 2: Process queue
    logger.info("Step 2: Processing application queue...")
    processing_result = await process_application_queue(
        user_id=user_id,
        limit=max_applications,
        dry_run=dry_run,
        use_browserbase=use_browserbase,
        generate_cover_letter=generate_cover_letter
    )

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETE - Duration: {duration:.1f}s")
    logger.info("=" * 60)

    return {
        "success": True,
        "pipeline_started_at": start_time.isoformat(),
        "pipeline_completed_at": end_time.isoformat(),
        "duration_seconds": round(duration, 1),
        "matching": {
            "users_processed": matching_result.get("users_processed", 0),
            "jobs_evaluated": matching_result.get("jobs_evaluated", 0),
            "matches_found": matching_result.get("total_matches_found", 0),
            "applications_created": matching_result.get("applications_created", 0),
            "applications_queued": matching_result.get("applications_queued", 0),
            "user_summaries": matching_result.get("user_summaries", [])
        },
        "processing": {
            "applications_processed": processing_result.get("processed", 0),
            "successful": processing_result.get("successful", 0),
            "failed": processing_result.get("failed", 0),
            "dry_run": dry_run,
            "used_browserbase": processing_result.get("used_browserbase", False),
            "results": processing_result.get("results", [])
        }
    }


async def run_full_pipeline_parallel(
    top_matches_per_user: int = 3,
    min_match_score: float = 0.3,
    max_applications: int = 50,
    dry_run: bool = False,
    use_browserbase: bool = True,
    max_concurrent: Optional[int] = None,
    user_id: Optional[str] = None,
    generate_cover_letter: bool = False
) -> Dict[str, Any]:
    """
    Run the complete pipeline with PARALLEL processing: match + queue + process in parallel.

    This is the production-ready entry point that can handle large queues efficiently
    by running multiple BrowserBase sessions concurrently.

    Args:
        top_matches_per_user: Number of top matches per user
        min_match_score: Minimum match score threshold
        max_applications: Maximum applications to process in this run
        dry_run: If True, fill forms but don't submit
        use_browserbase: If True, use BrowserBase cloud browsers
        max_concurrent: Max concurrent sessions (defaults to config)
        user_id: Optional specific user ID
        generate_cover_letter: If True, generate tailored cover letter for each application

    Returns:
        Complete pipeline results with parallel processing metrics
    """
    concurrent_limit = max_concurrent or MAX_CONCURRENT_SESSIONS

    start_time = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info("STARTING FULL MATCHING & PARALLEL AUTOMATION PIPELINE")
    logger.info(f"Max concurrent sessions: {concurrent_limit}")
    logger.info("=" * 60)

    # Step 1: Run matching pipeline (same as sequential)
    logger.info("Step 1: Running matching pipeline...")
    matching_result = await run_matching_pipeline(
        top_matches_per_user=top_matches_per_user,
        min_match_score=min_match_score,
        auto_queue=True,
        user_id=user_id
    )

    logger.info(f"Matching complete: {matching_result['applications_queued']} applications queued")

    # Step 2: Process queue IN PARALLEL
    logger.info(f"Step 2: Processing application queue in PARALLEL ({concurrent_limit} concurrent)...")
    processing_result = await process_application_queue_parallel(
        user_id=user_id,
        limit=max_applications,
        dry_run=dry_run,
        use_browserbase=use_browserbase,
        max_concurrent=concurrent_limit,
        generate_cover_letter=generate_cover_letter
    )

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    # Calculate efficiency metrics
    apps_processed = processing_result.get("processed", 0)
    sequential_estimate = apps_processed * 180  # ~3 min per app sequential
    time_saved = sequential_estimate - duration if apps_processed > 0 else 0
    speedup_factor = sequential_estimate / duration if duration > 0 and apps_processed > 0 else 1

    logger.info("=" * 60)
    logger.info(f"PARALLEL PIPELINE COMPLETE - Duration: {duration:.1f}s")
    logger.info(f"Sequential estimate would be: {sequential_estimate:.1f}s")
    logger.info(f"Time saved: {time_saved:.1f}s ({speedup_factor:.1f}x speedup)")
    logger.info("=" * 60)

    return {
        "success": True,
        "parallel_mode": True,
        "max_concurrent_sessions": concurrent_limit,
        "pipeline_started_at": start_time.isoformat(),
        "pipeline_completed_at": end_time.isoformat(),
        "duration_seconds": round(duration, 1),
        "efficiency": {
            "sequential_estimate_seconds": round(sequential_estimate, 1),
            "time_saved_seconds": round(time_saved, 1),
            "speedup_factor": round(speedup_factor, 2)
        },
        "matching": {
            "users_processed": matching_result.get("users_processed", 0),
            "jobs_evaluated": matching_result.get("jobs_evaluated", 0),
            "matches_found": matching_result.get("total_matches_found", 0),
            "applications_created": matching_result.get("applications_created", 0),
            "applications_queued": matching_result.get("applications_queued", 0),
            "user_summaries": matching_result.get("user_summaries", [])
        },
        "processing": {
            "applications_processed": processing_result.get("processed", 0),
            "successful": processing_result.get("successful", 0),
            "failed": processing_result.get("failed", 0),
            "dry_run": dry_run,
            "avg_duration_per_app": processing_result.get("avg_duration_per_app", 0),
            "used_browserbase": processing_result.get("used_browserbase", False),
            "results": processing_result.get("results", [])
        }
    }
