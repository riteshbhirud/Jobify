# backend/app/routers/pipeline.py

"""
API endpoints for the matching and automation pipeline.
Provides manual triggers and status monitoring for the job matching system.
"""

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from typing import Optional
from datetime import datetime, timezone
import logging

from app.database import get_supabase
from app.services.matching_pipeline import (
    run_matching_pipeline,
    process_application_queue,
    run_full_pipeline
)
from app.services.automation_service import is_browserbase_configured

router = APIRouter()
logger = logging.getLogger(__name__)

# Track pipeline runs
_pipeline_status = {
    "last_run": None,
    "is_running": False,
    "last_result": None
}


@router.get("/status")
async def get_pipeline_status():
    """
    Get the current status of the pipeline.
    Shows last run time, whether it's currently running, and last results.
    """
    supabase = get_supabase()

    # Get queue statistics
    queued_result = supabase.table("applications").select("id", count="exact").eq("status", "queued").execute()
    matched_result = supabase.table("applications").select("id", count="exact").eq("status", "matched").execute()
    submitted_result = supabase.table("applications").select("id", count="exact").eq("status", "submitted").execute()
    failed_result = supabase.table("applications").select("id", count="exact").eq("status", "failed").execute()

    # Get active users count
    users_result = supabase.table("users").select("id", count="exact").eq("is_active", True).not_.is_("embedding", "null").execute()

    # Get jobs with embeddings count
    jobs_result = supabase.table("jobs").select("id", count="exact").not_.is_("embedding", "null").execute()

    return {
        "success": True,
        "pipeline": {
            "is_running": _pipeline_status["is_running"],
            "last_run": _pipeline_status["last_run"],
            "last_result_summary": {
                "success": _pipeline_status["last_result"].get("success") if _pipeline_status["last_result"] else None,
                "duration_seconds": _pipeline_status["last_result"].get("duration_seconds") if _pipeline_status["last_result"] else None
            } if _pipeline_status["last_result"] else None
        },
        "queue": {
            "queued": queued_result.count or 0,
            "matched": matched_result.count or 0,
            "submitted": submitted_result.count or 0,
            "failed": failed_result.count or 0
        },
        "resources": {
            "active_users_with_embeddings": users_result.count or 0,
            "jobs_with_embeddings": jobs_result.count or 0,
            "browserbase_configured": is_browserbase_configured()
        }
    }


@router.post("/match")
async def trigger_matching(
    background_tasks: BackgroundTasks,
    top_matches_per_user: int = Query(3, ge=1, le=10, description="Number of top matches per user"),
    min_match_score: float = Query(0.3, ge=0.0, le=1.0, description="Minimum match score threshold"),
    auto_queue: bool = Query(True, description="Automatically queue matches for automation"),
    user_id: Optional[str] = Query(None, description="Match for specific user only"),
    run_async: bool = Query(True, description="Run in background")
):
    """
    Trigger the matching pipeline.

    Matches all active users (or a specific user) to their top N jobs
    and creates application records. Optionally queues them for automation.
    """
    if _pipeline_status["is_running"]:
        raise HTTPException(
            status_code=409,
            detail="Pipeline is already running. Please wait for it to complete."
        )

    async def run_matching():
        global _pipeline_status
        _pipeline_status["is_running"] = True
        _pipeline_status["last_run"] = datetime.now(timezone.utc).isoformat()

        try:
            result = await run_matching_pipeline(
                top_matches_per_user=top_matches_per_user,
                min_match_score=min_match_score,
                auto_queue=auto_queue,
                user_id=user_id
            )
            _pipeline_status["last_result"] = result
            return result
        finally:
            _pipeline_status["is_running"] = False

    if run_async:
        background_tasks.add_task(run_matching)
        return {
            "success": True,
            "message": "Matching pipeline started in background",
            "status": "processing",
            "params": {
                "top_matches_per_user": top_matches_per_user,
                "min_match_score": min_match_score,
                "auto_queue": auto_queue,
                "user_id": user_id
            }
        }
    else:
        result = await run_matching()
        return result


@router.post("/process-queue")
async def trigger_queue_processing(
    background_tasks: BackgroundTasks,
    limit: int = Query(10, ge=1, le=50, description="Maximum applications to process"),
    dry_run: bool = Query(False, description="Fill forms but don't submit"),
    use_browserbase: bool = Query(True, description="Use BrowserBase cloud browsers"),
    user_id: Optional[str] = Query(None, description="Process for specific user only"),
    run_async: bool = Query(True, description="Run in background")
):
    """
    Process queued applications.

    Takes applications with status='queued' and runs the automation
    pipeline to fill out and submit job applications.
    """
    if _pipeline_status["is_running"]:
        raise HTTPException(
            status_code=409,
            detail="Pipeline is already running. Please wait for it to complete."
        )

    async def run_processing():
        global _pipeline_status
        _pipeline_status["is_running"] = True

        try:
            result = await process_application_queue(
                user_id=user_id,
                limit=limit,
                dry_run=dry_run,
                use_browserbase=use_browserbase
            )
            _pipeline_status["last_result"] = result
            return result
        finally:
            _pipeline_status["is_running"] = False

    if run_async:
        background_tasks.add_task(run_processing)
        return {
            "success": True,
            "message": f"Queue processing started in background (limit: {limit})",
            "status": "processing",
            "params": {
                "limit": limit,
                "dry_run": dry_run,
                "use_browserbase": use_browserbase,
                "user_id": user_id
            }
        }
    else:
        result = await run_processing()
        return result


@router.post("/run")
async def trigger_full_pipeline(
    background_tasks: BackgroundTasks,
    top_matches_per_user: int = Query(3, ge=1, le=10, description="Number of top matches per user"),
    min_match_score: float = Query(0.3, ge=0.0, le=1.0, description="Minimum match score threshold"),
    max_applications: int = Query(10, ge=1, le=50, description="Maximum applications to process"),
    dry_run: bool = Query(False, description="Fill forms but don't submit"),
    use_browserbase: bool = Query(True, description="Use BrowserBase cloud browsers"),
    user_id: Optional[str] = Query(None, description="Run for specific user only"),
    run_async: bool = Query(True, description="Run in background")
):
    """
    Run the complete pipeline: match + queue + process.

    This is the main entry point that:
    1. Matches all active users to their top N jobs
    2. Creates and queues application records
    3. Processes the queue by filling out applications

    Use this for manual triggers or scheduled runs.
    """
    if _pipeline_status["is_running"]:
        raise HTTPException(
            status_code=409,
            detail="Pipeline is already running. Please wait for it to complete."
        )

    async def run_pipeline():
        global _pipeline_status
        _pipeline_status["is_running"] = True
        _pipeline_status["last_run"] = datetime.now(timezone.utc).isoformat()

        try:
            result = await run_full_pipeline(
                top_matches_per_user=top_matches_per_user,
                min_match_score=min_match_score,
                max_applications=max_applications,
                dry_run=dry_run,
                use_browserbase=use_browserbase,
                user_id=user_id
            )
            _pipeline_status["last_result"] = result
            return result
        finally:
            _pipeline_status["is_running"] = False

    browserbase_available = is_browserbase_configured()

    if run_async:
        background_tasks.add_task(run_pipeline)
        return {
            "success": True,
            "message": "Full pipeline started in background",
            "status": "processing",
            "browserbase_configured": browserbase_available,
            "will_use_browserbase": use_browserbase and browserbase_available,
            "params": {
                "top_matches_per_user": top_matches_per_user,
                "min_match_score": min_match_score,
                "max_applications": max_applications,
                "dry_run": dry_run,
                "use_browserbase": use_browserbase,
                "user_id": user_id
            }
        }
    else:
        result = await run_pipeline()
        return result


@router.get("/last-result")
async def get_last_result():
    """
    Get the detailed results from the last pipeline run.
    """
    if not _pipeline_status["last_result"]:
        return {
            "success": True,
            "message": "No pipeline runs yet",
            "result": None
        }

    return {
        "success": True,
        "last_run": _pipeline_status["last_run"],
        "is_running": _pipeline_status["is_running"],
        "result": _pipeline_status["last_result"]
    }


@router.get("/queue")
async def get_queue_details(
    status: Optional[str] = Query(None, description="Filter by status (queued, matched, started, submitted, failed)"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    Get detailed view of the application queue.
    """
    supabase = get_supabase()

    query = supabase.table("applications").select(
        "id, user_id, job_id, status, match_score, matched_at, queued_at, "
        "started_at, submitted_at, attempt_count, last_error, "
        "users(email, first_name, last_name), "
        "jobs(title, company, location, apply_url)"
    ).order("created_at", desc=True)

    if status:
        query = query.eq("status", status)
    if user_id:
        query = query.eq("user_id", user_id)

    result = query.range(offset, offset + limit - 1).execute()

    # Format the results
    applications = []
    for app in (result.data or []):
        user = app.pop("users", {}) or {}
        job = app.pop("jobs", {}) or {}
        applications.append({
            **app,
            "user": {
                "email": user.get("email"),
                "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            },
            "job": job
        })

    return {
        "success": True,
        "total": len(applications),
        "offset": offset,
        "limit": limit,
        "applications": applications
    }


@router.delete("/queue/clear")
async def clear_queue(
    status: str = Query(..., description="Status to clear (queued, matched, or failed)"),
    user_id: Optional[str] = Query(None, description="Clear only for specific user")
):
    """
    Clear applications with a specific status.
    Use with caution - this deletes application records.
    """
    if status not in ["queued", "matched", "failed"]:
        raise HTTPException(
            status_code=400,
            detail="Can only clear queued, matched, or failed applications"
        )

    supabase = get_supabase()

    query = supabase.table("applications").delete().eq("status", status)

    if user_id:
        query = query.eq("user_id", user_id)

    result = query.execute()

    deleted_count = len(result.data) if result.data else 0

    return {
        "success": True,
        "message": f"Cleared {deleted_count} applications with status '{status}'",
        "deleted_count": deleted_count
    }


@router.get("/matches")
async def get_all_matches(
    status: Optional[str] = Query(None, description="Filter by status"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum match score"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Get all matches across all users with job details.
    Provides full visibility into what jobs users have been matched to.
    """
    supabase = get_supabase()

    query = supabase.table("applications").select(
        "id, user_id, job_id, status, match_score, match_reasons, "
        "matched_at, queued_at, started_at, submitted_at, "
        "attempt_count, last_error, created_at, "
        "users(id, email, first_name, last_name), "
        "jobs(id, title, company, location, salary_min, salary_max, employment_type, apply_url)"
    ).gte("match_score", min_score).order("match_score", desc=True)

    if status:
        query = query.eq("status", status)

    result = query.range(offset, offset + limit - 1).execute()

    matches = []
    for app in (result.data or []):
        user = app.pop("users", {}) or {}
        job = app.pop("jobs", {}) or {}
        matches.append({
            "application_id": app["id"],
            "status": app["status"],
            "match_score": app["match_score"],
            "match_reasons": app.get("match_reasons"),
            "matched_at": app.get("matched_at"),
            "queued_at": app.get("queued_at"),
            "submitted_at": app.get("submitted_at"),
            "attempt_count": app.get("attempt_count"),
            "last_error": app.get("last_error"),
            "user": {
                "id": user.get("id"),
                "email": user.get("email"),
                "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            },
            "job": {
                "id": job.get("id"),
                "title": job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "salary_range": f"${job.get('salary_min', 0):,} - ${job.get('salary_max', 0):,}" if job.get("salary_min") else None,
                "employment_type": job.get("employment_type"),
                "apply_url": job.get("apply_url")
            }
        })

    return {
        "success": True,
        "total": len(matches),
        "offset": offset,
        "limit": limit,
        "matches": matches
    }


@router.get("/matches/user/{user_id}")
async def get_user_matches(
    user_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200)
):
    """
    Get all job matches for a specific user.
    Shows which jobs the user has been matched to, with scores and reasons.
    """
    supabase = get_supabase()

    # First get the user info
    user_result = supabase.table("users").select(
        "id, email, first_name, last_name, is_active"
    ).eq("id", user_id).single().execute()

    if not user_result.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = user_result.data

    # Get all matches for this user
    query = supabase.table("applications").select(
        "id, job_id, status, match_score, match_reasons, "
        "matched_at, queued_at, started_at, submitted_at, "
        "attempt_count, last_error, confirmation_number, "
        "jobs(id, title, company, location, description, salary_min, salary_max, "
        "employment_type, experience_level, apply_url, posted_at)"
    ).eq("user_id", user_id).order("match_score", desc=True)

    if status:
        query = query.eq("status", status)

    result = query.limit(limit).execute()

    # Format matches
    matches = []
    status_summary = {"matched": 0, "queued": 0, "started": 0, "submitted": 0, "failed": 0}

    for app in (result.data or []):
        job = app.pop("jobs", {}) or {}
        status_summary[app["status"]] = status_summary.get(app["status"], 0) + 1

        matches.append({
            "application_id": app["id"],
            "status": app["status"],
            "match_score": app["match_score"],
            "match_score_percent": f"{(app['match_score'] or 0) * 100:.1f}%",
            "match_reasons": app.get("match_reasons"),
            "timestamps": {
                "matched_at": app.get("matched_at"),
                "queued_at": app.get("queued_at"),
                "started_at": app.get("started_at"),
                "submitted_at": app.get("submitted_at")
            },
            "automation": {
                "attempt_count": app.get("attempt_count", 0),
                "last_error": app.get("last_error"),
                "confirmation_number": app.get("confirmation_number")
            },
            "job": {
                "id": job.get("id"),
                "title": job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "description_preview": (job.get("description") or "")[:200] + "..." if job.get("description") and len(job.get("description", "")) > 200 else job.get("description"),
                "salary_range": f"${job.get('salary_min', 0):,} - ${job.get('salary_max', 0):,}" if job.get("salary_min") else None,
                "employment_type": job.get("employment_type"),
                "experience_level": job.get("experience_level"),
                "apply_url": job.get("apply_url"),
                "posted_at": job.get("posted_at")
            }
        })

    return {
        "success": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "is_active": user["is_active"]
        },
        "summary": {
            "total_matches": len(matches),
            "by_status": status_summary,
            "avg_match_score": sum(m["match_score"] or 0 for m in matches) / len(matches) if matches else 0
        },
        "matches": matches
    }


@router.get("/matches/job/{job_id}")
async def get_job_matches(
    job_id: str,
    limit: int = Query(50, ge=1, le=200)
):
    """
    Get all users matched to a specific job.
    Shows which users have been matched to this job position.
    """
    supabase = get_supabase()

    # First get the job info
    job_result = supabase.table("jobs").select(
        "id, title, company, location, description, salary_min, salary_max, "
        "employment_type, experience_level, apply_url, posted_at"
    ).eq("id", job_id).single().execute()

    if not job_result.data:
        raise HTTPException(status_code=404, detail="Job not found")

    job = job_result.data

    # Get all matches for this job
    result = supabase.table("applications").select(
        "id, user_id, status, match_score, match_reasons, "
        "matched_at, queued_at, submitted_at, "
        "users(id, email, first_name, last_name)"
    ).eq("job_id", job_id).order("match_score", desc=True).limit(limit).execute()

    # Format matches
    matches = []
    for app in (result.data or []):
        user = app.pop("users", {}) or {}
        matches.append({
            "application_id": app["id"],
            "status": app["status"],
            "match_score": app["match_score"],
            "match_score_percent": f"{(app['match_score'] or 0) * 100:.1f}%",
            "match_reasons": app.get("match_reasons"),
            "matched_at": app.get("matched_at"),
            "submitted_at": app.get("submitted_at"),
            "user": {
                "id": user.get("id"),
                "email": user.get("email"),
                "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            }
        })

    return {
        "success": True,
        "job": {
            "id": job["id"],
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "salary_range": f"${job.get('salary_min', 0):,} - ${job.get('salary_max', 0):,}" if job.get("salary_min") else None,
            "employment_type": job.get("employment_type"),
            "experience_level": job.get("experience_level"),
            "apply_url": job.get("apply_url")
        },
        "total_matched_users": len(matches),
        "matches": matches
    }


@router.get("/matches/summary")
async def get_matches_summary():
    """
    Get a high-level summary of all matches in the system.
    Useful for dashboard/overview views.
    """
    supabase = get_supabase()

    # Get counts by status
    statuses = ["matched", "queued", "started", "submitted", "failed"]
    status_counts = {}

    for status in statuses:
        result = supabase.table("applications").select("id", count="exact").eq("status", status).execute()
        status_counts[status] = result.count or 0

    # Get total applications
    total_result = supabase.table("applications").select("id", count="exact").execute()

    # Get unique users with matches
    users_result = supabase.table("applications").select("user_id").execute()
    unique_users = len(set(app["user_id"] for app in (users_result.data or [])))

    # Get unique jobs matched
    jobs_result = supabase.table("applications").select("job_id").execute()
    unique_jobs = len(set(app["job_id"] for app in (jobs_result.data or [])))

    # Get average match score
    scores_result = supabase.table("applications").select("match_score").not_.is_("match_score", "null").execute()
    scores = [app["match_score"] for app in (scores_result.data or []) if app.get("match_score")]
    avg_score = sum(scores) / len(scores) if scores else 0

    # Get top matches (highest scores)
    top_matches_result = supabase.table("applications").select(
        "id, match_score, status, "
        "users(email, first_name, last_name), "
        "jobs(title, company)"
    ).not_.is_("match_score", "null").order("match_score", desc=True).limit(5).execute()

    top_matches = []
    for app in (top_matches_result.data or []):
        user = app.pop("users", {}) or {}
        job = app.pop("jobs", {}) or {}
        top_matches.append({
            "application_id": app["id"],
            "match_score": app["match_score"],
            "match_score_percent": f"{(app['match_score'] or 0) * 100:.1f}%",
            "status": app["status"],
            "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "user_email": user.get("email"),
            "job_title": job.get("title"),
            "company": job.get("company")
        })

    # Get recent activity
    recent_result = supabase.table("applications").select(
        "id, status, match_score, updated_at, "
        "users(email), jobs(title, company)"
    ).order("updated_at", desc=True).limit(10).execute()

    recent_activity = []
    for app in (recent_result.data or []):
        user = app.pop("users", {}) or {}
        job = app.pop("jobs", {}) or {}
        recent_activity.append({
            "application_id": app["id"],
            "status": app["status"],
            "match_score": app.get("match_score"),
            "updated_at": app.get("updated_at"),
            "user_email": user.get("email"),
            "job_title": job.get("title"),
            "company": job.get("company")
        })

    return {
        "success": True,
        "summary": {
            "total_applications": total_result.count or 0,
            "unique_users_matched": unique_users,
            "unique_jobs_matched": unique_jobs,
            "average_match_score": round(avg_score, 3),
            "average_match_score_percent": f"{avg_score * 100:.1f}%"
        },
        "by_status": status_counts,
        "top_matches": top_matches,
        "recent_activity": recent_activity
    }
