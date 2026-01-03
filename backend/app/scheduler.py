# backend/app/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def scrape_jobs_task():
    """
    Background task to scrape jobs periodically from all sources
    This will run every hour to fetch fresh job listings
    """
    logger.info("Starting scheduled job scraping from all sources...")

    try:
        # Import here to avoid circular dependency
        from app.routers.jobs import aggregate_jobs_from_all_sources
        import app.routers.jobs as jobs_module

        # Fetch jobs from all sources with default parameters
        jobs = await aggregate_jobs_from_all_sources(
            query="software engineer",
            location="United States",
            num_pages=3,
            remote_jobs_only=False
        )

        # Update the global cache
        jobs_module.jobs_cache = jobs
        jobs_module.last_fetch_time = datetime.utcnow()

        logger.info(f"Successfully scraped {len(jobs)} jobs from all sources at {datetime.utcnow()}")

    except Exception as e:
        logger.error(f"Error during scheduled job scraping: {str(e)}")


def start_scheduler():
    """
    Initialize and start the background scheduler
    """
    # Schedule the job scraping task to run every hour
    scheduler.add_job(
        scrape_jobs_task,
        trigger=IntervalTrigger(hours=1),
        id="scrape_jobs",
        name="Scrape job listings every hour",
        replace_existing=True
    )

    # Run the task immediately on startup
    scheduler.add_job(
        scrape_jobs_task,
        id="scrape_jobs_startup",
        name="Initial job scrape on startup"
    )

    scheduler.start()
    logger.info("Job scraping scheduler started successfully")


def stop_scheduler():
    """
    Stop the scheduler gracefully
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Job scraping scheduler stopped")
