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
from app.services.automation_service import (
    run_application_pipeline,
    detect_ats_platform,
    is_browserbase_configured
)

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


def calculate_match_score(job: Dict, user: Dict, similarity: float) -> tuple[float, Dict]:
    """
    Calculate comprehensive match score between job and user.
    Returns (score, reasons).
    """
    reasons = {
        "embedding_similarity": round(similarity, 3),
        "filters_passed": [],
        "filters_failed": [],
        "preference_matches": []
    }

    filters_passed = True

    # Visa sponsorship check
    if user.get("needs_visa_sponsorship") and job.get("visa_sponsorship") is False:
        reasons["filters_failed"].append("Requires visa sponsorship but job doesn't offer it")
        filters_passed = False

    # Minimum salary check
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

    # Preference bonuses
    preference_score = 0.0

    # Remote preference
    user_remote_pref = user.get("remote_preference", "any")
    job_remote_type = (job.get("remote_type") or "").lower()
    if user_remote_pref == "remote" and "remote" in job_remote_type:
        preference_score += 0.1
        reasons["preference_matches"].append("Remote preference matched")

    # Preferred companies
    preferred_companies = user.get("preferred_companies") or []
    if preferred_companies and job.get("company"):
        job_company_lower = job.get("company", "").lower()
        for preferred in preferred_companies:
            if preferred.lower() in job_company_lower:
                preference_score += 0.1
                reasons["preference_matches"].append(f"Preferred company")
                break

    # Location matching
    user_locations = user.get("locations") or []
    job_location = job.get("location") or ""
    if user_locations and job_location:
        for loc in user_locations:
            if loc.lower() in job_location.lower():
                preference_score += 0.05
                reasons["preference_matches"].append(f"Location matched")
                break

    preference_score = min(preference_score, 0.3)
    final_score = (similarity * 0.7) + preference_score
    final_score = max(0.0, min(1.0, final_score))

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
        match_score, match_reasons = calculate_match_score(job, user, similarity)

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

    # Fetch users
    users_query = supabase.table("users").select(
        "id, email, first_name, last_name, embedding, min_match_score, "
        "needs_visa_sponsorship, min_salary, excluded_companies, preferred_companies, "
        "locations, remote_preference, experience_level, is_active"
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

    # Fetch jobs with embeddings
    jobs_result = supabase.table("jobs").select(
        "id, external_id, title, company, location, apply_url, "
        "salary_min, salary_max, visa_sponsorship, remote_type, "
        "experience_level, embedding"
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
    delay_between_apps: float = 5.0
) -> Dict[str, Any]:
    """
    Process queued applications by running automation pipelines.

    Args:
        user_id: Optional specific user ID
        limit: Maximum applications to process
        dry_run: If True, fill forms but don't submit
        use_browserbase: If True, use BrowserBase cloud browsers
        delay_between_apps: Seconds to wait between applications

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
                use_browserbase=use_browserbase
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


async def run_full_pipeline(
    top_matches_per_user: int = 3,
    min_match_score: float = 0.3,
    max_applications: int = 10,
    dry_run: bool = False,
    use_browserbase: bool = True,
    user_id: Optional[str] = None
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
        use_browserbase=use_browserbase
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
