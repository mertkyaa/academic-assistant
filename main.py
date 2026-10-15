import json
import os
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from query_utils import preprocess_query
from paper_search import search_papers
from filter_agent import run_filter_agent
from evidence_agent import run_evidence_agent
from summary_agent import run_summary_agent
from database import init_db, get_cached_search, save_to_cache


logger = logging.getLogger("academic-assistant")

# Allowed frontend origins. Since the built React app is served from this same
# service, the deployed app is same-origin; we still allow the Railway domain
# explicitly plus the local Vite dev server for development.
ALLOWED_ORIGINS = [
    "https://academic-assistant-production-35e4.up.railway.app",
    # Vite dev server.
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # Vite preview server, which the E2E suite builds and serves the frontend
    # from. The built bundle calls this deployed API, so that origin needs to
    # be allowed or the search test fails CORS preflight.
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

# Topic bounds. The minimum mirrors the frontend's own check so a direct API
# call can't burn a Claude pipeline run (and a rate-limit slot) on "a" or "".
# The maximum keeps a pathological payload out of the model's context.
MIN_TOPIC_LEN = 5
MAX_TOPIC_LEN = 200


# Pydantic models
class SearchRequest(BaseModel):
    topic: str

    @field_validator("topic")
    @classmethod
    def valid_topic(cls, v):
        v = v.strip()
        if len(v) < MIN_TOPIC_LEN:
            raise ValueError(
                f"Topic must be at least {MIN_TOPIC_LEN} characters"
            )
        if len(v) > MAX_TOPIC_LEN:
            raise ValueError(
                f"Topic must be at most {MAX_TOPIC_LEN} characters"
            )
        return v


class SearchResponse(BaseModel):
    topic: str
    synthesis: dict
    paper_count: int


# App
app = FastAPI()

# Per-IP rate limiting is the only access control: search is open to everyone,
# so this is what protects the expensive pipeline (3 Claude calls per request)
# from abuse. Can be disabled for test runs via RATE_LIMIT_ENABLED=false.
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() != "false"
limiter = Limiter(key_func=get_remote_address, enabled=RATE_LIMIT_ENABLED)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Academic Assistant API is running"}


# Search is open to everyone — no accounts, no login. The per-IP limit is the
# cost guard, so it must count real client IPs: see --proxy-headers in the
# Procfile, which makes get_remote_address see the true IP behind Railway.
@app.post("/api/search", response_model=SearchResponse)
@limiter.limit("10/hour;30/day")
def search_endpoint(request: Request, payload: SearchRequest):
    # Cache on the raw user input so identical searches hit the cache without
    # paying for query normalization; normalize only on a cache miss.
    cache_key = payload.topic.strip().lower()

    try:
        cached = get_cached_search(cache_key)
    except Exception as e:
        # A cache read failure must not take the whole search down — just run
        # the pipeline as if it were a miss.
        logger.exception("Cache read failed for topic=%r: %s", cache_key, e)
        cached = None

    if cached:
        synthesis = json.loads(cached["synthesis"])
        # Only trust a cached entry that is actually a synthesis object. A past
        # bug stored `null` here when the summary agent returned invalid JSON,
        # which then made this topic fail for as long as the entry lived. Treat
        # anything unusable as a miss so the entry heals itself on this run.
        if isinstance(synthesis, dict) and synthesis:
            return SearchResponse(
                topic=payload.topic,
                synthesis=synthesis,
                paper_count=cached["paper_count"],
            )
        logger.warning("Discarding unusable cache entry for topic=%r", cache_key)

    try:
        topic = preprocess_query(payload.topic)
        papers = search_papers(topic)
        scored = run_filter_agent(papers, topic)
    except Exception as e:
        # Log the real error server-side; return a generic message so we don't
        # leak internal details (stack traces, DB errors) to the client.
        logger.exception("Search failed for topic=%r: %s", payload.topic, e)
        raise HTTPException(status_code=500, detail="Search failed. Please try again.")

    # Nothing relevant survived scoring (off-topic query, or all three paper
    # sources were down). Tell the user plainly instead of running the two
    # remaining agents on an empty list and caching a hollow "no papers were
    # provided" synthesis for a week.
    if not scored:
        raise HTTPException(
            status_code=404,
            detail="No relevant papers found for this topic. Try different or broader wording.",
        )

    try:
        enriched = run_evidence_agent(scored, topic)
        synthesis = run_summary_agent(enriched, topic)
    except Exception as e:
        logger.exception("Search failed for topic=%r: %s", payload.topic, e)
        raise HTTPException(status_code=500, detail="Search failed. Please try again.")

    # run_summary_agent returns None when the model's reply wasn't valid JSON.
    # Surface that as a retryable error and never cache it.
    if not isinstance(synthesis, dict) or not synthesis:
        logger.error("Summary agent produced no usable synthesis for topic=%r", payload.topic)
        raise HTTPException(
            status_code=503,
            detail="Could not generate a summary for this topic. Please try again.",
        )

    paper_count = len(scored)

    try:
        save_to_cache(cache_key, json.dumps(synthesis), paper_count)
    except Exception as e:
        # The result is good even if we failed to cache it — serve it anyway.
        logger.exception("Cache write failed for topic=%r: %s", cache_key, e)

    return SearchResponse(
        topic=payload.topic,
        synthesis=synthesis,
        paper_count=paper_count,
    )


# --- Serve the built React frontend from this same service (single-service deploy) ---
# Mounted AFTER all /api routes so API endpoints keep precedence over the SPA catch-all.
# Guarded by an existence check so local dev without a build doesn't crash the app on startup
# (StaticFiles raises immediately if the directory is missing).
FRONTEND_DIST = "frontend/dist"

if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=f"{FRONTEND_DIST}/assets"), name="assets")

    # Catch-all for everything not matched above.
    # Serve a real file from dist when it exists (favicon.svg, icons.svg, etc.),
    # otherwise fall back to index.html so client-side routing / SPA works.
    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # Unknown API paths should 404, not silently return the SPA shell.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        dist_root = os.path.abspath(FRONTEND_DIST)
        candidate = os.path.abspath(os.path.join(dist_root, full_path))
        # Guard against path traversal: only serve files that live inside dist.
        if full_path and candidate.startswith(dist_root + os.sep) and os.path.isfile(candidate):
            return FileResponse(candidate)
        # index.html must never be cached: it points to hash-named JS/CSS bundles,
        # so a stale cached index.html keeps loading an old bundle after a deploy
        # (which is how users end up on outdated frontend code). The hashed assets
        # themselves are immutable and safe for the browser to cache.
        return FileResponse(
            f"{FRONTEND_DIST}/index.html",
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )
