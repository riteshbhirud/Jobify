# backend/app/services/automation_service.py

"""
Service for running job application automation pipelines.
Integrates with BrowserBase for cloud browser automation and the automation_script
package to apply to jobs via different ATS platforms.
"""

import sys
import os
import asyncio
import logging
import tempfile
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from dataclasses import asdict

# Add automation_script to path
AUTOMATION_SCRIPT_DIR = Path(__file__).parent.parent.parent.parent / "automation_script"
sys.path.insert(0, str(AUTOMATION_SCRIPT_DIR))

from playwright.async_api import async_playwright

from openai import OpenAI

from app.database import get_supabase
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize OpenAI client
_openai_client = None

def get_openai_client() -> OpenAI:
    """Get or create OpenAI client."""
    global _openai_client
    if _openai_client is None:
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


# ATS domain to pipeline mapping
ATS_DOMAINS = {
    "greenhouse.io": "greenhouse",
    "lever.co": "lever",
    "workable.com": "workable",
    "myworkdayjobs.com": "workday",
}


def detect_ats_platform(url: str) -> Optional[str]:
    """
    Detect the ATS platform from a job URL.
    Returns the platform name or None if not supported.
    """
    if not url:
        return None
    url_lower = url.lower()
    for domain, platform in ATS_DOMAINS.items():
        if domain in url_lower:
            return platform
    return None


def extract_storage_path_from_url(resume_url: str) -> Optional[Tuple[str, str]]:
    """
    Extract bucket name and file path from a Supabase Storage URL.

    Expected URL format:
    https://{project_id}.supabase.co/storage/v1/object/public/{bucket}/{path}

    Returns:
        Tuple of (bucket_name, file_path) or None if URL is invalid
    """
    if not resume_url:
        return None

    try:
        parsed = urllib.parse.urlparse(resume_url)
        path_parts = parsed.path.split('/')

        # Expected path: /storage/v1/object/public/{bucket}/{user_id}/{filename}
        if len(path_parts) >= 6 and 'storage' in path_parts and 'object' in path_parts:
            # Find index of 'public' or 'sign' (for signed URLs)
            for i, part in enumerate(path_parts):
                if part in ('public', 'sign'):
                    bucket_name = path_parts[i + 1]
                    file_path = '/'.join(path_parts[i + 2:])
                    return (bucket_name, file_path)

        return None
    except Exception as e:
        logger.error(f"Error parsing resume URL {resume_url}: {e}")
        return None


def download_resume_from_storage(resume_url: str, user_id: str) -> Tuple[Optional[str], bool]:
    """
    Download resume from Supabase Storage to a temporary file.

    Args:
        resume_url: The Supabase Storage public URL for the resume
        user_id: The user's ID (for logging)

    Returns:
        Tuple of (temp_file_path, success_flag)
        - On success: (path_to_temp_file, True)
        - On failure: (None, False)
    """
    if not resume_url:
        logger.warning(f"No resume URL provided for user {user_id}")
        return (None, False)

    temp_path = None
    try:
        # Parse the URL to extract bucket and path
        storage_info = extract_storage_path_from_url(resume_url)

        if not storage_info:
            logger.error(f"Could not parse resume URL: {resume_url}")
            return (None, False)

        bucket_name, file_path = storage_info

        # Get the file extension from the path
        file_ext = Path(file_path).suffix or '.pdf'

        # Create temp file with appropriate extension
        temp_file = tempfile.NamedTemporaryFile(
            suffix=file_ext,
            prefix=f"resume_{user_id[:8]}_",
            delete=False  # We'll handle deletion manually
        )
        temp_path = temp_file.name
        temp_file.close()

        # Download from Supabase Storage
        supabase = get_supabase()

        logger.info(f"Downloading resume from bucket '{bucket_name}', path '{file_path}'")

        response = supabase.storage.from_(bucket_name).download(file_path)

        # Write to temp file
        with open(temp_path, 'wb') as f:
            f.write(response)

        logger.info(f"Successfully downloaded resume for user {user_id} to {temp_path}")
        return (temp_path, True)

    except Exception as e:
        logger.error(f"Failed to download resume for user {user_id}: {e}")
        # Clean up temp file if it was created
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass
        return (None, False)


def cleanup_temp_file(file_path: str) -> None:
    """
    Clean up a temporary file.

    Args:
        file_path: Path to the temporary file to delete
    """
    if file_path and os.path.exists(file_path):
        try:
            os.unlink(file_path)
            logger.debug(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp file {file_path}: {e}")


async def generate_cover_letter(
    user_profile: Dict[str, Any],
    job_info: Dict[str, Any]
) -> Tuple[Optional[str], bool]:
    """
    Generate a tailored cover letter using OpenAI.

    The cover letter is designed to:
    - Sound human/student-written, NOT AI-generated
    - Be tailored to the specific job and user's background
    - Be max 1 page (~300-400 words)
    - Have natural imperfections and personal voice

    Args:
        user_profile: User's profile with experience, skills, education
        job_info: Job details including title, company, description

    Returns:
        Tuple of (cover_letter_text, success_flag)
    """
    try:
        client = get_openai_client()

        # Extract key info from user profile
        user_name = f"{user_profile.get('first_name', '')} {user_profile.get('last_name', '')}".strip()
        user_email = user_profile.get('email', '')
        user_phone = user_profile.get('phone', '')
        target_role = user_profile.get('target_role', '')
        skills = user_profile.get('skills', [])
        experience = user_profile.get('experience', [])
        education = user_profile.get('education', [])
        projects = user_profile.get('projects', [])

        # Format experience for prompt
        experience_text = ""
        if experience:
            for exp in experience[:3]:  # Top 3 experiences
                if isinstance(exp, dict):
                    exp_title = exp.get('title', exp.get('position', ''))
                    exp_company = exp.get('company', '')
                    exp_desc = exp.get('description', '')[:200] if exp.get('description') else ''
                    experience_text += f"- {exp_title} at {exp_company}: {exp_desc}\n"

        # Format education
        education_text = ""
        if education:
            for edu in education[:2]:
                if isinstance(edu, dict):
                    degree = edu.get('degree', '')
                    school = edu.get('school', edu.get('institution', ''))
                    education_text += f"- {degree} from {school}\n"

        # Format projects
        projects_text = ""
        if projects:
            for proj in projects[:2]:
                if isinstance(proj, dict):
                    proj_name = proj.get('name', proj.get('title', ''))
                    proj_desc = proj.get('description', '')[:150] if proj.get('description') else ''
                    projects_text += f"- {proj_name}: {proj_desc}\n"

        # Job info
        job_title = job_info.get('title', 'the position')
        company = job_info.get('company', 'your company')
        job_description = job_info.get('description', '')[:1500] if job_info.get('description') else ''

        prompt = f"""Write a cover letter for a job application. The letter must sound like it was written by a real college student or recent graduate - natural, genuine, and definitely NOT AI-generated.

CRITICAL REQUIREMENTS:
- Sound like a real person wrote it, not AI
- Use casual-professional tone, like a motivated student would write
- Include 1-2 minor imperfections (like starting a sentence with "And" or using contractions naturally)
- Be specific about why this role/company interests you (make educated guesses based on company name)
- Connect your actual experience to the job naturally
- Show enthusiasm without being over-the-top
- Keep it under 350 words (fits on one page)
- Don't use clichés like "I am writing to express my interest" or "I believe I would be a great fit"
- Don't list skills robotically - weave them into stories
- Use "I" statements naturally but don't start every sentence with "I"

APPLICANT INFO:
Name: {user_name}
Target Role: {target_role}
Skills: {', '.join(skills[:8]) if skills else 'Not specified'}

Experience:
{experience_text if experience_text else 'Recent graduate / limited experience'}

Education:
{education_text if education_text else 'Not specified'}

Projects:
{projects_text if projects_text else 'None listed'}

JOB INFO:
Position: {job_title}
Company: {company}
Description excerpt: {job_description[:800] if job_description else 'Not provided'}

Write the cover letter now. Start directly with the greeting (Dear Hiring Manager or Dear [Company] Team), no header/address block needed. End with a simple sign-off using the applicant's name."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cost-effective
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that writes authentic, human-sounding cover letters. Your writing should feel like a real college student or recent grad wrote it - natural, genuine, with personality. Never sound robotic or AI-generated."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=600,
            temperature=0.8  # Higher temperature for more natural variation
        )

        cover_letter = response.choices[0].message.content.strip()
        logger.info(f"Generated cover letter for {user_name} applying to {company} ({len(cover_letter)} chars)")

        return (cover_letter, True)

    except Exception as e:
        logger.error(f"Failed to generate cover letter: {e}")
        return (None, False)


def save_cover_letter_to_temp(cover_letter_text: str, user_id: str) -> Tuple[Optional[str], bool]:
    """
    Save cover letter text to a temporary PDF file.

    Args:
        cover_letter_text: The cover letter text content
        user_id: User ID for file naming

    Returns:
        Tuple of (temp_file_path, success_flag)
    """
    temp_path = None
    try:
        # Create temp file with .txt extension (most ATS accept plain text)
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.txt',
            prefix=f"cover_letter_{user_id[:8]}_",
            delete=False,
            mode='w',
            encoding='utf-8'
        )
        temp_path = temp_file.name

        # Write cover letter
        temp_file.write(cover_letter_text)
        temp_file.close()

        logger.info(f"Saved cover letter to {temp_path}")
        return (temp_path, True)

    except Exception as e:
        logger.error(f"Failed to save cover letter: {e}")
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass
        return (None, False)


def get_pipeline_class(platform: str):
    """
    Get the pipeline class for a given platform.
    Import is done lazily to avoid import errors if automation_script is not set up.
    """
    try:
        if platform == "greenhouse":
            from pipelines.greenhouse import GreenhousePipeline
            return GreenhousePipeline
        elif platform == "lever":
            from pipelines.lever import LeverPipeline
            return LeverPipeline
        elif platform == "workable":
            from pipelines.workable import WorkablePipeline
            return WorkablePipeline
        elif platform == "workday":
            from pipelines.workday import WorkdayPipeline
            return WorkdayPipeline
        else:
            return None
    except ImportError as e:
        logger.error(f"Failed to import pipeline for {platform}: {e}")
        return None


def build_user_profile(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a user profile dict compatible with the automation pipelines.
    Maps database user fields to the profile format expected by pipelines.
    """
    profile = {
        # Basic info
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "phone_country_code": user.get("phone_country_code", "us"),

        # Address
        "address": {
            "street": user.get("address_line1", ""),
            "street2": user.get("address_line2", ""),
            "city": user.get("city", ""),
            "state": user.get("state", ""),
            "zip": user.get("zip_code", ""),
            "country": user.get("country", "United States"),
        },

        # Links
        "linkedin_url": user.get("linkedin_url", ""),
        "github_url": user.get("github_url", ""),
        "portfolio_url": user.get("portfolio_url", ""),

        # Professional info
        "target_role": user.get("target_role", ""),
        "experience_level": user.get("experience_level", ""),
        "skills": user.get("skills", []),

        # Education & Experience (JSONB fields)
        "education": user.get("education", []),
        "experience": user.get("experience", []),
        "projects": user.get("projects", []),
        "certifications": user.get("certifications", []),

        # Work preferences
        "remote_preference": user.get("remote_preference", "any"),
        "locations": user.get("locations", []),
        "willing_to_relocate": user.get("willing_to_relocate", True),
        "start_date": user.get("start_date", ""),
        "min_salary": user.get("min_salary"),

        # Authorization
        "is_us_citizen": user.get("is_us_citizen", False),
        "needs_visa_sponsorship": user.get("needs_visa_sponsorship", False),
        "security_clearance": user.get("security_clearance", "No Clearance"),
        "military_experience": user.get("military_experience", False),

        # Demographics (for EEOC questions)
        "demographics": user.get("demographics", {}),

        # Pre-populated answers for common questions
        "common_answers": user.get("common_answers", {}),

        # Portal password (for sites that require account creation)
        "portal_password": "",
    }

    # Decrypt portal_password if present
    raw_pw = user.get("portal_password", "")
    if raw_pw:
        try:
            from app.crypto import decrypt_portal_password
            profile["portal_password"] = decrypt_portal_password(raw_pw)
        except Exception:
            # Fallback for legacy plaintext passwords not yet encrypted
            profile["portal_password"] = raw_pw

    return profile


def build_job_info(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a job info dict compatible with the automation pipelines.
    """
    return {
        "id": job.get("id"),
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "description": job.get("description", ""),
        "apply_url": job.get("apply_url", ""),
        "source": job.get("source", ""),
        "employment_type": job.get("employment_type", ""),
        "experience_level": job.get("experience_level", ""),
        "remote_type": job.get("remote_type", ""),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
    }


def get_browserbase_proxy_settings() -> Dict[str, Any]:
    """
    Resolve BrowserBase proxy configuration for a Webshare external proxy.
    """
    enabled = bool(
        getattr(settings, "browserbase_webshare_proxy_enabled", False)
        or os.getenv("BROWSERBASE_WEBSHARE_PROXY_ENABLED", "").lower() == "true"
    )

    if not enabled:
        return {
            "enabled": False,
            "mode": "none",
            "proxies": None,
            "server": None,
        }

    scheme = getattr(settings, "browserbase_webshare_proxy_scheme", None) or os.getenv("BROWSERBASE_WEBSHARE_PROXY_SCHEME", "http")
    host = getattr(settings, "browserbase_webshare_proxy_host", None) or os.getenv("BROWSERBASE_WEBSHARE_PROXY_HOST")
    port = getattr(settings, "browserbase_webshare_proxy_port", None) or os.getenv("BROWSERBASE_WEBSHARE_PROXY_PORT")
    username = getattr(settings, "browserbase_webshare_proxy_username", None) or os.getenv("BROWSERBASE_WEBSHARE_PROXY_USERNAME")
    password = getattr(settings, "browserbase_webshare_proxy_password", None) or os.getenv("BROWSERBASE_WEBSHARE_PROXY_PASSWORD")
    domain_pattern = getattr(settings, "browserbase_webshare_proxy_domain_pattern", None) or os.getenv("BROWSERBASE_WEBSHARE_PROXY_DOMAIN_PATTERN")
    webshare_api_key = getattr(settings, "webshare_api_key", None) or os.getenv("WEBSHARE_API_KEY")
    webshare_proxy_mode = (getattr(settings, "webshare_proxy_mode", None) or os.getenv("WEBSHARE_PROXY_MODE", "direct")).lower()
    webshare_proxy_country_code = getattr(settings, "webshare_proxy_country_code", None) or os.getenv("WEBSHARE_PROXY_COUNTRY_CODE")
    webshare_proxy_plan_id = getattr(settings, "webshare_proxy_plan_id", None) or os.getenv("WEBSHARE_PROXY_PLAN_ID")

    if webshare_api_key:
        resolved_host, resolved_port, resolved_username, resolved_password = fetch_webshare_proxy_credentials(
            api_key=webshare_api_key,
            mode=webshare_proxy_mode,
            country_code=webshare_proxy_country_code,
            plan_id=webshare_proxy_plan_id,
        )
        server = f"{scheme}://{resolved_host}:{resolved_port}"
        proxy: Dict[str, Any] = {
            "type": "external",
            "server": server,
            "username": resolved_username,
            "password": resolved_password,
        }
        if domain_pattern:
            proxy["domainPattern"] = domain_pattern

        return {
            "enabled": True,
            "mode": f"webshare-{webshare_proxy_mode}-api",
            "proxies": [proxy],
            "server": server,
            "username": resolved_username,
            "password": resolved_password,
        }

    if not (host and port and username and password):
        missing_fields = [
            field_name
            for field_name, field_value in (
                ("BROWSERBASE_WEBSHARE_PROXY_HOST", host),
                ("BROWSERBASE_WEBSHARE_PROXY_PORT", port),
                ("BROWSERBASE_WEBSHARE_PROXY_USERNAME", username),
                ("BROWSERBASE_WEBSHARE_PROXY_PASSWORD", password),
                ("WEBSHARE_API_KEY", webshare_api_key),
            )
            if not field_value
        ]
        raise ValueError(
            "Webshare proxy is enabled but missing required settings: "
            + ", ".join(missing_fields)
        )

    server = f"{scheme}://{host}:{port}"
    proxy: Dict[str, Any] = {
        "type": "external",
        "server": server,
        "username": username,
        "password": password,
    }
    if domain_pattern:
        proxy["domainPattern"] = domain_pattern

    return {
        "enabled": True,
        "mode": "webshare-explicit",
        "proxies": [proxy],
        "server": server,
        "username": username,
        "password": password,
    }


def fetch_webshare_proxy_credentials(
    api_key: str,
    mode: str = "direct",
    country_code: Optional[str] = None,
    plan_id: Optional[str] = None,
) -> Tuple[str, int, str, str]:
    """
    Fetch one working proxy from the Webshare Proxy List API.

    Official docs:
    - https://apidocs.webshare.io/proxy-list
    - https://apidocs.webshare.io/proxy-list/list
    """
    import requests

    if mode not in {"direct", "backbone"}:
        raise ValueError("WEBSHARE_PROXY_MODE must be either 'direct' or 'backbone'")

    params: Dict[str, Any] = {
        "mode": mode,
        "page": 1,
        "page_size": 10,
    }
    if country_code:
        params["country_code__in"] = country_code.upper()
    if plan_id:
        params["plan_id"] = plan_id
    if mode == "direct":
        params["valid"] = "true"

    response = requests.get(
        "https://proxy.webshare.io/api/v2/proxy/list/",
        headers={"Authorization": f"Token {api_key}"},
        params=params,
        timeout=15,
    )
    response.raise_for_status()

    payload = response.json()
    results = payload.get("results") or []
    if not results:
        raise ValueError("Webshare API returned no proxies for the requested filters")

    proxy = next((item for item in results if item.get("username") and item.get("password")), None)
    if not proxy:
        raise ValueError("Webshare API returned proxies, but none included username/password credentials")

    username = proxy.get("username")
    password = proxy.get("password")
    proxy_address = proxy.get("proxy_address")
    port = proxy.get("port")

    if mode == "direct":
        if not proxy_address or not port:
            raise ValueError("Webshare direct proxy response is missing proxy_address or port")
        return proxy_address, int(port), username, password

    # Webshare backbone mode uses p.webshare.io as the connection address.
    # Port is sometimes plan-dependent, so prefer the API value when present.
    if not port:
        port = 80
    return "p.webshare.io", int(port), username, password


async def create_browserbase_session() -> Optional[Dict[str, Any]]:
    """
    Create a BrowserBase session for cloud browser automation.
    Returns session info including connect_url, or None if BrowserBase is not configured.
    """
    browserbase_api_key = getattr(settings, 'browserbase_api_key', None) or os.getenv("BROWSERBASE_API_KEY")
    browserbase_project_id = getattr(settings, 'browserbase_project_id', None) or os.getenv("BROWSERBASE_PROJECT_ID")

    if not browserbase_api_key or not browserbase_project_id:
        logger.warning("BrowserBase credentials not configured")
        return None

    try:
        from browserbase import Browserbase

        bb = Browserbase(api_key=browserbase_api_key)
        proxy_settings = get_browserbase_proxy_settings()
        session_kwargs: Dict[str, Any] = {
            "project_id": browserbase_project_id,
        }

        if proxy_settings["enabled"]:
            session_kwargs["proxies"] = proxy_settings["proxies"]
            logger.info(
                "Creating BrowserBase session with proxy mode=%s server=%s",
                proxy_settings["mode"],
                proxy_settings["server"],
            )
        else:
            logger.info("Creating BrowserBase session without proxies")

        session = bb.sessions.create(**session_kwargs)

        logger.info(
            "Created BrowserBase session: %s proxy_enabled=%s proxy_mode=%s proxy_server=%s",
            session.id,
            proxy_settings["enabled"],
            proxy_settings["mode"],
            proxy_settings["server"],
        )

        return {
            "id": session.id,
            "connect_url": session.connect_url,
            "proxy_mode": proxy_settings["mode"],
            "proxy_enabled": proxy_settings["enabled"],
            "proxy_server": proxy_settings["server"],
        }
    except Exception as e:
        logger.error(f"Failed to create BrowserBase session: {e}")
        return None


def get_local_playwright_proxy_settings() -> Dict[str, Any]:
    """
    Resolve Playwright proxy settings for local Chromium runs.
    Reuses the same Webshare configuration as the BrowserBase path.
    """
    proxy_settings = get_browserbase_proxy_settings()
    if not proxy_settings["enabled"]:
        return {
            "enabled": False,
            "mode": "none",
            "proxy": None,
            "server": None,
        }

    return {
        "enabled": True,
        "mode": proxy_settings["mode"],
        "server": proxy_settings["server"],
        "proxy": {
            "server": proxy_settings["server"],
            "username": proxy_settings.get("username"),
            "password": proxy_settings.get("password"),
        },
    }


def get_local_browser_launch_settings() -> Dict[str, Any]:
    """
    Resolve whether local Playwright should use bundled Chromium, channel=chrome,
    or a specific local Chrome executable.
    """
    executable_path = getattr(settings, "local_browser_executable_path", None) or os.getenv("LOCAL_BROWSER_EXECUTABLE_PATH")
    channel = getattr(settings, "local_browser_channel", None) or os.getenv("LOCAL_BROWSER_CHANNEL")

    if executable_path:
        return {
            "browser_name": "Google Chrome",
            "launch_overrides": {"executable_path": executable_path},
        }

    if channel:
        return {
            "browser_name": f"channel={channel}",
            "launch_overrides": {"channel": channel},
        }

    return {
        "browser_name": "bundled Chromium",
        "launch_overrides": {},
    }


def get_local_browser_cdp_url() -> Optional[str]:
    """Resolve an externally launched Chrome CDP endpoint, if configured."""
    return getattr(settings, "local_browser_cdp_url", None) or os.getenv("LOCAL_BROWSER_CDP_URL")


def get_local_browser_user_data_dir() -> str:
    """
    Resolve the persistent Chrome profile directory for local Playwright runs.
    """
    configured_dir = getattr(settings, "local_browser_user_data_dir", None) or os.getenv("LOCAL_BROWSER_USER_DATA_DIR")
    if configured_dir:
        return configured_dir

    default_dir = Path(__file__).parent.parent.parent / ".playwright-user-data" / "chrome-profile"
    default_dir.mkdir(parents=True, exist_ok=True)
    return str(default_dir)


def get_local_browser_context_settings() -> Dict[str, Any]:
    """
    Use a more realistic default browser context for local runs.
    """
    return {
        "viewport": {"width": 1440, "height": 900},
        "screen": {"width": 1440, "height": 900},
        "locale": "en-US",
        "timezone_id": "America/New_York",
        "color_scheme": "light",
        "device_scale_factor": 2,
        "has_touch": False,
        "is_mobile": False,
        "user_agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
    }


async def apply_local_browser_stealth(context: Any) -> None:
    """
    Best-effort fingerprint hardening for local Playwright-driven Chrome.
    This reduces obvious automation indicators but does not guarantee stealth.
    """
    await context.add_init_script(
        """
        (() => {
          const override = (obj, prop, value) => {
            try {
              Object.defineProperty(obj, prop, {
                get: () => value,
                configurable: true
              });
            } catch (e) {}
          };

          override(Navigator.prototype, 'webdriver', undefined);
          override(Navigator.prototype, 'platform', 'MacIntel');
          override(Navigator.prototype, 'language', 'en-US');
          override(Navigator.prototype, 'languages', ['en-US', 'en']);
          override(Navigator.prototype, 'hardwareConcurrency', 8);
          override(Navigator.prototype, 'deviceMemory', 8);

          if (!window.chrome) {
            Object.defineProperty(window, 'chrome', {
              value: { runtime: {} },
              configurable: true
            });
          }

          const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
          if (originalQuery) {
            window.navigator.permissions.query = (parameters) => (
              parameters && parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters)
            );
          }

          Object.defineProperty(WebGLRenderingContext.prototype, 'getParameter', {
            value: new Proxy(WebGLRenderingContext.prototype.getParameter, {
              apply(target, thisArg, args) {
                const param = args && args[0];
                if (param === 37445) return 'Intel Inc.';
                if (param === 37446) return 'Intel Iris OpenGL Engine';
                return Reflect.apply(target, thisArg, args);
              }
            }),
            configurable: true
          });
        })();
        """
    )


async def launch_local_browser(
    playwright: Any,
    headless: bool,
    log_prefix: str = "",
) -> Tuple[Any, Any, Any, bool, bool]:
    """
    Launch or connect to local Chrome/Chromium with proxy, stealth, and optional persistent profile.

    Returns:
        Tuple of (browser_or_none, context, page, persistent_profile_enabled, externally_managed_browser)
    """
    local_proxy_settings = get_local_playwright_proxy_settings()
    local_browser_settings = get_local_browser_launch_settings()
    local_browser_cdp_url = get_local_browser_cdp_url()
    persistent_profile_enabled = bool(
        getattr(settings, "local_browser_persistent_profile_enabled", True)
        or os.getenv("LOCAL_BROWSER_PERSISTENT_PROFILE_ENABLED", "").lower() == "true"
    )

    if local_browser_cdp_url:
        logger.info(
            "%sConnecting to externally launched Chrome via CDP url=%s",
            log_prefix,
            local_browser_cdp_url,
        )
        if local_proxy_settings["enabled"]:
            logger.info(
                "%sNote: Webshare proxy settings from the app are not injected into an externally launched Chrome. "
                "If you want proxying in CDP mode, launch Chrome itself with the proxy configured.",
                log_prefix,
            )

        browser = await playwright.chromium.connect_over_cdp(local_browser_cdp_url)
        context = browser.contexts[0] if browser.contexts else await browser.new_context(**get_local_browser_context_settings())
        await apply_local_browser_stealth(context)
        page = await context.new_page()
        await log_context_egress_ip(
            context=context,
            proxy_enabled=local_proxy_settings["enabled"],
            proxy_mode="external-cdp",
            proxy_server=local_proxy_settings["server"],
            log_prefix=log_prefix,
        )
        return browser, context, page, False, True

    logger.info(
        "%sUsing local browser=%s with proxy_enabled=%s mode=%s server=%s persistent_profile=%s",
        log_prefix,
        local_browser_settings["browser_name"],
        local_proxy_settings["enabled"],
        local_proxy_settings["mode"],
        local_proxy_settings["server"],
        persistent_profile_enabled,
    )

    launch_kwargs: Dict[str, Any] = {
        "headless": headless,
        "slow_mo": 100,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-dev-shm-usage",
        ],
    }
    launch_kwargs.update(local_browser_settings["launch_overrides"])
    if local_proxy_settings["enabled"]:
        launch_kwargs["proxy"] = local_proxy_settings["proxy"]

    if persistent_profile_enabled:
        user_data_dir = get_local_browser_user_data_dir()
        logger.info("%sLocal browser persistent profile dir=%s", log_prefix, user_data_dir)
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            **launch_kwargs,
            **get_local_browser_context_settings(),
        )
        await apply_local_browser_stealth(context)
        page = context.pages[0] if context.pages else await context.new_page()
        await log_context_egress_ip(
            context=context,
            proxy_enabled=local_proxy_settings["enabled"],
            proxy_mode=local_proxy_settings["mode"],
            proxy_server=local_proxy_settings["server"],
            log_prefix=log_prefix,
        )
        return None, context, page, True, False

    browser = await playwright.chromium.launch(**launch_kwargs)
    context = await browser.new_context(**get_local_browser_context_settings())
    await apply_local_browser_stealth(context)
    page = await context.new_page()
    await log_context_egress_ip(
        context=context,
        proxy_enabled=local_proxy_settings["enabled"],
        proxy_mode=local_proxy_settings["mode"],
        proxy_server=local_proxy_settings["server"],
        log_prefix=log_prefix,
    )
    return browser, context, page, False, False


async def log_context_egress_ip(
    context: Any,
    proxy_enabled: bool,
    proxy_mode: str,
    proxy_server: Optional[str],
    log_prefix: str = "",
) -> None:
    """
    Best-effort check of the public IP seen from inside a browser context.
    This is only for observability and should never break automation.
    """
    try:
        response = await context.request.get(
            "https://api.ipify.org?format=json",
            timeout=15000,
        )
        if not response.ok:
            logger.warning(
                "%sBrowser egress IP check failed with status=%s proxy_enabled=%s mode=%s server=%s",
                log_prefix,
                response.status,
                proxy_enabled,
                proxy_mode,
                proxy_server,
            )
            return

        payload = await response.json()
        observed_ip = payload.get("ip")
        logger.info(
            "%sBrowser egress IP check: observed_ip=%s proxy_enabled=%s mode=%s server=%s",
            log_prefix,
            observed_ip,
            proxy_enabled,
            proxy_mode,
            proxy_server,
        )
    except Exception as e:
        logger.warning(
            "%sBrowser egress IP check error: %s proxy_enabled=%s mode=%s server=%s",
            log_prefix,
            e,
            proxy_enabled,
            proxy_mode,
            proxy_server,
        )


async def run_application_pipeline(
    user_id: str,
    job_id: str,
    application_id: str,
    dry_run: bool = False,
    use_browserbase: bool = True,
    headless: bool = True,
    worker_id: Optional[int] = None,
    generate_cover_letter_flag: bool = False
) -> Dict[str, Any]:
    """
    Run the automation pipeline to apply for a job.

    Args:
        user_id: The user's ID
        job_id: The job's ID
        application_id: The application record ID
        dry_run: If True, fill form but don't submit
        use_browserbase: If True, use BrowserBase cloud browsers (recommended)
        headless: If True and not using BrowserBase, run local browser in headless mode
        worker_id: Optional worker ID for parallel processing (used in logging)
        generate_cover_letter_flag: If True, generate tailored cover letter using OpenAI

    Returns:
        Dict with result information
    """
    supabase = get_supabase()
    browserbase_session = None
    temp_cover_letter_path = None  # Track for cleanup

    # Log prefix for worker identification in parallel mode
    log_prefix = f"[Worker {worker_id}] " if worker_id is not None else ""

    try:
        # Update application status to 'started'
        current_app = supabase.table("applications").select("attempt_count").eq("id", application_id).single().execute()
        current_attempt = current_app.data.get("attempt_count", 0) if current_app.data else 0

        supabase.table("applications").update({
            "status": "started",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "attempt_count": current_attempt + 1
        }).eq("id", application_id).execute()

        # Fetch user data
        user_result = supabase.table("users").select("*").eq("id", user_id).single().execute()
        if not user_result.data:
            raise ValueError(f"User {user_id} not found")
        user = user_result.data

        # Fetch job data
        job_result = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
        if not job_result.data:
            raise ValueError(f"Job {job_id} not found")
        job = job_result.data

        # Get apply URL
        apply_url = job.get("apply_url")
        if not apply_url:
            raise ValueError("Job has no apply URL")

        # Detect ATS platform
        platform = detect_ats_platform(apply_url)
        if not platform:
            raise ValueError(f"Unsupported ATS platform for URL: {apply_url}")

        logger.info(f"{log_prefix}Detected ATS platform: {platform} for URL: {apply_url}")

        # Get pipeline class
        pipeline_class = get_pipeline_class(platform)
        if not pipeline_class:
            raise ValueError(f"Pipeline not available for platform: {platform}")

        # Build profile and job info
        user_profile = build_user_profile(user)
        job_info = build_job_info(job)

        # Download resume from Supabase Storage
        resume_url = user.get("resume_url")
        resume_path = None
        temp_resume_path = None  # Track for cleanup

        if resume_url:
            temp_resume_path, download_success = download_resume_from_storage(
                resume_url=resume_url,
                user_id=user_id
            )
            if download_success:
                resume_path = temp_resume_path
            else:
                logger.warning(f"Could not download resume for user {user_id}, proceeding without resume")
        else:
            logger.warning(f"No resume_url found for user {user_id}")

        # Validate resume exists (required for application)
        if not resume_path:
            raise ValueError(f"Resume is required but could not be obtained for user {user_id}")

        # Verify file exists and has content
        if not os.path.exists(resume_path) or os.path.getsize(resume_path) == 0:
            raise ValueError(f"Downloaded resume file is invalid or empty: {resume_path}")

        # Generate cover letter if enabled (before starting BrowserBase session)
        cover_letter_path = None
        if generate_cover_letter_flag:
            logger.info(f"{log_prefix}Generating tailored cover letter for {job_info.get('title')} at {job_info.get('company')}...")

            cover_letter_text, cl_success = await generate_cover_letter(
                user_profile=user_profile,
                job_info=job_info
            )

            if cl_success and cover_letter_text:
                temp_cover_letter_path, save_success = save_cover_letter_to_temp(
                    cover_letter_text=cover_letter_text,
                    user_id=user_id
                )
                if save_success:
                    cover_letter_path = temp_cover_letter_path
                    logger.info(f"{log_prefix}Cover letter ready: {cover_letter_path}")
                else:
                    logger.warning(f"{log_prefix}Failed to save cover letter, proceeding without it")
            else:
                logger.warning(f"{log_prefix}Failed to generate cover letter, proceeding without it")
        else:
            logger.debug(f"{log_prefix}Cover letter generation disabled")

        # Run the pipeline with BrowserBase or local browser
        async with async_playwright() as p:
            browser = None
            context = None
            page = None
            persistent_local_context = False
            externally_managed_browser = False

            try:
                if use_browserbase:
                    # Try to create BrowserBase session
                    browserbase_session = await create_browserbase_session()

                    if browserbase_session:
                        logger.info(f"Connecting to BrowserBase session: {browserbase_session['id']}")
                        logger.info(
                            "%sBrowserBase proxy configuration: enabled=%s mode=%s server=%s",
                            log_prefix,
                            browserbase_session.get("proxy_enabled"),
                            browserbase_session.get("proxy_mode"),
                            browserbase_session.get("proxy_server"),
                        )

                        # Connect to BrowserBase via CDP
                        browser = await p.chromium.connect_over_cdp(browserbase_session["connect_url"])

                        # Get the default context and page from BrowserBase
                        context = browser.contexts[0]
                        page = context.pages[0] if context.pages else await context.new_page()

                        logger.info(
                            "%sSuccessfully connected to BrowserBase session %s with proxy_enabled=%s mode=%s server=%s",
                            log_prefix,
                            browserbase_session["id"],
                            browserbase_session.get("proxy_enabled"),
                            browserbase_session.get("proxy_mode"),
                            browserbase_session.get("proxy_server"),
                        )
                        await log_context_egress_ip(
                            context=context,
                            proxy_enabled=browserbase_session.get("proxy_enabled", False),
                            proxy_mode=browserbase_session.get("proxy_mode", "none"),
                            proxy_server=browserbase_session.get("proxy_server"),
                            log_prefix=log_prefix,
                        )
                    else:
                        logger.warning("BrowserBase not available, falling back to local browser")
                        use_browserbase = False

                if not use_browserbase or not browser:
                    browser, context, page, persistent_local_context, externally_managed_browser = await launch_local_browser(
                        playwright=p,
                        headless=headless,
                        log_prefix=log_prefix,
                    )

                # Create pipeline instance
                pipeline = pipeline_class(
                    page=page,
                    user_profile=user_profile,
                    job_info=job_info,
                    resume_path=resume_path,
                    cover_letter_path=cover_letter_path,
                    dry_run=dry_run
                )

                # Run the pipeline
                result = await pipeline.run(apply_url)

            finally:
                # Close browser
                if browser and not externally_managed_browser:
                    await browser.close()
                elif persistent_local_context and context:
                    await context.close()

                # Clean up temporary resume file
                if temp_resume_path:
                    cleanup_temp_file(temp_resume_path)

                # Clean up temporary cover letter file
                if temp_cover_letter_path:
                    cleanup_temp_file(temp_cover_letter_path)

        # Update application with result
        update_data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "answers_used": result.answers_used,
        }

        if result.success:
            if result.status == "dry_run":
                update_data["status"] = "dry_run"
            else:
                update_data["status"] = "submitted"
                update_data["submitted_at"] = datetime.now(timezone.utc).isoformat()
                if result.confirmation_number:
                    update_data["confirmation_number"] = result.confirmation_number
        else:
            update_data["status"] = "failed"
            update_data["last_error"] = result.error

        supabase.table("applications").update(update_data).eq("id", application_id).execute()

        return {
            "success": result.success,
            "status": result.status,
            "error": result.error,
            "confirmation_number": result.confirmation_number,
            "screenshot_path": result.screenshot_path,
            "ai_calls_made": result.ai_calls_made,
            "answers_used": result.answers_used,
            "used_browserbase": use_browserbase and browserbase_session is not None,
            "browserbase_session_id": browserbase_session["id"] if browserbase_session else None,
            "improvement_logs": [
                {
                    "question": log.question,
                    "field_type": log.field_type,
                    "options": log.options,
                    "reason": log.reason,
                }
                for log in result.improvement_logs
            ] if result.improvement_logs else []
        }

    except Exception as e:
        logger.error(f"Pipeline error for application {application_id}: {e}")

        # Clean up temporary files if they were created
        if 'temp_resume_path' in locals() and temp_resume_path:
            cleanup_temp_file(temp_resume_path)
        if 'temp_cover_letter_path' in locals() and temp_cover_letter_path:
            cleanup_temp_file(temp_cover_letter_path)

        # Update application status to failed
        supabase.table("applications").update({
            "status": "failed",
            "last_error": str(e),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", application_id).execute()

        return {
            "success": False,
            "status": "failed",
            "error": str(e),
            "used_browserbase": browserbase_session is not None,
            "browserbase_session_id": browserbase_session["id"] if browserbase_session else None
        }


async def process_queued_applications(
    user_id: Optional[str] = None,
    limit: int = 10,
    dry_run: bool = False,
    use_browserbase: bool = True
) -> Dict[str, Any]:
    """
    Process queued applications for a user or all users.

    Args:
        user_id: Optional user ID to process for. If None, processes all queued.
        limit: Maximum number of applications to process
        dry_run: If True, fill forms but don't submit
        use_browserbase: If True, use BrowserBase cloud browsers

    Returns:
        Dict with processing results
    """
    supabase = get_supabase()

    # Fetch queued applications
    query = supabase.table("applications").select(
        "id, user_id, job_id"
    ).eq("status", "queued").limit(limit)

    if user_id:
        query = query.eq("user_id", user_id)

    result = query.execute()

    if not result.data:
        return {
            "success": True,
            "message": "No queued applications found",
            "processed": 0,
            "results": []
        }

    applications = result.data
    results = []

    for app in applications:
        app_result = await run_application_pipeline(
            user_id=app["user_id"],
            job_id=app["job_id"],
            application_id=app["id"],
            dry_run=dry_run,
            use_browserbase=use_browserbase
        )
        results.append({
            "application_id": app["id"],
            **app_result
        })

        # Small delay between applications
        await asyncio.sleep(2)

    successful = sum(1 for r in results if r["success"])

    return {
        "success": True,
        "message": f"Processed {len(results)} applications, {successful} successful",
        "processed": len(results),
        "successful": successful,
        "failed": len(results) - successful,
        "results": results
    }


def is_browserbase_configured() -> bool:
    """
    Check if BrowserBase credentials are configured.
    """
    browserbase_api_key = getattr(settings, 'browserbase_api_key', None) or os.getenv("BROWSERBASE_API_KEY")
    browserbase_project_id = getattr(settings, 'browserbase_project_id', None) or os.getenv("BROWSERBASE_PROJECT_ID")
    return bool(browserbase_api_key and browserbase_project_id)


# ============================================================================
# Browser Session Persistence
# ============================================================================

def extract_ats_domain(url: str) -> Optional[str]:
    """
    Extract the ATS domain from a job URL for session matching.
    """
    if not url:
        return None
    url_lower = url.lower()
    for domain in ATS_DOMAINS.keys():
        if domain in url_lower:
            return domain
    return None


async def get_saved_session(user_id: str, ats_domain: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a saved browser session for a user and ATS domain.
    Returns None if no valid session exists.
    """
    supabase = get_supabase()

    try:
        result = supabase.table("browser_sessions").select(
            "id, cookies, local_storage, session_storage, browserbase_session_id, "
            "is_logged_in, last_used_at, expires_at"
        ).eq("user_id", user_id).eq("ats_domain", ats_domain).single().execute()

        if not result.data:
            return None

        session = result.data

        # Check if session has expired
        if session.get("expires_at"):
            expires_at = datetime.fromisoformat(session["expires_at"].replace("Z", "+00:00"))
            if expires_at < datetime.now(timezone.utc):
                logger.info(f"Session expired for user {user_id} on {ats_domain}")
                # Delete expired session
                supabase.table("browser_sessions").delete().eq("id", session["id"]).execute()
                return None

        logger.info(f"Found saved session for user {user_id} on {ats_domain} (logged_in: {session.get('is_logged_in')})")
        return session

    except Exception as e:
        logger.warning(f"Error fetching saved session: {e}")
        return None


async def save_browser_session(
    user_id: str,
    ats_domain: str,
    cookies: list,
    local_storage: Optional[Dict[str, str]] = None,
    session_storage: Optional[Dict[str, str]] = None,
    browserbase_session_id: Optional[str] = None,
    is_logged_in: bool = False,
    expires_in_hours: int = 24
) -> Optional[str]:
    """
    Save browser session data for a user and ATS domain.
    Returns the session ID on success.
    """
    supabase = get_supabase()

    try:
        expires_at = datetime.now(timezone.utc).replace(
            hour=datetime.now(timezone.utc).hour + expires_in_hours
        )

        # Check if session already exists
        existing = supabase.table("browser_sessions").select("id").eq(
            "user_id", user_id
        ).eq("ats_domain", ats_domain).execute()

        session_data = {
            "user_id": user_id,
            "ats_domain": ats_domain,
            "cookies": cookies,
            "local_storage": local_storage or {},
            "session_storage": session_storage or {},
            "browserbase_session_id": browserbase_session_id,
            "is_logged_in": is_logged_in,
            "last_used_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at.isoformat(),
        }

        if existing.data:
            # Update existing session
            result = supabase.table("browser_sessions").update(session_data).eq(
                "id", existing.data[0]["id"]
            ).execute()
            session_id = existing.data[0]["id"]
            logger.info(f"Updated browser session {session_id} for user {user_id} on {ats_domain}")
        else:
            # Create new session
            result = supabase.table("browser_sessions").insert(session_data).execute()
            session_id = result.data[0]["id"] if result.data else None
            logger.info(f"Created browser session {session_id} for user {user_id} on {ats_domain}")

        return session_id

    except Exception as e:
        logger.error(f"Error saving browser session: {e}")
        return None


async def restore_session_to_context(
    context,
    saved_session: Dict[str, Any]
) -> bool:
    """
    Restore cookies and storage from a saved session to a browser context.
    Returns True if successful.
    """
    try:
        # Restore cookies
        cookies = saved_session.get("cookies", [])
        if cookies:
            await context.add_cookies(cookies)
            logger.info(f"Restored {len(cookies)} cookies to browser context")

        # Note: localStorage and sessionStorage restoration requires page-level access
        # They will be set after navigating to the domain
        return True

    except Exception as e:
        logger.error(f"Error restoring session to context: {e}")
        return False


async def restore_storage_to_page(
    page,
    saved_session: Dict[str, Any],
    url: str
) -> bool:
    """
    Restore localStorage and sessionStorage to a page after navigation.
    Must be called after page.goto() to the target domain.
    """
    try:
        local_storage = saved_session.get("local_storage", {})
        session_storage = saved_session.get("session_storage", {})

        if local_storage:
            for key, value in local_storage.items():
                await page.evaluate(f"localStorage.setItem('{key}', '{value}')")
            logger.info(f"Restored {len(local_storage)} localStorage items")

        if session_storage:
            for key, value in session_storage.items():
                await page.evaluate(f"sessionStorage.setItem('{key}', '{value}')")
            logger.info(f"Restored {len(session_storage)} sessionStorage items")

        return True

    except Exception as e:
        logger.error(f"Error restoring storage to page: {e}")
        return False


async def capture_session_from_context(context, page) -> Dict[str, Any]:
    """
    Capture cookies and storage from the current browser context/page.
    """
    try:
        # Get cookies
        cookies = await context.cookies()

        # Get localStorage and sessionStorage
        local_storage = await page.evaluate("() => { const items = {}; for (let i = 0; i < localStorage.length; i++) { const key = localStorage.key(i); items[key] = localStorage.getItem(key); } return items; }")
        session_storage = await page.evaluate("() => { const items = {}; for (let i = 0; i < sessionStorage.length; i++) { const key = sessionStorage.key(i); items[key] = sessionStorage.getItem(key); } return items; }")

        return {
            "cookies": cookies,
            "local_storage": local_storage,
            "session_storage": session_storage
        }

    except Exception as e:
        logger.error(f"Error capturing session: {e}")
        return {"cookies": [], "local_storage": {}, "session_storage": {}}


async def delete_user_session(user_id: str, ats_domain: Optional[str] = None) -> int:
    """
    Delete saved browser sessions for a user.
    If ats_domain is provided, only delete that specific session.
    Returns the number of sessions deleted.
    """
    supabase = get_supabase()

    try:
        query = supabase.table("browser_sessions").delete().eq("user_id", user_id)

        if ats_domain:
            query = query.eq("ats_domain", ats_domain)

        result = query.execute()
        deleted_count = len(result.data) if result.data else 0

        logger.info(f"Deleted {deleted_count} browser sessions for user {user_id}")
        return deleted_count

    except Exception as e:
        logger.error(f"Error deleting browser sessions: {e}")
        return 0


async def get_user_sessions(user_id: str) -> list:
    """
    Get all saved browser sessions for a user.
    """
    supabase = get_supabase()

    try:
        result = supabase.table("browser_sessions").select(
            "id, ats_domain, is_logged_in, last_used_at, expires_at"
        ).eq("user_id", user_id).execute()

        return result.data or []

    except Exception as e:
        logger.error(f"Error fetching user sessions: {e}")
        return []


# ============================================================================
# Test Pipeline (Direct URL without DB records)
# ============================================================================

async def run_test_pipeline(
    user_id: str,
    apply_url: str,
    job_title: Optional[str] = None,
    company: Optional[str] = None,
    dry_run: bool = True,
    use_browserbase: bool = False,
    headless: bool = True,
    generate_cover_letter_flag: bool = False,
    keep_browser_open: bool = False
) -> Dict[str, Any]:
    """
    Run automation pipeline directly from a URL for testing purposes.
    Does NOT create or update any database records (jobs/applications).

    Args:
        user_id: The user's ID (to fetch profile from DB)
        apply_url: Direct URL to the job application page
        job_title: Optional job title (for cover letter generation)
        company: Optional company name (for cover letter generation)
        dry_run: If True, fill form but don't submit (defaults to True for safety)
        use_browserbase: If True, use BrowserBase cloud browsers
        headless: If True and not using BrowserBase, run local browser in headless mode
        generate_cover_letter_flag: If True, generate tailored cover letter
        keep_browser_open: If True, don't close the browser after pipeline completes (useful for debugging)

    Returns:
        Dict with result information
    """
    supabase = get_supabase()
    browserbase_session = None
    temp_cover_letter_path = None
    temp_resume_path = None

    try:
        # Detect ATS platform
        platform = detect_ats_platform(apply_url)
        if not platform:
            raise ValueError(f"Unsupported ATS platform for URL: {apply_url}. Supported: {', '.join(ATS_DOMAINS.keys())}")

        logger.info(f"[TEST] Detected ATS platform: {platform} for URL: {apply_url}")

        # Get pipeline class
        pipeline_class = get_pipeline_class(platform)
        if not pipeline_class:
            raise ValueError(f"Pipeline not available for platform: {platform}")

        # Fetch user data
        user_result = supabase.table("users").select("*").eq("id", user_id).single().execute()
        if not user_result.data:
            raise ValueError(f"User {user_id} not found")
        user = user_result.data

        # Build user profile
        user_profile = build_user_profile(user)

        # Build minimal job info (not from DB)
        job_info = {
            "id": None,
            "title": job_title or "Test Position",
            "company": company or "Test Company",
            "location": "",
            "description": "",
            "apply_url": apply_url,
            "source": "test",
            "employment_type": "",
            "experience_level": "",
            "remote_type": "",
            "salary_min": None,
            "salary_max": None,
        }

        # Download resume from Supabase Storage
        resume_url = user.get("resume_url")
        resume_path = None

        if resume_url:
            temp_resume_path, download_success = download_resume_from_storage(
                resume_url=resume_url,
                user_id=user_id
            )
            if download_success:
                resume_path = temp_resume_path
            else:
                logger.warning(f"[TEST] Could not download resume for user {user_id}")

        if not resume_path:
            raise ValueError(f"Resume is required but could not be obtained for user {user_id}")

        if not os.path.exists(resume_path) or os.path.getsize(resume_path) == 0:
            raise ValueError(f"Downloaded resume file is invalid or empty: {resume_path}")

        # Generate cover letter if enabled
        cover_letter_path = None
        if generate_cover_letter_flag:
            logger.info(f"[TEST] Generating cover letter for {job_info['title']} at {job_info['company']}...")

            cover_letter_text, cl_success = await generate_cover_letter(
                user_profile=user_profile,
                job_info=job_info
            )

            if cl_success and cover_letter_text:
                temp_cover_letter_path, save_success = save_cover_letter_to_temp(
                    cover_letter_text=cover_letter_text,
                    user_id=user_id
                )
                if save_success:
                    cover_letter_path = temp_cover_letter_path
                    logger.info(f"[TEST] Cover letter ready: {cover_letter_path}")

        # Run the pipeline
        # Note: We don't use 'async with' when keep_browser_open=True because
        # the context manager would close playwright when exiting, killing the browser
        p = await async_playwright().start()
        browser = None
        context = None
        page = None
        persistent_local_context = False
        externally_managed_browser = False

        try:
            if use_browserbase:
                browserbase_session = await create_browserbase_session()

                if browserbase_session:
                    logger.info(f"[TEST] Connecting to BrowserBase session: {browserbase_session['id']}")
                    logger.info(
                        "[TEST] BrowserBase proxy configuration: enabled=%s mode=%s server=%s",
                        browserbase_session.get("proxy_enabled"),
                        browserbase_session.get("proxy_mode"),
                        browserbase_session.get("proxy_server"),
                    )
                    browser = await p.chromium.connect_over_cdp(browserbase_session["connect_url"])
                    context = browser.contexts[0]
                    page = context.pages[0] if context.pages else await context.new_page()
                    logger.info(
                        "[TEST] Successfully connected to BrowserBase session %s with proxy_enabled=%s mode=%s server=%s",
                        browserbase_session["id"],
                        browserbase_session.get("proxy_enabled"),
                        browserbase_session.get("proxy_mode"),
                        browserbase_session.get("proxy_server"),
                    )
                    await log_context_egress_ip(
                        context=context,
                        proxy_enabled=browserbase_session.get("proxy_enabled", False),
                        proxy_mode=browserbase_session.get("proxy_mode", "none"),
                        proxy_server=browserbase_session.get("proxy_server"),
                        log_prefix="[TEST] ",
                    )
                else:
                    logger.warning("[TEST] BrowserBase not available, falling back to local browser")
                    use_browserbase = False

            if not use_browserbase or not browser:
                browser, context, page, persistent_local_context, externally_managed_browser = await launch_local_browser(
                    playwright=p,
                    headless=headless,
                    log_prefix="[TEST] ",
                )

            # Create pipeline instance
            pipeline = pipeline_class(
                page=page,
                user_profile=user_profile,
                job_info=job_info,
                resume_path=resume_path,
                cover_letter_path=cover_letter_path,
                dry_run=dry_run
            )

            # Run the pipeline
            result = await pipeline.run(apply_url)

        finally:
            if keep_browser_open:
                logger.info("[TEST] Keeping browser open for debugging. You must close it manually.")
            else:
                if browser and not externally_managed_browser:
                    await browser.close()
                elif persistent_local_context and context:
                    await context.close()
                await p.stop()
            if temp_resume_path:
                cleanup_temp_file(temp_resume_path)
            if temp_cover_letter_path:
                cleanup_temp_file(temp_cover_letter_path)

        return {
            "success": result.success,
            "status": result.status,
            "error": result.error,
            "confirmation_number": result.confirmation_number,
            "screenshot_path": result.screenshot_path,
            "ai_calls_made": result.ai_calls_made,
            "answers_used": result.answers_used,
            "platform": platform,
            "used_browserbase": use_browserbase and browserbase_session is not None,
            "browserbase_session_id": browserbase_session["id"] if browserbase_session else None,
            "dry_run": dry_run,
            "improvement_logs": [
                {
                    "question": log.question,
                    "field_type": log.field_type,
                    "options": log.options,
                    "reason": log.reason,
                }
                for log in result.improvement_logs
            ] if result.improvement_logs else []
        }

    except Exception as e:
        logger.error(f"[TEST] Pipeline error: {e}")

        # Clean up temp files
        if temp_resume_path:
            cleanup_temp_file(temp_resume_path)
        if temp_cover_letter_path:
            cleanup_temp_file(temp_cover_letter_path)

        return {
            "success": False,
            "status": "failed",
            "error": str(e),
            "platform": detect_ats_platform(apply_url),
            "used_browserbase": browserbase_session is not None,
            "browserbase_session_id": browserbase_session["id"] if browserbase_session else None,
            "dry_run": dry_run
        }
