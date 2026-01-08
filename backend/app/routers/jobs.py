# backend/app/routers/jobs.py

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
import httpx
import os
from datetime import datetime, timezone
import asyncio
import logging
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
