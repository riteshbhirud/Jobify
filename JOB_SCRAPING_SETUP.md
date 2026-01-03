# Job Scraping Setup Guide

This guide explains how to set up and use the automated job scraping feature in Jobify.

## Overview

The job scraping feature uses the **JSearch API** (via OpenWeb Ninja/RapidAPI) to automatically fetch job postings every hour. The jobs are displayed in a clean, filterable table on the Job Board page.

## Features

- **Automatic Scraping**: Jobs are scraped every hour in the background
- **Manual Refresh**: Users can manually trigger a job scrape
- **Real-time Data**: Fetches jobs from Google for Jobs and other public sources
- **Rich Metadata**: Includes salary, location, employment type, remote status, and more
- **Beautiful UI**: Jobs displayed in a responsive table with company logos

## Setup Instructions

### 1. Get Your JSearch API Key

1. Go to [RapidAPI JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
2. Sign up for a free RapidAPI account if you don't have one
3. Subscribe to the JSearch API (there's a free tier available)
4. Copy your API key from the "X-RapidAPI-Key" header

### 2. Configure Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a `.env` file (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and add your API key:
   ```env
   JSEARCH_API_KEY=your_actual_api_key_here
   APP_ENV=development
   ```

4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Start the Backend

```bash
# Make sure you're in the backend directory
cd backend

# Run the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will start on `http://localhost:8000`

### 4. Start the Frontend

In a new terminal:

```bash
cd frontend
npm install  # if you haven't already
npm run dev
```

The frontend will start on `http://localhost:3000`

## Usage

### Accessing the Job Board

1. Log in to your Jobify account
2. Click on "Job Board" in the sidebar navigation (💼 icon)
3. The page will show cached jobs from the last scrape

### Manual Refresh

Click the "Refresh Jobs" button to manually trigger a new job scrape. This fetches fresh data from the JSearch API.

### Automatic Scraping

Jobs are automatically scraped every hour. The scheduler starts when the backend server starts. You'll see logs like:

```
INFO: Job scraping scheduler started successfully
INFO: Starting scheduled job scraping...
INFO: Successfully scraped 30 jobs at 2026-01-02 20:00:00
```

## API Endpoints

### Backend Endpoints

- `GET /api/jobs/search` - Search for jobs with custom parameters
  - Query params: `query`, `location`, `num_pages`, `employment_types`, `remote_jobs_only`

- `GET /api/jobs/cached` - Get cached jobs from the last scrape

- `POST /api/jobs/scrape` - Manually trigger a job scrape
  - Query params: `query`, `location`, `num_pages`

### Example API Call

```bash
# Search for remote Python jobs
curl "http://localhost:8000/api/jobs/search?query=python%20developer&remote_jobs_only=true&num_pages=2"

# Get cached jobs
curl "http://localhost:8000/api/jobs/cached"

# Trigger manual scrape
curl -X POST "http://localhost:8000/api/jobs/scrape?query=software%20engineer&num_pages=3"
```

## Customization

### Change Scraping Parameters

Edit `backend/app/scheduler.py` to customize what jobs are scraped:

```python
async def scrape_jobs_task():
    jobs = await fetch_jobs_from_jsearch(
        query="data scientist",           # Change job type
        location="New York, NY",          # Change location
        num_pages=5,                      # Change number of results
        remote_jobs_only=True            # Only remote jobs
    )
```

### Change Scraping Frequency

Edit the interval in `backend/app/scheduler.py`:

```python
scheduler.add_job(
    scrape_jobs_task,
    trigger=IntervalTrigger(hours=2),  # Change from 1 hour to 2 hours
    # ... rest of config
)
```

## Troubleshooting

### No jobs appearing

1. Check that your API key is correct in `.env`
2. Look at backend logs for errors
3. Make sure the backend is running on port 8000
4. Try manually triggering a scrape with the "Refresh Jobs" button

### API Rate Limits

The free tier of JSearch API has limits. If you hit the limit:
- Wait for the limit to reset (usually monthly)
- Reduce scraping frequency
- Upgrade your RapidAPI plan

### CORS Errors

If you see CORS errors in the browser console:
1. Ensure the backend is running on `localhost:8000`
2. Check that CORS is properly configured in `backend/app/main.py`

## API Alternatives

If you want to try other job APIs, you can swap out the JSearch implementation:

1. **Mantiks Job Postings API** - Better for enriched metadata
2. **APIJobs.dev** - Enterprise-grade with advanced filtering
3. **Simple Job Data API** - No throttle limits
4. **Findwork API** - Developer-focused jobs

Just update the API calls in `backend/app/routers/jobs.py` to match the new API's format.

## Next Steps

- Add filtering on the frontend (by location, salary, remote status)
- Add ability to save/favorite jobs
- Integrate with the auto-apply feature
- Add email notifications for new matching jobs
- Store jobs in a database for historical tracking
