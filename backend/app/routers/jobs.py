# backend/app/routers/jobs.py

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
import httpx
import os
from datetime import datetime
import asyncio
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# API configurations
JSEARCH_API_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")

FINDWORK_API_URL = "https://findwork.dev/api/jobs/"
FINDWORK_API_KEY = os.getenv("FINDWORK_API_KEY", "")

# In-memory cache for jobs (since we're not using a database)
jobs_cache: List[Dict[str, Any]] = []
last_fetch_time: Optional[datetime] = None
api_stats: Dict[str, Any] = {
    "jsearch": {"count": 0, "last_fetch": None, "status": "unknown"},
    "findwork": {"count": 0, "last_fetch": None, "status": "unknown"},
}


async def fetch_jobs_from_jsearch(
    query: str = "software engineer",
    location: str = "United States",
    num_pages: int = 1,
    employment_types: Optional[str] = None,
    remote_jobs_only: bool = False
) -> List[Dict[str, Any]]:
    """Fetch jobs from JSearch API (RapidAPI)"""
    global api_stats

    if not JSEARCH_API_KEY:
        logger.warning("JSearch API key not configured")
        api_stats["jsearch"]["status"] = "not_configured"
        return []

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

            jobs = []
            for job in data.get("data", []):
                normalized_job = {
                    "job_id": f"jsearch_{job.get('job_id')}",
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
                    "source": "JSearch"
                }
                jobs.append(normalized_job)

            api_stats["jsearch"]["count"] = len(jobs)
            api_stats["jsearch"]["last_fetch"] = datetime.utcnow().isoformat()
            api_stats["jsearch"]["status"] = "success"
            logger.info(f"Fetched {len(jobs)} jobs from JSearch")
            return jobs

    except httpx.HTTPError as e:
        logger.error(f"JSearch API error: {str(e)}")
        api_stats["jsearch"]["status"] = "error"
        return []
    except Exception as e:
        logger.error(f"JSearch unexpected error: {str(e)}")
        api_stats["jsearch"]["status"] = "error"
        return []


async def fetch_jobs_from_findwork(
    query: str = "software engineer",
    location: Optional[str] = None,
    remote_only: bool = False
) -> List[Dict[str, Any]]:
    """Fetch jobs from Findwork.dev API (Free, developer-focused jobs)"""
    global api_stats

    # Findwork API is public and doesn't require authentication for basic usage
    params = {
        "search": query,
    }

    if remote_only:
        params["location"] = "remote"
    elif location:
        params["location"] = location

    try:
        async with httpx.AsyncClient() as client:
            # Add Authorization header if API key is provided
            headers = {}
            if FINDWORK_API_KEY:
                headers["Authorization"] = f"Token {FINDWORK_API_KEY}"

            response = await client.get(
                FINDWORK_API_URL,
                headers=headers if headers else None,
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            jobs = []
            results = data.get("results", [])

            for job in results:
                normalized_job = {
                    "job_id": f"findwork_{job.get('id')}",
                    "title": job.get("role"),
                    "company": job.get("company_name"),
                    "location": job.get("location"),
                    "description": job.get("text"),
                    "apply_link": job.get("url"),
                    "employment_type": job.get("employment_type"),
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": None,
                    "salary_period": None,
                    "posted_date": job.get("date_posted"),
                    "is_remote": job.get("remote", False),
                    "experience_level": None,
                    "logo": job.get("logo"),
                    "publisher": "Findwork",
                    "source": "Findwork"
                }
                jobs.append(normalized_job)

            api_stats["findwork"]["count"] = len(jobs)
            api_stats["findwork"]["last_fetch"] = datetime.utcnow().isoformat()
            api_stats["findwork"]["status"] = "success"
            logger.info(f"Fetched {len(jobs)} jobs from Findwork")
            return jobs

    except httpx.HTTPError as e:
        logger.error(f"Findwork API error: {str(e)}")
        api_stats["findwork"]["status"] = "error"
        return []
    except Exception as e:
        logger.error(f"Findwork unexpected error: {str(e)}")
        api_stats["findwork"]["status"] = "error"
        return []


async def aggregate_jobs_from_all_sources(
    query: str = "software engineer",
    location: str = "United States",
    num_pages: int = 1,
    remote_jobs_only: bool = False
) -> List[Dict[str, Any]]:
    """Fetch and aggregate jobs from all available APIs in parallel"""

    # Fetch from all sources concurrently
    tasks = [
        fetch_jobs_from_jsearch(
            query=query,
            location=location,
            num_pages=num_pages,
            remote_jobs_only=remote_jobs_only
        ),
        fetch_jobs_from_findwork(
            query=query,
            location=location if location != "United States" else None,
            remote_only=remote_jobs_only
        )
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Combine all results
    all_jobs = []
    for result in results:
        if isinstance(result, list):
            all_jobs.extend(result)
        elif isinstance(result, Exception):
            logger.error(f"Error fetching from a source: {str(result)}")

    # Remove duplicates based on title and company
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = (job.get("title", "").lower(), job.get("company", "").lower())
        if key not in seen and key != ("", ""):
            seen.add(key)
            unique_jobs.append(job)

    logger.info(f"Aggregated {len(unique_jobs)} unique jobs from {len(all_jobs)} total results")
    return unique_jobs


@router.get("/search")
async def search_jobs(
    query: str = Query("software engineer", description="Job search query"),
    location: str = Query("United States", description="Job location"),
    num_pages: int = Query(1, ge=1, le=20, description="Number of pages to fetch"),
    remote_jobs_only: bool = Query(False, description="Filter for remote jobs only"),
):
    """
    Search for jobs from all available APIs (JSearch + Findwork)
    """
    jobs = await aggregate_jobs_from_all_sources(
        query=query,
        location=location,
        num_pages=num_pages,
        remote_jobs_only=remote_jobs_only
    )

    return {
        "success": True,
        "count": len(jobs),
        "jobs": jobs,
        "sources": api_stats
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
        "last_fetch_time": last_fetch_time.isoformat() if last_fetch_time else None,
        "sources": api_stats
    }


@router.post("/scrape")
async def trigger_scrape(
    query: str = Query("software engineer", description="Job search query"),
    location: str = Query("United States", description="Job location"),
    num_pages: int = Query(3, ge=1, le=20, description="Number of pages to fetch"),
):
    """
    Manually trigger a job scrape from all sources and update the cache
    """
    global jobs_cache, last_fetch_time

    try:
        jobs = await aggregate_jobs_from_all_sources(
            query=query,
            location=location,
            num_pages=num_pages
        )

        # Update cache
        jobs_cache = jobs
        last_fetch_time = datetime.utcnow()

        return {
            "success": True,
            "message": f"Jobs scraped successfully from multiple sources",
            "count": len(jobs),
            "jobs": jobs,
            "sources": api_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_api_stats():
    """
    Get statistics about API sources
    """
    return {
        "success": True,
        "sources": api_stats,
        "total_cached": len(jobs_cache),
        "last_fetch_time": last_fetch_time.isoformat() if last_fetch_time else None
    }
