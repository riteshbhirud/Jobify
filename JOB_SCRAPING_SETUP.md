# Job Scraping Setup Guide

This guide explains how to set up and use the automated job scraping feature in Jobify.

## Overview

The job scraping feature aggregates job postings from **multiple APIs** to provide comprehensive job listings:
- **JSearch API** (RapidAPI) - Real-time jobs from Google for Jobs and other sources
- **Findwork API** - Developer-focused job board (free tier available)

Jobs are automatically fetched every hour and displayed in a clean, filterable table on the Job Board page.

## Features

- **Multi-Source Aggregation**: Fetches from multiple APIs in parallel for maximum coverage
- **Automatic Deduplication**: Removes duplicate listings across sources
- **Automatic Scraping**: Jobs are scraped every hour in the background
- **Manual Refresh**: Users can manually trigger a job scrape
- **Real-time Data**: Fetches jobs from Google for Jobs, Findwork, and other sources
- **Rich Metadata**: Includes salary, location, employment type, remote status, and more
- **Source Tracking**: See which API each job came from
- **API Health Monitoring**: View status of each data source
- **Beautiful UI**: Jobs displayed in a responsive table with company logos

## Setup Instructions

### 1. Get Your API Keys

#### JSearch API (Required)
1. Go to [RapidAPI JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
2. Sign up for a free RapidAPI account if you don't have one
3. Subscribe to the JSearch API (there's a free tier available)
4. Copy your API key from the "X-RapidAPI-Key" header

#### Findwork API (Optional - works without it)
1. Go to [Findwork Developers](https://findwork.dev/developers/)
2. Create an account if needed
3. Generate an API token (optional - the API works without authentication but has lower rate limits)

### 2. Configure Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Edit your `.env` file and add the API keys:
   ```env
   # Required
   JSEARCH_API_KEY=your_actual_jsearch_key_here

   # Optional - leave empty if you don't have one
   FINDWORK_API_KEY=your_findwork_key_here_or_leave_empty

   APP_ENV=development
   ```

3. Install Python dependencies:
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

- `GET /api/jobs/search` - Search for jobs from all sources with custom parameters
  - Query params: `query`, `location`, `num_pages`, `remote_jobs_only`
  - Returns: Jobs from JSearch + Findwork, deduplicated

- `GET /api/jobs/cached` - Get cached jobs from the last scrape
  - Includes API source statistics

- `POST /api/jobs/scrape` - Manually trigger a job scrape from all sources
  - Query params: `query`, `location`, `num_pages`
  - Fetches from all APIs in parallel

- `GET /api/jobs/stats` - Get statistics about API sources
  - Shows health status and job counts per source

### Example API Calls

```bash
# Search for remote Python jobs from all sources
curl "http://localhost:8000/api/jobs/search?query=python%20developer&remote_jobs_only=true&num_pages=2"

# Get cached jobs with source statistics
curl "http://localhost:8000/api/jobs/cached"

# Trigger manual scrape from all sources
curl -X POST "http://localhost:8000/api/jobs/scrape?query=software%20engineer&num_pages=3"

# Get API health statistics
curl "http://localhost:8000/api/jobs/stats"
```

## Customization

### Change Scraping Parameters

Edit `backend/app/scheduler.py` to customize what jobs are scraped:

```python
async def scrape_jobs_task():
    jobs = await aggregate_jobs_from_all_sources(
        query="data scientist",           # Change job type
        location="New York, NY",          # Change location
        num_pages=5,                      # Change number of results (for JSearch)
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

1. Check that your JSearch API key is correct in `.env`
2. Look at backend logs for errors
3. Make sure the backend is running on port 8000
4. Try manually triggering a scrape with the "Refresh Jobs" button
5. Check the "Data Sources" section on the job board to see API health status

### API Rate Limits

**JSearch API (RapidAPI):**
- Free tier has limits (usually 100-500 requests/month)
- If you hit the limit:
  - Wait for the limit to reset (usually monthly)
  - Reduce scraping frequency
  - Upgrade your RapidAPI plan

**Findwork API:**
- Works without authentication but has rate limits
- Add an API key to increase rate limits
- Generally more generous limits than JSearch

### One API failing

The system is designed to work even if one API fails:
- Jobs will still appear from working APIs
- Check the "Data Sources" section to see which APIs are working
- Error status will show a red dot
- Check backend logs for specific error messages

### CORS Errors

If you see CORS errors in the browser console:
1. Ensure the backend is running on `localhost:8000`
2. Check that CORS is properly configured in `backend/app/main.py`

## How It Works

### Multi-API Aggregation

The system uses a smart aggregation strategy:

1. **Parallel Fetching**: Both APIs are called simultaneously using `asyncio.gather()`
2. **Error Handling**: If one API fails, the other continues working
3. **Deduplication**: Jobs are deduplicated based on title + company name
4. **Source Tracking**: Each job is tagged with its source API
5. **Statistics**: Real-time monitoring of each API's health and contribution

### Adding More APIs

Want to add more job APIs? Here's how:

1. Create a new fetch function in `backend/app/routers/jobs.py`:
```python
async def fetch_jobs_from_newapi(...):
    # Implement API call
    # Return normalized job list
```

2. Add it to the aggregation in `aggregate_jobs_from_all_sources()`:
```python
tasks = [
    fetch_jobs_from_jsearch(...),
    fetch_jobs_from_findwork(...),
    fetch_jobs_from_newapi(...),  # Add here
]
```

3. Update `api_stats` dictionary to track the new source

## Next Steps

- Add filtering on the frontend (by location, salary, remote status)
- Add ability to save/favorite jobs
- Integrate with the auto-apply feature
- Add email notifications for new matching jobs
- Store jobs in a database for historical tracking
