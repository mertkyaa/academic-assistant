import json
import os
import re
import logging
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from query_utils import preprocess_query
from paper_search import search_papers
from filter_agent import run_filter_agent
from evidence_agent import run_evidence_agent
from summary_agent import run_summary_agent
from database import (
    init_db, create_user, get_user_by_email, save_search, get_user_history,
    get_cached_search, save_to_cache,
)
from auth import hash_password, verify_password, create_token, verify_token


logger = logging.getLogger("academic-assistant")

# Allowed frontend origins. Since the built React app is served from this same
# service, the deployed app is same-origin; we still allow the Railway domain
# explicitly plus the local Vite dev server for development.
ALLOWED_ORIGINS = [
    "https://academic-assistant-production-35e4.up.railway.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# Pydantic models
class SearchRequest(BaseModel):
    topic: str


class SearchResponse(BaseModel):
    topic: str
    synthesis: dict
    paper_count: int


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def valid_email(cls, v):
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Invalid email format")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v):
        return v.strip().lower()


# App
app = FastAPI()

# Per-IP rate limiting to protect the expensive search pipeline (3 Claude calls
# per request) from abuse, and to slow down registration/brute-force attempts.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ")[1]
    user_id = verify_token(token)

    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user_id


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Academic Assistant API is running"}


@app.post("/api/register")
@limiter.limit("5/hour")
def register_endpoint(request: Request, payload: RegisterRequest):
    existing = get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(payload.password)
    user = create_user(payload.email, hashed)
    token = create_token(user["id"])

    return {"message": "Registration successful", "token": token, "email": user["email"]}


@app.post("/api/login")
@limiter.limit("10/minute")
def login_endpoint(request: Request, payload: LoginRequest):
    user = get_user_by_email(payload.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user["id"])
    return {"message": "Login successful", "token": token, "email": user["email"]}


@app.post("/api/search", response_model=SearchResponse)
@limiter.limit("20/hour")
def search_endpoint(request: Request, payload: SearchRequest, user_id: int = Depends(get_current_user)):
    try:
        topic = preprocess_query(payload.topic)
        cache_key = topic.strip().lower()

        # Reuse a recent cached result for this topic to skip the expensive pipeline.
        cached = get_cached_search(cache_key)
        if cached:
            synthesis = json.loads(cached["synthesis"])
            paper_count = cached["paper_count"]
        else:
            papers = search_papers(topic)
            scored = run_filter_agent(papers, topic)
            enriched = run_evidence_agent(scored, topic)
            synthesis = run_summary_agent(enriched, topic)
            paper_count = len(scored)
            save_to_cache(cache_key, json.dumps(synthesis), paper_count)

        # Always record the user's own search in their history (original input).
        save_search(user_id, payload.topic, json.dumps(synthesis), paper_count)

        return SearchResponse(
            topic=payload.topic,
            synthesis=synthesis,
            paper_count=paper_count,
        )

    except Exception as e:
        # Log the real error server-side; return a generic message so we don't
        # leak internal details (stack traces, DB errors) to the client.
        logger.exception("Search failed for topic=%r: %s", payload.topic, e)
        raise HTTPException(status_code=500, detail="Search failed. Please try again.")


@app.get("/api/history")
def history_endpoint(user_id: int = Depends(get_current_user)):
    history = get_user_history(user_id)
    return {"history": history}


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
        return FileResponse(f"{FRONTEND_DIST}/index.html")
