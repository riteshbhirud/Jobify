# backend/app/main.py

import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.routers import users, jobs, automation, pipeline, payments

settings = get_settings()
logger = logging.getLogger(__name__)

IS_VERCEL = bool(os.environ.get("VERCEL"))

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://applyafk-frontend.vercel.app",
    "https://www.applyafk.com",
    "https://applyafk.com",
]

app = FastAPI(
    title="Job Auto Apply API",
    version="1.0.0"
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return JSON with CORS headers."""
    origin = request.headers.get("origin", "")
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}")

    headers = {}
    if origin in ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=headers,
    )


# CORS - allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(automation.router, prefix="/api/automation", tags=["automation"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])


# Start the background scheduler (only for non-serverless environments)
@app.on_event("startup")
async def startup_event():
    if not IS_VERCEL:
        from app.scheduler import start_scheduler
        start_scheduler()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Job Auto Apply API", "docs": "/docs"}