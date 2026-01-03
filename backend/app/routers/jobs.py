# backend/app/routers/jobs.py

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
import httpx
import os
from datetime import datetime

router = APIRouter()

# JSearch API configuration
JSEARCH_API_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")  # Get from environment variable

# In-memory cache for jobs (since we're not using a database)
jobs_cache: List[Dict[str, Any]] = []
last_fetch_time: Optional[datetime] = None


async def fetch_jobs_from_jsearch(
    query: str = "software engineer",
    location: str = "United States",
    num_pages: int = 1,
    employment_types: Optional[str] = None,
    remote_jobs_only: bool = False
) -> List[Dict[str, Any]]:
    """
    Fetch jobs from JSearch API

    Args:
        query: Job search query (e.g., "python developer", "data scientist")
        location: Location to search (e.g., "New York, NY", "Remote")
        num_pages: Number of pages to fetch (10 results per page)
        employment_types: Comma-separated employment types (FULLTIME, PARTTIME, CONTRACTOR, INTERN)
        remote_jobs_only: Filter for remote jobs only
    """
    print("API KEY: ", JSEARCH_API_KEY)
    headers = {
        "X-RapidAPI-Key": JSEARCH_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }

    params = {
        "query": query,
        "page": "1",
        "num_pages": str(num_pages),
    }

    if location:
        params["location"] = location

    if employment_types:
        params["employment_types"] = employment_types

    if remote_jobs_only:
        params["remote_jobs_only"] = "true"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                JSEARCH_API_URL,
                headers=headers,
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            # Parse and normalize job data
            jobs = []
            for job in data.get("data", []):
                normalized_job = {
                    "job_id": job.get("job_id"),
                    "title": job.get("job_title"),
                    "company": job.get("employer_name"),
                    "location": job.get("job_city") or job.get("job_state") or job.get("job_country"),
                    "description": job.get("job_description"),
                    "apply_link": job.get("job_apply_link"),
                    "employment_type": job.get("job_employment_type"),
                    "salary_min": job.get("job_min_salary"),
                    "salary_max": job.get("job_max_salary"),
                    "salary_currency": job.get("job_salary_currency"),
                    "salary_period": job.get("job_salary_period"),
                    "posted_date": job.get("job_posted_at_datetime_utc"),
                    "is_remote": job.get("job_is_remote", False),
                    "experience_level": job.get("job_required_experience", {}).get("required_experience_in_months") if isinstance(job.get("job_required_experience"), dict) else None,
                    "logo": job.get("employer_logo"),
                    "publisher": job.get("job_publisher"),
                }
                jobs.append(normalized_job)

            return jobs

    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Error fetching jobs from JSearch API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/search")
async def search_jobs(
    query: str = Query("software engineer", description="Job search query"),
    location: str = Query("United States", description="Job location"),
    num_pages: int = Query(1, ge=1, le=20, description="Number of pages to fetch"),
    employment_types: Optional[str] = Query(None, description="Employment types (FULLTIME, PARTTIME, CONTRACTOR, INTERN)"),
    remote_jobs_only: bool = Query(False, description="Filter for remote jobs only"),
):
    """
    Search for jobs using JSearch API
    """
    jobs = await fetch_jobs_from_jsearch(
        query=query,
        location=location,
        num_pages=num_pages,
        employment_types=employment_types,
        remote_jobs_only=remote_jobs_only
    )

    return {
        "success": True,
        "count": len(jobs),
        "jobs": jobs
    }


@router.get("/cached")
async def get_cached_jobs():
    """
    Get cached jobs from the last scrape
    """
    global jobs_cache, last_fetch_time

    return {
        "success": True,
        "count": len(jobs_cache),
        "jobs": jobs_cache,
        "last_fetch_time": last_fetch_time.isoformat() if last_fetch_time else None
    }


@router.post("/scrape")
async def trigger_scrape(
    query: str = Query("software engineer", description="Job search query"),
    location: str = Query("United States", description="Job location"),
    num_pages: int = Query(3, ge=1, le=20, description="Number of pages to fetch"),
):
    """
    Manually trigger a job scrape and update the cache
    """
    global jobs_cache, last_fetch_time

    try:
        jobs = await fetch_jobs_from_jsearch(
            query=query,
            location=location,
            num_pages=num_pages
        )

        # Update cache
        jobs_cache = jobs
        last_fetch_time = datetime.utcnow()

        return {
            "success": True,
            "message": "Jobs scraped successfully",
            "count": len(jobs),
            "jobs": jobs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
