# backend/app/routers/automation.py

"""
API endpoints for job application automation.
Handles triggering, monitoring, and managing automated job applications.
Supports BrowserBase for cloud browser automation.
"""

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging

from app.database import get_supabase
from app.services.automation_service import (
    run_application_pipeline,
    run_test_pipeline,
    process_queued_applications,
    detect_ats_platform,
    is_browserbase_configured,
    get_browserbase_proxy_settings,
    ATS_DOMAINS
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/config")
async def get_automation_config():
    """
    Get automation configuration status including BrowserBase availability.
    """
    proxy_settings = get_browserbase_proxy_settings()

    return {
        "success": True,
        "browserbase": {
            "configured": is_browserbase_configured(),
            "enabled": True,
            "description": "Cloud browser automation via BrowserBase",
            "proxy": {
                "enabled": proxy_settings["enabled"],
                "mode": proxy_settings["mode"],
                "server": proxy_settings["server"],
            }
        },
        "local_browser": {
            "available": True,
            "description": "Local Playwright browser (fallback)"
        }
    }


@router.get("/supported-platforms")
async def get_supported_platforms():
    """
    Get list of supported ATS platforms for automation.
    """
    return {
        "success": True,
        "browserbase_configured": is_browserbase_configured(),
        "platforms": [
            {
                "name": platform,
                "domain": domain,
                "supported": True
            }
            for domain, platform in ATS_DOMAINS.items()
        ]
    }


@router.get("/check-support")
async def check_job_support(
    job_id: Optional[str] = Query(None, description="Job ID to check"),
    url: Optional[str] = Query(None, description="URL to check")
):
    """
    Check if a job URL is supported for automation.
    Either provide job_id or url.
    """
    if not job_id and not url:
        raise HTTPException(status_code=400, detail="Provide either job_id or url")

    if job_id:
        supabase = get_supabase()
        job_result = supabase.table("jobs").select("apply_url, title, company").eq("id", job_id).single().execute()
        if not job_result.data:
            raise HTTPException(status_code=404, detail="Job not found")
        url = job_result.data.get("apply_url")
        job_info = job_result.data
    else:
        job_info = None

    platform = detect_ats_platform(url)

    return {
        "success": True,
        "url": url,
        "supported": platform is not None,
        "platform": platform,
        "job_info": job_info
    }


@router.post("/queue")
async def queue_application(
    application_id: str = Query(..., description="Application ID to queue for automation"),
):
    """
    Queue an application for automated processing.
    Changes application status from 'matched' to 'queued'.
    """
    supabase = get_supabase()

    # Fetch application
    app_result = supabase.table("applications").select(
        "id, user_id, job_id, status"
    ).eq("id", application_id).single().execute()

    if not app_result.data:
        raise HTTPException(status_code=404, detail="Application not found")

    application = app_result.data

    # Check current status
    if application["status"] not in ["matched", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot queue application with status '{application['status']}'. Must be 'matched' or 'failed'."
        )

    # Get job to check if URL is supported
    job_result = supabase.table("jobs").select("apply_url, title, company").eq("id", application["job_id"]).single().execute()
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Job not found")

    job = job_result.data
    platform = detect_ats_platform(job.get("apply_url"))

    if not platform:
        raise HTTPException(
            status_code=400,
            detail=f"Job URL is not supported for automation. Supported platforms: {', '.join(ATS_DOMAINS.keys())}"
        )

    # Update status to queued
    supabase.table("applications").update({
        "status": "queued",
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", application_id).execute()

    return {
        "success": True,
        "message": f"Application queued for {job.get('title')} at {job.get('company')}",
        "application_id": application_id,
        "platform": platform
    }


@router.post("/queue-batch")
async def queue_applications_batch(
    user_id: str = Query(..., description="User ID to queue applications for"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of applications to queue"),
    min_match_score: float = Query(0.7, ge=0, le=1, description="Minimum match score to queue")
):
    """
    Queue multiple matched applications for a user.
    Only queues jobs with supported ATS platforms.
    """
    supabase = get_supabase()

    # Fetch matched applications with job URLs
    result = supabase.table("applications").select(
        "id, job_id, match_score, jobs(apply_url, title, company)"
    ).eq("user_id", user_id).eq("status", "matched").gte("match_score", min_match_score).order(
        "match_score", desc=True
    ).limit(limit * 2).execute()  # Fetch extra in case some are unsupported

    if not result.data:
        return {
            "success": True,
            "message": "No matched applications found",
            "queued_count": 0
        }

    queued = []
    skipped = []

    for app in result.data:
        if len(queued) >= limit:
            break

        job = app.get("jobs", {})
        apply_url = job.get("apply_url") if job else None
        platform = detect_ats_platform(apply_url) if apply_url else None

        if platform:
            # Queue this application
            supabase.table("applications").update({
                "status": "queued",
                "queued_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", app["id"]).execute()

            queued.append({
                "application_id": app["id"],
                "job_title": job.get("title"),
                "company": job.get("company"),
                "platform": platform,
                "match_score": app["match_score"]
            })
        else:
            skipped.append({
                "application_id": app["id"],
                "job_title": job.get("title") if job else "Unknown",
                "reason": "Unsupported ATS platform"
            })

    return {
        "success": True,
        "message": f"Queued {len(queued)} applications",
        "queued_count": len(queued),
        "skipped_count": len(skipped),
        "queued": queued,
        "skipped": skipped[:10]  # Only show first 10 skipped
    }


@router.post("/run/{application_id}")
async def run_single_application(
    application_id: str,
    background_tasks: BackgroundTasks,
    dry_run: bool = Query(False, description="Fill form but don't submit"),
    use_browserbase: bool = Query(True, description="Use BrowserBase cloud browsers (recommended)"),
    headless: bool = Query(True, description="Run browser in headless mode (only if not using BrowserBase)"),
    run_async: bool = Query(True, description="Run in background (non-blocking)")
):
    """
    Run automation for a single application.

    By default uses BrowserBase for cloud browser automation.
    Falls back to local Playwright browser if BrowserBase is not configured.
    Runs asynchronously in the background by default.
    """
    supabase = get_supabase()

    # Fetch application
    app_result = supabase.table("applications").select(
        "id, user_id, job_id, status"
    ).eq("id", application_id).single().execute()

    if not app_result.data:
        raise HTTPException(status_code=404, detail="Application not found")

    application = app_result.data

    # Check status
    if application["status"] not in ["queued", "matched", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot run application with status '{application['status']}'"
        )

    # Get job to check platform support
    job_result = supabase.table("jobs").select("apply_url, title, company").eq("id", application["job_id"]).single().execute()
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Job not found")

    job = job_result.data
    platform = detect_ats_platform(job.get("apply_url"))
    if not platform:
        raise HTTPException(status_code=400, detail="Job URL is not supported for automation")

    # Check BrowserBase availability
    browserbase_available = is_browserbase_configured()
    will_use_browserbase = use_browserbase and browserbase_available

    if run_async:
        # Run in background
        background_tasks.add_task(
            run_application_pipeline,
            user_id=application["user_id"],
            job_id=application["job_id"],
            application_id=application_id,
            dry_run=dry_run,
            use_browserbase=use_browserbase,
            headless=headless
        )

        return {
            "success": True,
            "message": f"Application started in background for {job.get('title')} at {job.get('company')}",
            "application_id": application_id,
            "platform": platform,
            "status": "processing",
            "using_browserbase": will_use_browserbase,
            "dry_run": dry_run
        }
    else:
        # Run synchronously (blocking)
        result = await run_application_pipeline(
            user_id=application["user_id"],
            job_id=application["job_id"],
            application_id=application_id,
            dry_run=dry_run,
            use_browserbase=use_browserbase,
            headless=headless
        )

        return {
            "success": result["success"],
            "application_id": application_id,
            "platform": platform,
            "result": result
        }


@router.post("/run-batch")
async def run_batch_applications(
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = Query(None, description="User ID to process for"),
    limit: int = Query(10, ge=1, le=50, description="Maximum applications to process"),
    dry_run: bool = Query(False, description="Fill forms but don't submit"),
    use_browserbase: bool = Query(True, description="Use BrowserBase cloud browsers (recommended)")
):
    """
    Process multiple queued applications.

    By default uses BrowserBase for cloud browser automation.
    Falls back to local Playwright browser if BrowserBase is not configured.
    Runs in the background.
    """
    browserbase_available = is_browserbase_configured()
    will_use_browserbase = use_browserbase and browserbase_available

    background_tasks.add_task(
        process_queued_applications,
        user_id=user_id,
        limit=limit,
        dry_run=dry_run,
        use_browserbase=use_browserbase
    )

    return {
        "success": True,
        "message": f"Started processing up to {limit} queued applications",
        "status": "processing",
        "using_browserbase": will_use_browserbase,
        "dry_run": dry_run
    }


@router.get("/status/{application_id}")
async def get_application_status(application_id: str):
    """
    Get the current status and details of an application.
    """
    supabase = get_supabase()

    result = supabase.table("applications").select(
        "id, user_id, job_id, status, match_score, match_reasons, "
        "matched_at, queued_at, started_at, submitted_at, "
        "attempt_count, max_attempts, last_error, confirmation_number, "
        "answers_used, created_at, updated_at, "
        "jobs(title, company, location, apply_url)"
    ).eq("id", application_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Application not found")

    app = result.data
    job = app.pop("jobs", {})

    return {
        "success": True,
        "application": {
            **app,
            "job": job,
            "platform": detect_ats_platform(job.get("apply_url")) if job else None
        }
    }


@router.get("/user/{user_id}/applications")
async def get_user_applications(
    user_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    Get all applications for a user with optional status filter.
    """
    supabase = get_supabase()

    query = supabase.table("applications").select(
        "id, status, match_score, matched_at, queued_at, started_at, submitted_at, "
        "attempt_count, last_error, confirmation_number, created_at, "
        "jobs(id, title, company, location, apply_url)"
    ).eq("user_id", user_id).order("created_at", desc=True)

    if status:
        query = query.eq("status", status)

    result = query.range(offset, offset + limit - 1).execute()

    # Add platform info to each application
    applications = []
    for app in result.data or []:
        job = app.pop("jobs", {})
        applications.append({
            **app,
            "job": job,
            "platform": detect_ats_platform(job.get("apply_url")) if job else None,
            "automation_supported": detect_ats_platform(job.get("apply_url")) is not None if job else False
        })

    # Get counts by status
    counts_result = supabase.table("applications").select(
        "status"
    ).eq("user_id", user_id).execute()

    status_counts = {}
    for app in counts_result.data or []:
        s = app["status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    return {
        "success": True,
        "total": len(applications),
        "status_counts": status_counts,
        "applications": applications
    }


@router.delete("/{application_id}")
async def cancel_application(application_id: str):
    """
    Cancel a queued or matched application.
    Cannot cancel applications that are already started or submitted.
    """
    supabase = get_supabase()

    # Fetch application
    app_result = supabase.table("applications").select("status").eq("id", application_id).single().execute()

    if not app_result.data:
        raise HTTPException(status_code=404, detail="Application not found")

    status = app_result.data["status"]

    if status in ["started", "submitted"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel application with status '{status}'"
        )

    # Delete the application
    supabase.table("applications").delete().eq("id", application_id).execute()

    return {
        "success": True,
        "message": "Application cancelled and removed",
        "application_id": application_id
    }


@router.post("/retry/{application_id}")
async def retry_application(
    application_id: str,
    background_tasks: BackgroundTasks,
    dry_run: bool = Query(False)
):
    """
    Retry a failed application.
    Resets attempt count and queues for processing.
    """
    supabase = get_supabase()

    # Fetch application
    app_result = supabase.table("applications").select(
        "id, user_id, job_id, status, attempt_count, max_attempts"
    ).eq("id", application_id).single().execute()

    if not app_result.data:
        raise HTTPException(status_code=404, detail="Application not found")

    app = app_result.data

    if app["status"] != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Can only retry failed applications. Current status: {app['status']}"
        )

    if app["attempt_count"] >= app["max_attempts"]:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum attempts ({app['max_attempts']}) reached. Increase max_attempts to retry."
        )

    # Queue for retry
    supabase.table("applications").update({
        "status": "queued",
        "last_error": None,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", application_id).execute()

    # Run in background
    background_tasks.add_task(
        run_application_pipeline,
        user_id=app["user_id"],
        job_id=app["job_id"],
        application_id=application_id,
        dry_run=dry_run
    )

    return {
        "success": True,
        "message": "Application queued for retry",
        "application_id": application_id,
        "attempt": app["attempt_count"] + 1,
        "max_attempts": app["max_attempts"]
    }


@router.post("/test-url")
async def test_url_automation(
    background_tasks: BackgroundTasks,
    user_id: str = Query(..., description="User ID to use for profile data"),
    apply_url: str = Query(..., description="Direct URL to the job application page"),
    job_title: Optional[str] = Query(None, description="Job title (optional, for cover letter)"),
    company: Optional[str] = Query(None, description="Company name (optional, for cover letter)"),
    dry_run: bool = Query(True, description="Fill form but don't submit (default: True for safety)"),
    use_browserbase: bool = Query(False, description="Use BrowserBase cloud browsers (default: False for local)"),
    headless: bool = Query(True, description="Run browser in headless mode (only for local browser)"),
    generate_cover_letter: bool = Query(False, description="Generate tailored cover letter"),
    run_async: bool = Query(False, description="Run in background (default: False for immediate result)"),
    keep_browser_open: bool = Query(False, description="Keep browser open after completion (for debugging)")
):
    """
    Test automation with a direct URL without creating database records.

    This endpoint is for testing purposes - it runs the automation pipeline
    directly on a provided URL using the user's profile, but does NOT:
    - Create a job record in the database
    - Create an application record in the database
    - Track the application status

    Useful for:
    - Testing automation on specific job URLs
    - Debugging ATS-specific issues
    - Verifying user profile data works correctly

    By default uses local Chromium (use_browserbase=false) and dry_run=true for safety.
    """
    # Validate URL is supported
    platform = detect_ats_platform(apply_url)
    if not platform:
        supported = ", ".join(ATS_DOMAINS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"URL is not from a supported ATS platform. Supported domains: {supported}"
        )

    # Verify user exists
    supabase = get_supabase()
    user_result = supabase.table("users").select("id, first_name, last_name, resume_url").eq("id", user_id).single().execute()
    if not user_result.data:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    user = user_result.data
    if not user.get("resume_url"):
        raise HTTPException(status_code=400, detail="User does not have a resume uploaded")

    browserbase_available = is_browserbase_configured()
    will_use_browserbase = use_browserbase and browserbase_available

    if run_async:
        # Run in background
        background_tasks.add_task(
            run_test_pipeline,
            user_id=user_id,
            apply_url=apply_url,
            job_title=job_title,
            company=company,
            dry_run=dry_run,
            use_browserbase=use_browserbase,
            headless=headless,
            generate_cover_letter_flag=generate_cover_letter,
            keep_browser_open=keep_browser_open
        )

        return {
            "success": True,
            "message": f"Test automation started in background for {platform} URL",
            "status": "processing",
            "platform": platform,
            "user": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "apply_url": apply_url,
            "using_browserbase": will_use_browserbase,
            "dry_run": dry_run
        }
    else:
        # Run synchronously and return result
        result = await run_test_pipeline(
            user_id=user_id,
            apply_url=apply_url,
            job_title=job_title,
            company=company,
            dry_run=dry_run,
            use_browserbase=use_browserbase,
            headless=headless,
            generate_cover_letter_flag=generate_cover_letter,
            keep_browser_open=keep_browser_open
        )

        return {
            "success": result["success"],
            "platform": platform,
            "user": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "apply_url": apply_url,
            "result": result
        }
