# backend/app/routers/jobs.py

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
import httpx
import os
from datetime import datetime, timezone
import asyncio
import logging
import math
from app.database import get_supabase
from app.config import get_settings
from openai import OpenAI

router = APIRouter()
logger = logging.getLogger(__name__)

# API configurations
JSEARCH_API_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")

FINDWORK_API_URL = "https://findwork.dev/api/jobs/"
FINDWORK_API_KEY = os.getenv("FINDWORK_API_KEY", "")

ACTIVEJOBSDB_API_URL = "https://active-jobs-db.p.rapidapi.com/active-ats-7d"
ACTIVEJOBSDB_API_KEY = os.getenv("ACTIVEJOBSDB_API_KEY", "")

# Initialize OpenAI client
settings = get_settings()
openai_client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

# In-memory cache for jobs (since we're not using a database)
jobs_cache: List[Dict[str, Any]] = []
last_fetch_time: Optional[datetime] = None
api_stats: Dict[str, Any] = {
    "jsearch": {"count": 0, "last_fetch": None, "status": "unknown"},
    "findwork": {"count": 0, "last_fetch": None, "status": "unknown"},
    "activejobsdb": {"count": 0, "last_fetch": None, "status": "unknown"},
}


def safe_int_conversion(value: Any) -> Optional[int]:
    """
    Safely convert a value to an integer, handling strings with decimals.
    Returns None if conversion fails.
    """
    if value is None:
        return None
    try:
        # If it's already an int, return it
        if isinstance(value, int):
            return value
        # If it's a float or string with decimal, convert to float first then int
        if isinstance(value, (float, str)):
            return int(float(value))
        return None
    except (ValueError, TypeError):
        return None


def is_allowed_ats_platform(url: str) -> bool:
    """
    Check if a URL belongs to one of the allowed ATS platforms.
    Allowed platforms: Greenhouse, Lever, Workable, Workday
    """
    if not url:
        return False

    url_lower = url.lower()
    allowed_platforms = [
        "greenhouse.io",
        "lever.co",
        "workable.com",
        "myworkdayjobs.com",
    ]

    return any(platform in url_lower for platform in allowed_platforms)


def create_job_embedding_text(job: Dict[str, Any]) -> str:
    """
    Create a text representation of a job for embedding generation.
    This combines key fields that are important for semantic search.
    """
    parts = []

    # Add title
    if job.get("title"):
        parts.append(f"Title: {job.get('title')}")

    # Add company
    if job.get("company"):
        parts.append(f"Company: {job.get('company')}")

    # Add location
    if job.get("location"):
        parts.append(f"Location: {job.get('location')}")

    # Add employment type
    if job.get("employment_type"):
        parts.append(f"Employment Type: {job.get('employment_type')}")

    # Add remote type
    if job.get("remote_type"):
        parts.append(f"Remote: {job.get('remote_type')}")

    # Add experience level
    if job.get("experience_level"):
        parts.append(f"Experience Level: {job.get('experience_level')}")

    # Add salary range if available
    if job.get("salary_min") or job.get("salary_max"):
        salary_parts = []
        if job.get("salary_min"):
            salary_parts.append(f"${job.get('salary_min'):,}")
        if job.get("salary_max"):
            salary_parts.append(f"${job.get('salary_max'):,}")
        if salary_parts:
            parts.append(f"Salary Range: {' - '.join(salary_parts)}")

    # Add description (truncated to first 500 characters to avoid token limits)
    if job.get("description"):
        description = job.get("description")[:500]
        parts.append(f"Description: {description}")

    return "\n".join(parts)


async def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate an embedding vector for the given text using OpenAI's text-embedding-3-small model.
    Returns None if embedding generation fails or OpenAI client is not configured.
    """
    if not openai_client:
        logger.warning("OpenAI client not configured. Skipping embedding generation.")
        return None

    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            encoding_format="float"
        )
        embedding = response.data[0].embedding
        logger.debug(f"Generated embedding with {len(embedding)} dimensions")
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        return None


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
                # Filter out Indeed jobs
                job_url = job.get("job_apply_link", "")
                if "indeed.com" in job_url.lower():
                    logger.debug(f"Filtering out Indeed job: {job.get('job_title')} at {job.get('employer_name')}")
                    continue

                # Filter to only include allowed ATS platforms
                if not is_allowed_ats_platform(job_url):
                    logger.debug(f"Filtering out non-ATS job: {job.get('job_title')} at {job.get('employer_name')} - URL: {job_url}")
                    continue

                # Filter out jobs without description
                if not job.get("job_description"):
                    logger.debug(f"Filtering out job without description: {job.get('job_title')} at {job.get('employer_name')}")
                    continue

                normalized_job = {
                    "job_id": f"jsearch_{job.get('job_id')}",
                    "title": job.get("job_title"),
                    "company": job.get("employer_name"),
                    "location": job.get("job_city") or job.get("job_state") or job.get("job_country"),
                    "description": job.get("job_description"),
                    "apply_link": job.get("job_apply_link"),
                    "employment_type": job.get("job_employment_type"),
                    "salary_min": safe_int_conversion(job.get("job_min_salary")),
                    "salary_max": safe_int_conversion(job.get("job_max_salary")),
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
            api_stats["jsearch"]["last_fetch"] = datetime.now(timezone.utc).isoformat()
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
                # Filter out Indeed jobs
                job_url = job.get("url", "")
                if "indeed.com" in job_url.lower():
                    logger.debug(f"Filtering out Indeed job: {job.get('role')} at {job.get('company_name')}")
                    continue

                # Filter out jobs without description
                if not job.get("text"):
                    logger.debug(f"Filtering out job without description: {job.get('role')} at {job.get('company_name')}")
                    continue

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
            api_stats["findwork"]["last_fetch"] = datetime.now(timezone.utc).isoformat()
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


async def fetch_jobs_from_activejobsdb(
    query: str = "software engineer",
    location: Optional[str] = None,
    remote_only: bool = False,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Fetch jobs from ActiveJobsDB API
    """
    global api_stats

    logger.info(f"ActiveJobsDB fetch called with query='{query}', location='{location}', limit={limit}")

    if not ACTIVEJOBSDB_API_KEY:
        logger.warning("ActiveJobsDB API key not configured")
        api_stats["activejobsdb"]["status"] = "not_configured"
        return []

    logger.info(f"ActiveJobsDB API key configured: {ACTIVEJOBSDB_API_KEY[:10]}...")

    headers = {
        "X-RapidAPI-Key": ACTIVEJOBSDB_API_KEY,
        "X-RapidAPI-Host": "active-jobs-db.p.rapidapi.com"
    }

    # Build query parameters
    params = {
        "limit": str(limit),
        "offset": "0",
        "include_ai": "true",  # Include AI-extracted insights
        "description_type": "text",  # Get text description
        "source": "workday,greenhouse,workable,lever.co"  # Filter by ATS platforms
    }

    # Add title filter (wrap in quotes for exact phrase matching)
    if query:
        params["title_filter"] = f'"{query}"'

    # Add location filter (wrap in quotes for exact matching)
    if location:
        # ActiveJobsDB supports OR syntax for multiple locations
        if location == "United States":
            params["location_filter"] = '"United States"'
        else:
            params["location_filter"] = f'"{location}"'

    # Add remote filter
    if remote_only:
        params["remote"] = "true"

    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Making request to ActiveJobsDB: {ACTIVEJOBSDB_API_URL}")
            logger.info(f"Request params: {params}")

            response = await client.get(
                ACTIVEJOBSDB_API_URL,
                headers=headers,
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"ActiveJobsDB response status: {response.status_code}")
            logger.info(f"ActiveJobsDB response type: {type(data)}")
            logger.info(f"ActiveJobsDB raw response length: {len(data) if isinstance(data, list) else 'not a list'}")

            jobs = []
            results = data if isinstance(data, list) else []

            if not results:
                logger.warning("ActiveJobsDB returned empty results or non-list response")

            for job in results:
                # Note: ATS platform filtering is done at the API level via the "source" parameter
                # No need to filter out Indeed or check ATS platforms here

                # Parse location from locations_derived
                location_str = None
                if job.get("locations_derived"):
                    location_str = job.get("locations_derived")[0] if job.get("locations_derived") else None
                elif job.get("cities_derived") and job.get("regions_derived") and job.get("countries_derived"):
                    city = job.get("cities_derived")[0] if job.get("cities_derived") else ""
                    region = job.get("regions_derived")[0] if job.get("regions_derived") else ""
                    country = job.get("countries_derived")[0] if job.get("countries_derived") else ""
                    location_str = f"{city}, {region}, {country}".strip(", ")

                # Parse salary from salary_raw (JSON string) and AI-extracted salary
                salary_min = None
                salary_max = None
                salary_currency = "USD"
                salary_period = "year"

                # Try salary_raw first
                if job.get("salary_raw"):
                    try:
                        import json
                        salary_data = json.loads(job.get("salary_raw"))
                        value = salary_data.get("value", {})
                        if isinstance(value, dict):
                            salary_min = safe_int_conversion(value.get("minValue"))
                            salary_max = safe_int_conversion(value.get("maxValue"))
                        currency = salary_data.get("currency")
                        if currency:
                            salary_currency = currency
                    except:
                        pass

                # Fall back to AI-extracted salary if salary_raw doesn't exist
                if not salary_min and not salary_max:
                    salary_min = safe_int_conversion(job.get("ai_salary_minvalue"))
                    salary_max = safe_int_conversion(job.get("ai_salary_maxvalue"))
                    if not salary_min and not salary_max:
                        # Try single salary value
                        single_salary = safe_int_conversion(job.get("ai_salary_value"))
                        if single_salary:
                            salary_min = single_salary
                            salary_max = single_salary

                    # Get currency and period from AI fields
                    if job.get("ai_salary_currency"):
                        salary_currency = job.get("ai_salary_currency")
                    if job.get("ai_salary_unittext"):
                        unit_text = job.get("ai_salary_unittext", "").upper()
                        salary_period = unit_text.lower() if unit_text in ["HOUR", "DAY", "WEEK", "MONTH", "YEAR"] else "year"

                # Parse employment type (use AI field if available)
                employment_type = None
                if job.get("ai_employment_type") and isinstance(job.get("ai_employment_type"), list):
                    employment_type = ", ".join(job.get("ai_employment_type"))
                elif job.get("employment_type") and isinstance(job.get("employment_type"), list):
                    employment_type = job.get("employment_type")[0] if job.get("employment_type") else None

                # Determine remote status using AI work arrangement
                is_remote = False
                ai_work_arrangement = job.get("ai_work_arrangement", "").lower()
                if "remote" in ai_work_arrangement or job.get("remote_derived", False):
                    is_remote = True

                # Get description (text or html)
                description = job.get("description_text") or job.get("description_html") or job.get("description")

                # Filter out jobs without description
                if not description:
                    logger.debug(f"Filtering out job without description: {job.get('title')} at {job.get('organization')}")
                    continue

                normalized_job = {
                    "job_id": f"activejobsdb_{job.get('id')}",
                    "title": job.get("title"),
                    "company": job.get("organization"),
                    "location": location_str,
                    "description": description,
                    "apply_link": job.get("url"),
                    "employment_type": employment_type,
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "salary_raw": job.get("salary_raw"),  # Pass through raw salary JSON
                    "salary_currency": salary_currency,
                    "salary_period": salary_period,
                    "posted_date": job.get("date_posted"),
                    "is_remote": is_remote,
                    "experience_level": job.get("ai_experience_level"),
                    "logo": job.get("organization_logo"),
                    "publisher": job.get("source"),
                    "source": "ActiveJobsDB",
                    # Hiring manager information
                    "hiring_manager_name": job.get("ai_hiring_manager_name"),
                    "hiring_manager_email_address": job.get("ai_hiring_manager_email_address"),
                    # Additional AI-enriched fields
                    "ai_work_arrangement": job.get("ai_work_arrangement"),
                    "ai_benefits": job.get("ai_benefits"),
                    "ai_key_skills": job.get("ai_key_skills"),
                    "ai_keywords": job.get("ai_keywords"),
                    "ai_taxonomies": job.get("ai_taxonomies_a"),
                    "ai_visa_sponsorship": job.get("ai_visa_sponsorship"),
                    "ai_education_requirements": job.get("ai_education_requirements"),
                    "ai_core_responsibilities": job.get("ai_core_responsibilities"),
                    "ai_requirements_summary": job.get("ai_requirements_summary"),
                    # Company information
                    "company_url": job.get("organization_url"),
                    "company_domain": job.get("domain_derived"),
                    # Location details
                    "cities": job.get("cities_derived"),
                    "regions": job.get("regions_derived"),
                    "countries": job.get("countries_derived"),
                }
                jobs.append(normalized_job)

            api_stats["activejobsdb"]["count"] = len(jobs)
            api_stats["activejobsdb"]["last_fetch"] = datetime.now(timezone.utc).isoformat()
            api_stats["activejobsdb"]["status"] = "success"
            logger.info(f"Fetched {len(jobs)} jobs from ActiveJobsDB")
            return jobs

    except httpx.HTTPError as e:
        logger.error(f"ActiveJobsDB API error: {str(e)}")
        api_stats["activejobsdb"]["status"] = "error"
        return []
    except Exception as e:
        logger.error(f"ActiveJobsDB unexpected error: {str(e)}")
        api_stats["activejobsdb"]["status"] = "error"
        return []


async def aggregate_jobs_from_all_sources(
    query: str = "software engineer",
    location: str = "United States",
    num_pages: int = 1,
    remote_jobs_only: bool = False,
    use_activejobsdb: bool = False
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
        # Findwork API temporarily disabled
        # fetch_jobs_from_findwork(
        #     query=query,
        #     location=location if location != "United States" else None,
        #     remote_only=remote_jobs_only
        # )
    ]

    # Only include ActiveJobsDB if explicitly enabled
    if use_activejobsdb:
        tasks.append(
            fetch_jobs_from_activejobsdb(
                query=query,
                location=location,  # Pass location as-is, including "United States"
                remote_only=remote_jobs_only,
                limit=100  # Fetch up to 100 jobs per request
            )
        )

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


async def save_jobs_to_database(jobs: List[Dict[str, Any]]) -> int:
    """
    Save jobs to Supabase database, skipping duplicates based on external_id.
    Generates embeddings for each job before saving.
    Returns the number of new jobs inserted.
    """
    if not jobs:
        return 0

    supabase = get_supabase()
    inserted_count = 0
    duplicate_count = 0

    # Get existing external_ids to check for duplicates before inserting
    try:
        job_ids = [job.get("job_id") for job in jobs if job.get("job_id")]
        existing_jobs = supabase.table("jobs").select("external_id").in_("external_id", job_ids).execute()
        existing_ids = {job["external_id"] for job in existing_jobs.data} if existing_jobs.data else set()
    except Exception as e:
        logger.warning(f"Could not fetch existing job IDs: {e}. Will handle duplicates during insert.")
        existing_ids = set()

    for job in jobs:
        job_id = job.get("job_id")

        # Skip if we know it already exists
        if job_id in existing_ids:
            duplicate_count += 1
            logger.debug(f"Skipping known duplicate job: {job_id}")
            continue

        try:
            # Generate embedding for the job
            embedding = None
            if openai_client:
                embedding_text = create_job_embedding_text(job)
                embedding = await generate_embedding(embedding_text)
                if embedding:
                    logger.debug(f"Generated embedding for job: {job.get('title')}")

            # Map the API response to database schema
            db_job = {
                "external_id": job_id,
                "title": job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "description": job.get("description"),
                "apply_url": job.get("apply_link"),
                "source": job.get("publisher") or job.get("source", "unknown"),  # Use publisher (ATS platform) as source
                "employment_type": job.get("employment_type"),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "salary_raw": str(job.get("salary_raw")) if job.get("salary_raw") else None,  # Store raw salary data
                "posted_at": job.get("posted_date"),
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "remote_type": job.get("ai_work_arrangement") or ("remote" if job.get("is_remote") else None),  # Use AI work arrangement if available
                "experience_level": job.get("experience_level"),
                "visa_sponsorship": job.get("ai_visa_sponsorship"),  # From AI fields
                "company_normalized": job.get("company_domain"),  # Use domain as normalized company
                "location_normalized": job.get("location"),  # Could be enhanced with more parsing
                "hiring_manager_name": job.get("hiring_manager_name"),  # Hiring manager name from AI
                "hiring_manager_email_address": job.get("hiring_manager_email_address"),  # Hiring manager email from AI
                "embedding": embedding,  # Add the embedding vector
            }

            # Try to insert
            result = supabase.table("jobs").insert(db_job).execute()

            if result.data:
                inserted_count += 1
                logger.debug(f"Inserted job: {job.get('title')} at {job.get('company')}")

        except Exception as e:
            # Log error but continue with other jobs
            error_msg = str(e)
            # Check for duplicate errors (409 Conflict, duplicate key, unique constraint)
            if any(indicator in error_msg.lower() for indicator in ["409", "conflict", "duplicate key", "unique constraint", "already exists"]):
                duplicate_count += 1
                logger.debug(f"Skipping duplicate job: {job_id}")
            else:
                logger.error(f"Error inserting job {job_id}: {error_msg}")

    logger.info(f"Job insertion complete: {inserted_count} new jobs inserted, {duplicate_count} duplicates skipped out of {len(jobs)} total")
    return inserted_count


@router.get("/search")
async def search_jobs(
    query: str = Query("software engineer", description="Job search query"),
    location: str = Query("United States", description="Job location"),
    num_pages: int = Query(1, ge=1, le=20, description="Number of pages to fetch"),
    remote_jobs_only: bool = Query(False, description="Filter for remote jobs only"),
    use_activejobsdb: bool = Query(False, description="Include ActiveJobsDB API"),
):
    """
    Search for jobs from all available APIs (JSearch + Findwork + optionally ActiveJobsDB)
    """
    jobs = await aggregate_jobs_from_all_sources(
        query=query,
        location=location,
        num_pages=num_pages,
        remote_jobs_only=remote_jobs_only,
        use_activejobsdb=use_activejobsdb
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
    Get cached jobs from the database (or memory cache as fallback)
    """
    global jobs_cache, last_fetch_time

    try:
        # Try to fetch from database first
        supabase = get_supabase()
        result = supabase.table("jobs").select("*").order("ingested_at", desc=True).limit(1000).execute()

        if result.data:
            # Map database schema back to API format for frontend compatibility
            db_jobs = []
            for job in result.data:
                api_job = {
                    "job_id": job.get("external_id"),
                    "title": job.get("title"),
                    "company": job.get("company"),
                    "location": job.get("location"),
                    "description": job.get("description"),
                    "apply_link": job.get("apply_url"),
                    "employment_type": job.get("employment_type"),
                    "salary_min": job.get("salary_min"),
                    "salary_max": job.get("salary_max"),
                    "salary_currency": "USD",  # Default since not stored in DB
                    "salary_period": "year",  # Default since not stored in DB
                    "posted_date": job.get("posted_at"),
                    "is_remote": job.get("remote_type") == "remote",
                    "experience_level": None,  # Not stored in DB
                    "logo": None,  # Not stored in DB
                    "publisher": job.get("source"),
                    "source": job.get("source")
                }
                db_jobs.append(api_job)

            logger.info(f"Fetched {len(db_jobs)} jobs from database")

            return {
                "success": True,
                "count": len(db_jobs),
                "jobs": db_jobs,
                "last_fetch_time": last_fetch_time.isoformat() if last_fetch_time else None,
                "sources": api_stats
            }
    except Exception as e:
        logger.error(f"Error fetching from database, falling back to cache: {str(e)}")

    # Fallback to in-memory cache if database fails
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
    use_activejobsdb: bool = Query(False, description="Include ActiveJobsDB API"),
):
    """
    Manually trigger a job scrape from all sources, save to database, and update the cache
    """
    global jobs_cache, last_fetch_time

    try:
        jobs = await aggregate_jobs_from_all_sources(
            query=query,
            location=location,
            num_pages=num_pages,
            use_activejobsdb=use_activejobsdb
        )

        # Save jobs to database
        inserted_count = await save_jobs_to_database(jobs)

        # Update cache
        jobs_cache = jobs
        last_fetch_time = datetime.now(timezone.utc)

        return {
            "success": True,
            "message": f"Jobs scraped successfully from multiple sources",
            "count": len(jobs),
            "inserted_count": inserted_count,
            "jobs": jobs,
            "sources": api_stats
        }
    except Exception as e:
        logger.error(f"Error in trigger_scrape: {str(e)}")
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


@router.get("/test-activejobsdb")
async def test_activejobsdb():
    """
    Test endpoint to verify ActiveJobsDB API integration
    """
    logger.info("Testing ActiveJobsDB API integration...")

    jobs = await fetch_jobs_from_activejobsdb(
        query="software engineer",
        location="United States",
        remote_only=False,
        limit=10
    )

    return {
        "success": True,
        "count": len(jobs),
        "jobs": jobs,
        "api_key_configured": bool(ACTIVEJOBSDB_API_KEY),
        "status": api_stats["activejobsdb"]["status"]
    }


@router.post("/regenerate-embeddings")
async def regenerate_embeddings(
    limit: int = Query(100, ge=1, le=1000, description="Number of jobs to process"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Regenerate embeddings for existing jobs in the database.
    Useful for backfilling embeddings or updating them with a new model.
    """
    if not openai_client:
        raise HTTPException(
            status_code=503,
            detail="OpenAI client not configured. Please set OPENAI_API_KEY environment variable."
        )

    try:
        supabase = get_supabase()

        # Fetch jobs that don't have embeddings or all jobs if you want to regenerate
        result = supabase.table("jobs")\
            .select("id, external_id, title, company, location, description, employment_type, remote_type, experience_level, salary_min, salary_max")\
            .is_("embedding", "null")\
            .order("ingested_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        if not result.data:
            return {
                "success": True,
                "message": "No jobs found without embeddings",
                "processed_count": 0
            }

        jobs = result.data
        processed_count = 0
        error_count = 0

        for job in jobs:
            try:
                # Create embedding text from database job fields
                job_data = {
                    "title": job.get("title"),
                    "company": job.get("company"),
                    "location": job.get("location"),
                    "description": job.get("description"),
                    "employment_type": job.get("employment_type"),
                    "remote_type": job.get("remote_type"),
                    "experience_level": job.get("experience_level"),
                    "salary_min": job.get("salary_min"),
                    "salary_max": job.get("salary_max"),
                }

                embedding_text = create_job_embedding_text(job_data)
                embedding = await generate_embedding(embedding_text)

                if embedding:
                    # Update the job with the embedding
                    supabase.table("jobs")\
                        .update({"embedding": embedding})\
                        .eq("id", job["id"])\
                        .execute()

                    processed_count += 1
                    logger.info(f"Updated embedding for job: {job.get('title')} at {job.get('company')}")
                else:
                    error_count += 1
                    logger.warning(f"Failed to generate embedding for job: {job.get('title')}")

            except Exception as e:
                error_count += 1
                logger.error(f"Error processing job {job.get('id')}: {str(e)}")

        return {
            "success": True,
            "message": f"Regenerated embeddings for {processed_count} jobs",
            "processed_count": processed_count,
            "error_count": error_count,
            "total_jobs": len(jobs)
        }

    except Exception as e:
        logger.error(f"Error in regenerate_embeddings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    Returns a value between -1 and 1, where 1 means identical direction.
    Handles both list and string formats (from database).
    """
    # Parse string embeddings if needed (from Supabase vector type)
    import json

    if isinstance(vec1, str):
        try:
            vec1 = json.loads(vec1)
        except:
            logger.error(f"Failed to parse vec1 as JSON: {vec1[:100]}")
            return 0.0

    if isinstance(vec2, str):
        try:
            vec2 = json.loads(vec2)
        except:
            logger.error(f"Failed to parse vec2 as JSON: {vec2[:100]}")
            return 0.0

    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    # Calculate dot product
    dot_product = sum(a * b for a, b in zip(vec1, vec2))

    # Calculate magnitudes
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    # Avoid division by zero
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def calculate_match_score(
    job: Dict[str, Any],
    user: Dict[str, Any],
    similarity_score: float
) -> tuple[float, Dict[str, Any]]:
    """
    Calculate a comprehensive match score between a job and user.
    Returns (final_score, match_reasons)

    The score combines:
    - Embedding similarity (70% weight)
    - Hard filters and preference matching (30% weight)
    """
    reasons = {
        "embedding_similarity": round(similarity_score, 3),
        "filters_passed": [],
        "filters_failed": [],
        "preference_matches": []
    }

    # Start with embedding similarity as base (0-1 scale)
    base_score = similarity_score

    # Hard filters that disqualify a match
    filters_passed = True

    # Visa sponsorship check
    if user.get("needs_visa_sponsorship") and job.get("visa_sponsorship") is False:
        reasons["filters_failed"].append("Requires visa sponsorship but job doesn't offer it")
        filters_passed = False
    elif user.get("needs_visa_sponsorship") and job.get("visa_sponsorship") is True:
        reasons["filters_passed"].append("Visa sponsorship available")

    # Minimum salary check
    user_min_salary = user.get("min_salary")
    job_max_salary = job.get("salary_max")
    if user_min_salary and job_max_salary:
        if job_max_salary < user_min_salary:
            reasons["filters_failed"].append(f"Salary max ${job_max_salary:,} below user minimum ${user_min_salary:,}")
            filters_passed = False
        else:
            reasons["filters_passed"].append(f"Salary range meets minimum requirement")

    # Excluded companies check
    excluded_companies = user.get("excluded_companies", [])
    if excluded_companies and job.get("company"):
        job_company_lower = job.get("company").lower()
        for excluded in excluded_companies:
            if excluded.lower() in job_company_lower:
                reasons["filters_failed"].append(f"Company '{job.get('company')}' is in excluded list")
                filters_passed = False
                break

    # If hard filters failed, return 0 score
    if not filters_passed:
        return 0.0, reasons

    # Preference matching (adds bonus points)
    preference_score = 0.0
    max_preference_score = 0.3  # Max 30% bonus

    # Remote preference matching
    user_remote_pref = user.get("remote_preference", "any")
    job_remote_type = job.get("remote_type", "").lower() if job.get("remote_type") else ""

    if user_remote_pref == "remote" and "remote" in job_remote_type:
        preference_score += 0.1
        reasons["preference_matches"].append("Remote work preference matched")
    elif user_remote_pref == "hybrid" and "hybrid" in job_remote_type:
        preference_score += 0.1
        reasons["preference_matches"].append("Hybrid work preference matched")
    elif user_remote_pref == "onsite" and ("onsite" in job_remote_type or "office" in job_remote_type):
        preference_score += 0.1
        reasons["preference_matches"].append("On-site work preference matched")

    # Preferred companies check
    preferred_companies = user.get("preferred_companies", [])
    if preferred_companies and job.get("company"):
        job_company_lower = job.get("company").lower()
        for preferred in preferred_companies:
            if preferred.lower() in job_company_lower:
                preference_score += 0.1
                reasons["preference_matches"].append(f"Preferred company '{job.get('company')}'")
                break

    # Location matching
    user_locations = user.get("locations", [])
    job_location = job.get("location", "")
    if user_locations and job_location:
        for user_loc in user_locations:
            if user_loc.lower() in job_location.lower():
                preference_score += 0.05
                reasons["preference_matches"].append(f"Location preference matched: {user_loc}")
                break

    # Experience level matching
    user_exp_level = user.get("experience_level", "").lower()
    job_exp_level = job.get("experience_level", "").lower() if job.get("experience_level") else ""
    if user_exp_level and job_exp_level and user_exp_level in job_exp_level:
        preference_score += 0.05
        reasons["preference_matches"].append(f"Experience level matched: {user_exp_level}")

    # Cap preference score
    preference_score = min(preference_score, max_preference_score)

    # Calculate final score (embedding similarity weighted 70%, preferences 30%)
    final_score = (base_score * 0.7) + preference_score

    # Ensure score is between 0 and 1
    final_score = max(0.0, min(1.0, final_score))

    return final_score, reasons


@router.post("/match")
async def match_jobs_to_users(
    user_id: Optional[str] = Query(None, description="Match jobs for a specific user. If not provided, matches for all active users."),
    min_match_score: Optional[float] = Query(None, description="Minimum match score (0-1). If not provided, uses user's min_match_score setting."),
    limit_per_user: int = Query(50, ge=1, le=500, description="Maximum number of matches per user"),
    force_rematch: bool = Query(False, description="Force rematching even if already matched")
):
    """
    Match jobs to users using embedding similarity and preference matching.
    Creates entries in the applications table with status='matched'.

    Matching algorithm:
    1. Fetches users with embeddings (all active users or specific user)
    2. Fetches jobs with embeddings
    3. Calculates cosine similarity between user and job embeddings
    4. Applies filters (visa sponsorship, salary, excluded companies)
    5. Adds preference bonuses (remote preference, preferred companies, location)
    6. Saves matches to applications table with match_score and match_reasons
    """
    try:
        supabase = get_supabase()

        # Fetch users with embeddings
        users_query = supabase.table("users").select(
            "id, email, first_name, last_name, embedding, min_match_score, "
            "needs_visa_sponsorship, min_salary, excluded_companies, preferred_companies, "
            "locations, remote_preference, experience_level, is_active"
        ).not_.is_("embedding", "null")

        # Filter by user_id if provided
        if user_id:
            users_query = users_query.eq("id", user_id)
        else:
            # Only match for active users
            users_query = users_query.eq("is_active", True)

        users_result = users_query.execute()

        if not users_result.data:
            return {
                "success": False,
                "message": "No users found with embeddings" + (f" for user_id {user_id}" if user_id else ""),
                "matched_count": 0
            }

        users = users_result.data
        logger.info(f"Found {len(users)} user(s) to match")

        # Fetch jobs with embeddings
        jobs_result = supabase.table("jobs").select(
            "id, external_id, title, company, location, description, "
            "employment_type, salary_min, salary_max, visa_sponsorship, "
            "remote_type, experience_level, apply_url, posted_at, embedding"
        ).not_.is_("embedding", "null").execute()

        if not jobs_result.data:
            return {
                "success": False,
                "message": "No jobs found with embeddings",
                "matched_count": 0
            }

        jobs = jobs_result.data
        logger.info(f"Found {len(jobs)} job(s) with embeddings")

        # Track statistics
        total_matches = 0
        total_skipped = 0
        user_match_details = []

        # Process each user
        for user in users:
            user_id_current = user["id"]
            user_min_score = min_match_score if min_match_score is not None else user.get("min_match_score", 0.70)
            user_embedding = user.get("embedding")

            if not user_embedding:
                logger.warning(f"User {user_id_current} has no embedding, skipping")
                continue

            logger.info(f"Matching jobs for user {user.get('email')} (min_score: {user_min_score})")

            # Get existing applications for this user to avoid duplicates
            existing_apps = set()
            if not force_rematch:
                existing_result = supabase.table("applications").select("job_id").eq("user_id", user_id_current).execute()
                existing_apps = {app["job_id"] for app in existing_result.data} if existing_result.data else set()
                logger.info(f"User has {len(existing_apps)} existing applications")

            # Calculate match scores for all jobs
            job_matches = []
            for job in jobs:
                job_id = job["id"]
                job_embedding = job.get("embedding")

                # Skip if already applied (unless force_rematch)
                if not force_rematch and job_id in existing_apps:
                    total_skipped += 1
                    continue

                if not job_embedding:
                    continue

                # Calculate cosine similarity
                similarity = cosine_similarity(user_embedding, job_embedding)

                # Calculate comprehensive match score with filters and preferences
                match_score, match_reasons = calculate_match_score(job, user, similarity)

                # Only include matches above threshold
                if match_score >= user_min_score:
                    job_matches.append({
                        "job_id": job_id,
                        "job_title": job.get("title"),
                        "company": job.get("company"),
                        "match_score": match_score,
                        "match_reasons": match_reasons
                    })

            # Sort by match score and limit
            job_matches.sort(key=lambda x: x["match_score"], reverse=True)
            job_matches = job_matches[:limit_per_user]

            logger.info(f"Found {len(job_matches)} matches for user {user.get('email')}")

            # Insert into applications table
            inserted = 0
            for match in job_matches:
                try:
                    application = {
                        "user_id": user_id_current,
                        "job_id": match["job_id"],
                        "match_score": match["match_score"],
                        "match_reasons": match["match_reasons"],
                        "status": "matched",
                        "matched_at": datetime.now(timezone.utc).isoformat()
                    }

                    supabase.table("applications").insert(application).execute()
                    inserted += 1

                except Exception as e:
                    error_msg = str(e)
                    # Skip if duplicate
                    if any(indicator in error_msg.lower() for indicator in ["duplicate", "unique constraint", "already exists"]):
                        total_skipped += 1
                        logger.debug(f"Skipped duplicate application for user {user_id_current}, job {match['job_id']}")
                    else:
                        logger.error(f"Error inserting application: {error_msg}")

            total_matches += inserted
            user_match_details.append({
                "user_id": user_id_current,
                "email": user.get("email"),
                "matches_found": len(job_matches),
                "matches_inserted": inserted
            })

        return {
            "success": True,
            "message": f"Matched {total_matches} jobs across {len(users)} user(s)",
            "total_matches_created": total_matches,
            "total_skipped": total_skipped,
            "users_processed": len(users),
            "user_details": user_match_details
        }

    except Exception as e:
        logger.error(f"Error in match_jobs_to_users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/match/debug")
async def debug_match_status():
    """
    Debug endpoint to check the status of users and jobs for matching.
    Shows how many users/jobs have embeddings and their active status.
    """
    try:
        supabase = get_supabase()

        # Count total users
        all_users = supabase.table("users").select("id, email, embedding, is_active, onboarding_completed").execute()
        total_users = len(all_users.data) if all_users.data else 0

        # Count users with embeddings
        users_with_embeddings = [u for u in all_users.data if u.get("embedding")] if all_users.data else []

        # Count active users with embeddings
        active_users_with_embeddings = [
            u for u in users_with_embeddings
            if u.get("is_active")
        ]

        # Count jobs
        all_jobs = supabase.table("jobs").select("id, embedding").execute()
        total_jobs = len(all_jobs.data) if all_jobs.data else 0

        # Count jobs with embeddings
        jobs_with_embeddings = [j for j in all_jobs.data if j.get("embedding")] if all_jobs.data else []

        # User details for debugging
        user_details = []
        for user in users_with_embeddings[:10]:  # Show first 10
            user_details.append({
                "id": user.get("id"),
                "email": user.get("email"),
                "has_embedding": user.get("embedding") is not None,
                "is_active": user.get("is_active"),
                "onboarding_completed": user.get("onboarding_completed")
            })

        return {
            "success": True,
            "users": {
                "total": total_users,
                "with_embeddings": len(users_with_embeddings),
                "active_with_embeddings": len(active_users_with_embeddings),
                "sample_users": user_details
            },
            "jobs": {
                "total": total_jobs,
                "with_embeddings": len(jobs_with_embeddings)
            },
            "ready_to_match": len(active_users_with_embeddings) > 0 and len(jobs_with_embeddings) > 0,
            "issues": []
        }

    except Exception as e:
        logger.error(f"Error in debug_match_status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/match/scores/{user_id}")
async def get_match_scores(
    user_id: str,
    limit: int = Query(20, ge=1, le=100, description="Number of top matches to return")
):
    """
    Debug endpoint to see actual match scores for a user without saving to database.
    Shows top N matches sorted by score.
    """
    try:
        supabase = get_supabase()

        # Fetch user with all relevant fields
        user_result = supabase.table("users").select(
            "id, email, first_name, last_name, embedding, min_match_score, "
            "needs_visa_sponsorship, min_salary, excluded_companies, preferred_companies, "
            "locations, remote_preference, experience_level"
        ).eq("id", user_id).execute()

        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")

        user = user_result.data[0]

        if not user.get("embedding"):
            raise HTTPException(status_code=400, detail="User has no embedding")

        user_min_score = user.get("min_match_score", 0.70)
        user_embedding = user.get("embedding")

        # Fetch jobs with embeddings
        jobs_result = supabase.table("jobs").select(
            "id, external_id, title, company, location, description, "
            "employment_type, salary_min, salary_max, visa_sponsorship, "
            "remote_type, experience_level, apply_url, posted_at, embedding"
        ).not_.is_("embedding", "null").limit(200).execute()

        if not jobs_result.data:
            raise HTTPException(status_code=404, detail="No jobs found with embeddings")

        jobs = jobs_result.data

        # Calculate scores for all jobs
        all_scores = []
        for job in jobs:
            job_embedding = job.get("embedding")
            if not job_embedding:
                continue

            # Calculate cosine similarity
            similarity = cosine_similarity(user_embedding, job_embedding)

            # Calculate comprehensive match score
            match_score, match_reasons = calculate_match_score(job, user, similarity)

            all_scores.append({
                "job_id": job["id"],
                "title": job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "salary_range": f"${job.get('salary_min'):,} - ${job.get('salary_max'):,}" if job.get("salary_min") and job.get("salary_max") else None,
                "match_score": round(match_score, 4),
                "match_reasons": match_reasons,
                "meets_threshold": match_score >= user_min_score
            })

        # Sort by match score
        all_scores.sort(key=lambda x: x["match_score"], reverse=True)

        # Get top matches
        top_matches = all_scores[:limit]

        # Count matches above threshold
        above_threshold = [s for s in all_scores if s["meets_threshold"]]

        return {
            "success": True,
            "user": {
                "id": user["id"],
                "email": user.get("email"),
                "min_match_score": user_min_score
            },
            "stats": {
                "total_jobs_evaluated": len(all_scores),
                "matches_above_threshold": len(above_threshold),
                "highest_score": all_scores[0]["match_score"] if all_scores else 0,
                "lowest_score": all_scores[-1]["match_score"] if all_scores else 0
            },
            "top_matches": top_matches
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_match_scores: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/match/diagnose/{user_id}")
async def diagnose_embeddings(user_id: str):
    """
    Diagnose embedding issues for a specific user.
    Checks embedding dimensions and formats for user and sample jobs.
    """
    try:
        supabase = get_supabase()

        # Fetch user embedding
        user_result = supabase.table("users").select("id, email, embedding").eq("id", user_id).execute()

        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")

        user = user_result.data[0]
        user_embedding = user.get("embedding")

        if not user_embedding:
            raise HTTPException(status_code=400, detail="User has no embedding")

        # Fetch a few sample jobs
        jobs_result = supabase.table("jobs").select("id, title, company, embedding").not_.is_("embedding", "null").limit(3).execute()

        if not jobs_result.data:
            raise HTTPException(status_code=404, detail="No jobs found with embeddings")

        # Analyze embeddings
        user_embedding_info = {
            "type": type(user_embedding).__name__,
            "is_list": isinstance(user_embedding, list),
            "length": len(user_embedding) if isinstance(user_embedding, (list, str)) else None,
            "first_5_values": user_embedding[:5] if isinstance(user_embedding, list) else str(user_embedding)[:100],
            "sample_value_type": type(user_embedding[0]).__name__ if isinstance(user_embedding, list) and len(user_embedding) > 0 else None
        }

        job_embeddings_info = []
        for job in jobs_result.data[:3]:
            job_emb = job.get("embedding")
            job_embeddings_info.append({
                "job_id": job["id"],
                "title": job.get("title"),
                "company": job.get("company"),
                "embedding_type": type(job_emb).__name__,
                "is_list": isinstance(job_emb, list),
                "length": len(job_emb) if isinstance(job_emb, (list, str)) else None,
                "first_5_values": job_emb[:5] if isinstance(job_emb, list) else str(job_emb)[:100],
                "sample_value_type": type(job_emb[0]).__name__ if isinstance(job_emb, list) and len(job_emb) > 0 else None
            })

        # Try to calculate similarity with first job
        similarity_test = None
        similarity_error = None
        if jobs_result.data:
            try:
                job_emb = jobs_result.data[0].get("embedding")
                similarity_test = cosine_similarity(user_embedding, job_emb)
            except Exception as e:
                similarity_error = str(e)

        return {
            "success": True,
            "user_id": user_id,
            "user_email": user.get("email"),
            "user_embedding": user_embedding_info,
            "sample_job_embeddings": job_embeddings_info,
            "similarity_test": {
                "result": similarity_test,
                "error": similarity_error
            },
            "diagnosis": {
                "dimensions_match": user_embedding_info["length"] == job_embeddings_info[0]["length"] if job_embeddings_info else None,
                "types_match": user_embedding_info["type"] == job_embeddings_info[0]["embedding_type"] if job_embeddings_info else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in diagnose_embeddings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
