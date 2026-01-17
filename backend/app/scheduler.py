# backend/app/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_matching_pipeline_task():
    """
    Background task to run the matching pipeline periodically.
    Matches all active users to their top jobs and queues for automation.
    """
    logger.info("Starting scheduled matching pipeline...")

    try:
        from app.services.matching_pipeline import run_full_pipeline

        result = await run_full_pipeline(
            top_matches_per_user=3,
            min_match_score=0.3,
            max_applications=20,
            dry_run=False,
            use_browserbase=True
        )

        logger.info(f"Matching pipeline completed: {result.get('matching', {}).get('applications_created', 0)} applications created")

    except Exception as e:
        logger.error(f"Error during scheduled matching pipeline: {str(e)}")


async def scrape_jobs_task(use_activejobsdb: bool = False):
    """
    Background task to scrape jobs periodically from all sources
    This will run every hour to fetch fresh job listings
    """
    logger.info(f"Starting scheduled job scraping from all sources (ActiveJobsDB: {use_activejobsdb})...")

    try:
        # Import here to avoid circular dependency
        from app.routers.jobs import aggregate_jobs_from_all_sources, save_jobs_to_database
        import app.routers.jobs as jobs_module

        # Fetch jobs from all sources with default parameters
        jobs = await aggregate_jobs_from_all_sources(
            query="software engineer",
            location="United States",
            num_pages=3,
            remote_jobs_only=False,
            use_activejobsdb=use_activejobsdb
        )

        # Save jobs to database
        inserted_count = await save_jobs_to_database(jobs)

        # Update the global cache
        jobs_module.jobs_cache = jobs
        jobs_module.last_fetch_time = datetime.now(timezone.utc)

        logger.info(f"Successfully scraped {len(jobs)} jobs ({inserted_count} new) from all sources at {datetime.now(timezone.utc)}")

    except Exception as e:
        logger.error(f"Error during scheduled job scraping: {str(e)}")


def start_scheduler():
    """
    Initialize and start the background scheduler
    """
    # Schedule the job scraping task to run every hour (without ActiveJobsDB)
    scheduler.add_job(
        scrape_jobs_task,
        trigger=IntervalTrigger(hours=1),
        id="scrape_jobs",
        name="Scrape job listings every hour (JSearch only)",
        replace_existing=True,
        kwargs={"use_activejobsdb": False}
    )

    # Schedule ActiveJobsDB scraping to run once per day
    scheduler.add_job(
        scrape_jobs_task,
        trigger=IntervalTrigger(days=1),
        id="scrape_jobs_activejobsdb",
        name="Scrape job listings daily (includes ActiveJobsDB)",
        replace_existing=True,
        kwargs={"use_activejobsdb": True}
    )

    # Run the task immediately on startup (with ActiveJobsDB)
    scheduler.add_job(
        scrape_jobs_task,
        id="scrape_jobs_startup",
        name="Initial job scrape on startup (includes ActiveJobsDB)",
        kwargs={"use_activejobsdb": True}
    )

    # Optional: Schedule the matching pipeline to run periodically
    # Uncomment to enable automatic matching every 6 hours
    # scheduler.add_job(
    #     run_matching_pipeline_task,
    #     trigger=IntervalTrigger(hours=6),
    #     id="matching_pipeline",
    #     name="Run matching pipeline every 6 hours",
    #     replace_existing=True
    # )

    scheduler.start()
    logger.info("Job scraping scheduler started successfully")
    logger.info("- JSearch only: Every hour")
    logger.info("- ActiveJobsDB: Once per day")
    logger.info("- Matching pipeline: Manual trigger via /api/pipeline/run (or uncomment scheduler for automatic runs)")


def stop_scheduler():
    """
    Stop the scheduler gracefully
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Job scraping scheduler stopped")
