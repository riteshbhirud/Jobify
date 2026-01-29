#!/usr/bin/env python3
"""
Script to run job matching for test users and generate a detailed report.

Usage:
    cd backend
    source venv/bin/activate
    python -m scripts.run_matching_report
"""

import asyncio
import sys
import os
import json
import math
from datetime import datetime
from typing import Dict, List, Any

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.database import get_supabase

settings = get_settings()
supabase = get_supabase()


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


def get_role_category(text: str):
    """Determine the role category from title or description text."""
    if not text:
        return None
    text_lower = text.lower()
    for category, keywords in ROLE_CATEGORIES.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "general"


def calculate_skill_match(user_skills: List[str], job_description: str, job_title: str) -> tuple[float, List[str]]:
    """Calculate how many user skills appear in the job posting."""
    if not user_skills:
        return 0.0, []

    job_text = f"{job_title} {job_description}".lower() if job_description else job_title.lower()

    matched_skills = []
    for skill in user_skills:
        skill_lower = skill.lower()
        if skill_lower in job_text:
            matched_skills.append(skill)
        elif len(skill_lower.split()) > 1 and all(word in job_text for word in skill_lower.split()):
            matched_skills.append(skill)

    match_ratio = len(matched_skills) / min(len(user_skills), 10)
    score = min(match_ratio * 0.12, 0.10)

    return score, matched_skills


def calculate_role_category_match(
    job_title: str,
    job_description: str,
    user_target_role: str,
    user_skills: List[str]
) -> tuple[float, str, str, bool]:
    """Compare role categories between job and user preference."""
    job_category = get_role_category(job_title)
    if job_category == "general" and job_description:
        job_category = get_role_category(job_description)

    user_category = get_role_category(user_target_role)
    if user_category == "general" and user_skills:
        skills_text = " ".join(user_skills)
        user_category = get_role_category(skills_text)

    if job_category == "general" or user_category == "general":
        return 0.0, job_category or "general", user_category or "general", True

    if job_category == user_category:
        return 0.10, job_category, user_category, True

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
            return 0.05, job_category, user_category, True

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


def cosine_similarity(vec1, vec2) -> float:
    """Calculate cosine similarity between two vectors."""
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


def calculate_match_score(job: Dict, user: Dict, similarity: float, user_skills: List[str] = None) -> tuple[float, Dict]:
    """
    Calculate comprehensive match score between job and user.

    Scoring breakdown:
    - Embedding similarity: 50% weight (semantic match)
    - Role category match: up to 10% bonus / -8% penalty
    - Skill match: up to 10% bonus
    - Preference bonuses: up to 20% (location, remote, company, title, salary)
    - Experience match: up to 8% bonus / -12% penalty
    - Hard filters eliminate jobs entirely (return 0)
    """
    reasons = {
        "embedding_similarity": round(similarity, 4),
        "filters_passed": [],
        "filters_failed": [],
        "preference_matches": [],
        "penalties": [],
        "bonuses": {},
        "preference_bonus": 0.0,
        "penalty_total": 0.0
    }

    filters_passed = True

    # ============== HARD FILTERS ==============

    # Job type check (internship vs full_time)
    user_target_type = user.get("target_type", "both")
    job_employment_type = (job.get("employment_type") or "").upper()

    if user_target_type == "internship":
        if "INTERN" not in job_employment_type:
            reasons["filters_failed"].append(f"User seeking internship but job is {job_employment_type or 'unknown type'}")
            filters_passed = False
    elif user_target_type == "full_time":
        if "FULL_TIME" not in job_employment_type or job_employment_type == "INTERN":
            reasons["filters_failed"].append(f"User seeking full-time but job is {job_employment_type or 'unknown type'}")
            filters_passed = False

    # Visa sponsorship check
    if user.get("needs_visa_sponsorship") and job.get("visa_sponsorship") is False:
        reasons["filters_failed"].append("Requires visa sponsorship but job doesn't offer it")
        filters_passed = False

    # Minimum salary check (hard filter)
    user_min_salary = user.get("min_salary")
    job_max_salary = job.get("salary_max")
    if user_min_salary and job_max_salary and job_max_salary < user_min_salary:
        reasons["filters_failed"].append(f"Job salary (${job_max_salary:,}) below user minimum (${user_min_salary:,})")
        filters_passed = False

    # Excluded companies check
    excluded_companies = user.get("excluded_companies") or []
    if excluded_companies and job.get("company"):
        job_company_lower = job.get("company", "").lower()
        for excluded in excluded_companies:
            if excluded.lower() in job_company_lower:
                reasons["filters_failed"].append(f"Company '{job.get('company')}' in excluded list")
                filters_passed = False
                break

    if not filters_passed:
        return 0.0, reasons

    reasons["filters_passed"].append("All hard filters passed")

    # ============== SOFT SCORING ==============

    preference_score = 0.0
    penalty_score = 0.0

    # ============== ROLE CATEGORY MATCHING ==============

    job_title = job.get("title", "")
    job_description = job.get("description", "")
    user_target_role = user.get("target_role", "")
    user_skills_list = user_skills or user.get("skills") or []

    role_adjustment, job_category, user_category, role_matched = calculate_role_category_match(
        job_title=job_title,
        job_description=job_description,
        user_target_role=user_target_role,
        user_skills=user_skills_list
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

    if user_skills_list:
        skill_score, matched_skills = calculate_skill_match(
            user_skills=user_skills_list,
            job_description=job_description,
            job_title=job_title
        )
        if skill_score > 0:
            preference_score += skill_score
            reasons["preference_matches"].append(f"Skills matched: {len(matched_skills)} skills")
            reasons["bonuses"]["skill_match"] = round(skill_score, 3)
            reasons["matched_skills"] = matched_skills[:5]

    # ----- 1. Remote preference (single bonus, no double-counting) -----
    user_remote_pref = user.get("remote_preference", "any")
    job_remote_type = (job.get("remote_type") or "").lower()
    job_location_lower = (job.get("location") or "").lower()
    remote_bonus_applied = False

    is_remote_job = "remote" in job_remote_type or "remote" in job_location_lower

    if user_remote_pref == "remote":
        if is_remote_job:
            preference_score += 0.08
            reasons["preference_matches"].append(f"Remote job matches preference")
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
                continue

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
            preference_score += 0.08
            reasons["preference_matches"].append(f"Experience level match: {job_exp_level}")
            reasons["bonuses"]["experience_match"] = 0.08
        elif exp_diff == 1:
            preference_score += 0.03
            reasons["preference_matches"].append(f"Stretch role (+1 level)")
            reasons["bonuses"]["experience_stretch"] = 0.03
        elif exp_diff == -1:
            penalty_score += 0.03  # Reduced from 0.05
            reasons["penalties"].append(f"Job slightly below level ({job_exp_level} vs user: {user_exp_level})")
        elif exp_diff >= 2:
            penalty = 0.06 + min((exp_diff - 2) * 0.03, 0.06)  # Max -12%
            penalty_score += penalty
            reasons["penalties"].append(f"Job requires more experience ({job_exp_level} vs user: {user_exp_level})")
        elif exp_diff <= -2:
            penalty = 0.05 + min((abs(exp_diff) - 2) * 0.02, 0.05)  # Max -10%
            penalty_score += penalty
            reasons["penalties"].append(f"Job significantly below level ({job_exp_level} vs user: {user_exp_level})")

    # ----- 6. Salary fit bonus -----
    job_min_salary = job.get("salary_min")
    job_max_salary = job.get("salary_max")

    if user_min_salary and (job_min_salary or job_max_salary):
        if job_min_salary and job_min_salary >= user_min_salary:
            preference_score += 0.05
            reasons["preference_matches"].append("Salary floor meets expectations")
            reasons["bonuses"]["salary_fit"] = 0.05
        elif job_max_salary and job_max_salary >= user_min_salary * 1.2:
            preference_score += 0.03
            reasons["preference_matches"].append("Salary range has good potential")
            reasons["bonuses"]["salary_potential"] = 0.03

    # ============== FINAL SCORE CALCULATION ==============

    # Cap preference bonuses (increased cap to accommodate new signals)
    preference_score = min(preference_score, 0.35)
    reasons["preference_bonus"] = round(preference_score, 3)
    reasons["penalty_total"] = round(penalty_score, 3)

    # Final score: 50% embedding + bonuses - penalties
    final_score = (similarity * 0.50) + preference_score - penalty_score
    final_score = max(0.0, min(1.0, final_score))

    reasons["final_score_breakdown"] = {
        "embedding_contribution": round(similarity * 0.50, 3),
        "preference_bonus": round(preference_score, 3),
        "penalty": round(penalty_score, 3)
    }

    return final_score, reasons


def match_user_to_all_jobs(user: Dict, jobs: List[Dict], top_n: int = 5) -> List[Dict]:
    """Match a user to their top N jobs (without ATS filtering for report)."""
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

        similarity = cosine_similarity(user_embedding, job_embedding)
        match_score, match_reasons = calculate_match_score(job, user, similarity, user_skills=user_skills)

        # Include all matches for the report (even low scores)
        matches.append({
            "job": job,
            "match_score": match_score,
            "match_reasons": match_reasons
        })

    # Sort by score and take top N
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    return matches[:top_n]


def format_user_profile(user: Dict) -> str:
    """Format user profile for the report."""
    lines = []
    lines.append(f"  Name: {user.get('first_name', '')} {user.get('last_name', '')}")
    lines.append(f"  Email: {user.get('email', 'N/A')}")
    lines.append(f"  Target Role: {user.get('target_role', 'N/A')}")
    lines.append(f"  Target Type: {user.get('target_type', 'N/A')}")
    lines.append(f"  Experience Level: {user.get('experience_level', 'N/A')}")
    lines.append(f"  Remote Preference: {user.get('remote_preference', 'any')}")

    locations = user.get('locations') or []
    lines.append(f"  Preferred Locations: {', '.join(locations[:3]) if locations else 'Any'}")

    lines.append(f"  Min Salary: ${user.get('min_salary', 0):,}" if user.get('min_salary') else "  Min Salary: Not specified")
    lines.append(f"  Needs Visa Sponsorship: {'Yes' if user.get('needs_visa_sponsorship') else 'No'}")

    skills = user.get('skills') or []
    lines.append(f"  Top Skills: {', '.join(skills[:8])}{'...' if len(skills) > 8 else ''}")

    excluded = user.get('excluded_companies') or []
    if excluded:
        lines.append(f"  Excluded Companies: {', '.join(excluded)}")

    preferred = user.get('preferred_companies') or []
    if preferred:
        lines.append(f"  Preferred Companies: {', '.join(preferred)}")

    return '\n'.join(lines)


def format_job_details(job: Dict, rank: int, match_score: float, match_reasons: Dict) -> str:
    """Format job details for the report."""
    lines = []
    lines.append(f"  #{rank}. {job.get('title', 'Unknown Title')}")
    lines.append(f"      Company: {job.get('company', 'Unknown')}")
    lines.append(f"      Location: {job.get('location', 'N/A')}")

    if job.get('employment_type'):
        lines.append(f"      Employment Type: {job.get('employment_type')}")

    if job.get('remote_type'):
        lines.append(f"      Remote Type: {job.get('remote_type')}")

    if job.get('salary_min') or job.get('salary_max'):
        salary_str = ""
        if job.get('salary_min'):
            salary_str += f"${job.get('salary_min'):,}"
        if job.get('salary_max'):
            salary_str += f" - ${job.get('salary_max'):,}"
        lines.append(f"      Salary: {salary_str}")

    if job.get('experience_level'):
        lines.append(f"      Experience Level: {job.get('experience_level')}")

    lines.append(f"      Visa Sponsorship: {'Yes' if job.get('visa_sponsorship') else 'No' if job.get('visa_sponsorship') is False else 'Unknown'}")

    lines.append(f"      ")
    lines.append(f"      MATCH SCORE: {match_score:.4f} ({match_score*100:.1f}%)")

    # Show score breakdown
    breakdown = match_reasons.get('final_score_breakdown', {})
    if breakdown:
        lines.append(f"      Score Breakdown:")
        lines.append(f"        - Embedding (50%): {breakdown.get('embedding_contribution', 0):.3f}")
        lines.append(f"        - Bonuses: +{breakdown.get('preference_bonus', 0):.3f}")
        lines.append(f"        - Penalties: -{breakdown.get('penalty', 0):.3f}")
    else:
        lines.append(f"      - Embedding Similarity: {match_reasons.get('embedding_similarity', 0):.4f}")
        lines.append(f"      - Preference Bonus: +{match_reasons.get('preference_bonus', 0):.3f}")

    # Show role category info
    role_cat = match_reasons.get('role_category', {})
    if role_cat:
        lines.append(f"      Role Categories: user={role_cat.get('user', 'N/A')}, job={role_cat.get('job', 'N/A')}")

    # Show matched skills
    matched_skills = match_reasons.get('matched_skills', [])
    if matched_skills:
        lines.append(f"      Matched Skills: {', '.join(matched_skills[:5])}")

    if match_reasons.get('preference_matches'):
        lines.append(f"      Bonuses:")
        for pref in match_reasons['preference_matches']:
            lines.append(f"        + {pref}")

    if match_reasons.get('penalties'):
        lines.append(f"      Penalties:")
        for penalty in match_reasons['penalties']:
            lines.append(f"        - {penalty}")

    if match_reasons.get('filters_failed'):
        lines.append(f"      Filters Failed:")
        for fail in match_reasons['filters_failed']:
            lines.append(f"        ! {fail}")

    if job.get('apply_url'):
        url = job.get('apply_url')
        lines.append(f"      Apply URL: {url[:80]}{'...' if len(url) > 80 else ''}")

    return '\n'.join(lines)


async def main():
    """Run matching for all test users and generate report."""
    print("\n" + "="*70)
    print("JOBIFY MATCHING REPORT GENERATOR")
    print("="*70)

    # Fetch test users
    print("\nFetching test users...")
    users_result = supabase.table("users").select(
        "id, email, first_name, last_name, target_role, target_type, "
        "experience_level, remote_preference, locations, min_salary, "
        "needs_visa_sponsorship, skills, excluded_companies, preferred_companies, "
        "embedding"
    ).like("email", "%jobify-test.com").execute()

    users = users_result.data or []
    print(f"Found {len(users)} test users")

    if not users:
        print("No test users found!")
        return

    # Fetch all jobs with embeddings
    print("Fetching jobs...")
    jobs_result = supabase.table("jobs").select(
        "id, external_id, title, company, location, apply_url, "
        "salary_min, salary_max, visa_sponsorship, remote_type, "
        "experience_level, employment_type, description, embedding"
    ).not_.is_("embedding", "null").execute()

    # Debug: count job types
    intern_jobs = sum(1 for j in (jobs_result.data or []) if "INTERN" in (j.get("employment_type") or "").upper())
    ft_jobs = sum(1 for j in (jobs_result.data or []) if "FULL_TIME" in (j.get("employment_type") or "").upper())
    print(f"  - {intern_jobs} internship jobs, {ft_jobs} full-time jobs")

    jobs = jobs_result.data or []
    print(f"Found {len(jobs)} jobs with embeddings")

    if not jobs:
        print("No jobs with embeddings found!")
        return

    # Generate report
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("JOBIFY JOB MATCHING REPORT")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append(f"Total Test Users: {len(users)}")
    report_lines.append(f"Total Jobs in Database: {len(jobs)}")
    report_lines.append("")
    report_lines.append("Matching Algorithm (v2 - Improved):")
    report_lines.append("  - Cosine similarity between user and job embeddings (50% weight)")
    report_lines.append("  - Role category matching:")
    report_lines.append("      * Exact category match (ML/AI, Frontend, Backend, etc.): +10%")
    report_lines.append("      * Related category match: +5%")
    report_lines.append("      * Category mismatch penalty: -8%")
    report_lines.append("  - Skill matching (up to +10%)")
    report_lines.append("  - Preference bonuses (up to 35% total cap):")
    report_lines.append("      * Remote/hybrid preference match (+8%/+5%)")
    report_lines.append("      * Preferred company match (+8%)")
    report_lines.append("      * Location match with metro area expansion (+5%)")
    report_lines.append("      * Job title similarity to target role (up to +12%)")
    report_lines.append("      * Experience level match (+8% exact, +3% stretch)")
    report_lines.append("      * Salary fit bonus (+5% meets floor, +3% good potential)")
    report_lines.append("  - Penalties:")
    report_lines.append("      * On-site job for remote seeker (-10%)")
    report_lines.append("      * Experience mismatch (-3% to -12%, graduated)")
    report_lines.append("  - Hard filters (eliminate job entirely):")
    report_lines.append("      * Job type (internship vs full-time)")
    report_lines.append("      * Visa sponsorship requirement")
    report_lines.append("      * Minimum salary requirement")
    report_lines.append("      * Excluded companies")
    report_lines.append("")
    report_lines.append("=" * 80)

    # Process each user
    for i, user in enumerate(users, 1):
        print(f"\nProcessing user {i}/{len(users)}: {user.get('first_name')} {user.get('last_name')}")

        report_lines.append("")
        report_lines.append(f"USER {i}: {user.get('first_name')} {user.get('last_name')}")
        report_lines.append("-" * 80)
        report_lines.append("")
        report_lines.append("PROFILE:")
        report_lines.append(format_user_profile(user))
        report_lines.append("")
        report_lines.append("TOP 5 JOB MATCHES:")
        report_lines.append("")

        # Get top 5 matches
        matches = match_user_to_all_jobs(user, jobs, top_n=5)

        if not matches:
            report_lines.append("  No matches found (user may not have embedding)")
        else:
            for rank, match in enumerate(matches, 1):
                job = match["job"]
                score = match["match_score"]
                reasons = match["match_reasons"]

                report_lines.append(format_job_details(job, rank, score, reasons))
                report_lines.append("")

        report_lines.append("=" * 80)

    # Write report to file
    report_content = '\n'.join(report_lines)
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "matching_report.txt"
    )

    with open(output_path, 'w') as f:
        f.write(report_content)

    print(f"\n{'='*70}")
    print(f"Report generated: {output_path}")
    print(f"{'='*70}\n")

    # Also print summary
    print("SUMMARY:")
    print("-" * 40)
    for user in users:
        matches = match_user_to_all_jobs(user, jobs, top_n=5)
        avg_score = sum(m["match_score"] for m in matches) / len(matches) if matches else 0
        top_score = matches[0]["match_score"] if matches else 0
        print(f"  {user.get('first_name')} {user.get('last_name')}: "
              f"Top Score={top_score:.3f}, Avg={avg_score:.3f}")

    return output_path


if __name__ == "__main__":
    asyncio.run(main())
