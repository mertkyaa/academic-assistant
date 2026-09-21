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
    init_db, create_user, get_user_by_email, get_user_history,
    get_cached_search, save_to_cache,
    get_user_by_id, get_user_by_username, update_username, update_password, delete_user,
)
from auth import (
    hash_password, verify_password, create_token, verify_token,
    create_reset_token, verify_reset_token,
)
from email_service import send_reset_email


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
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_-]{3,30}$")

# Base URL used to build password-reset links (points at the deployed frontend).
APP_BASE_URL = os.getenv(
    "APP_BASE_URL", "https://academic-assistant-production-35e4.up.railway.app"
)


def _validate_username(v):
    v = v.strip()
    if not USERNAME_RE.match(v):
        raise ValueError("Username must be 3-30 characters: letters, numbers, _ or -")
    return v


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
    username: str

    @field_validator("email")
    @classmethod
    def valid_email(cls, v):
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("username")
    @classmethod
    def valid_username(cls, v):
        return _validate_username(v)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v):
        return v.strip().lower()


class UpdateProfileRequest(BaseModel):
    username: str

    @field_validator("username")
    @classmethod
    def valid_username(cls, v):
        return _validate_username(v)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v):
        return v.strip().lower()


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


# App
app = FastAPI()

# Per-IP rate limiting to protect the expensive search pipeline (3 Claude calls
# per request) from abuse, and to slow down registration/brute-force attempts.
# Can be disabled for test runs via RATE_LIMIT_ENABLED=false so a comprehensive
# suite can register/login freely without tripping the production limits.
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


def _public_user(user):
    """User fields safe to send to the client (never the password hash)."""
    return {
        "id": user["id"],
        "email": user["email"],
        "username": user.get("username"),
        "created_at": user["created_at"],
    }


@app.post("/api/register")
@limiter.limit("5/hour")
def register_endpoint(request: Request, payload: RegisterRequest):
    if get_user_by_email(payload.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if get_user_by_username(payload.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    hashed = hash_password(payload.password)
    user = create_user(payload.email, hashed, payload.username)
    token = create_token(user["id"])

    return {
        "message": "Registration successful",
        "token": token,
        "email": user["email"],
        "username": user["username"],
    }


@app.post("/api/login")
@limiter.limit("10/minute")
def login_endpoint(request: Request, payload: LoginRequest):
    user = get_user_by_email(payload.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user["id"])
    return {
        "message": "Login successful",
        "token": token,
        "email": user["email"],
        "username": user.get("username"),
    }


@app.post("/api/forgot-password")
@limiter.limit("3/hour")
def forgot_password_endpoint(request: Request, payload: ForgotPasswordRequest):
    # Always return the same response so we never reveal whether an email is
    # registered. Only actually send a mail when the user exists.
    user = get_user_by_email(payload.email)
    if user:
        token = create_reset_token(user["id"])
        reset_link = f"{APP_BASE_URL}/reset?token={token}"
        try:
            send_reset_email(user["email"], reset_link)
        except Exception as e:
            logger.exception("Failed to send reset email to %s: %s", payload.email, e)

    return {"message": "If that email is registered, a reset link has been sent."}


@app.post("/api/reset-password")
@limiter.limit("5/hour")
def reset_password_endpoint(request: Request, payload: ResetPasswordRequest):
    user_id = verify_reset_token(payload.token)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    update_password(user_id, hash_password(payload.new_password))
    return {"message": "Password updated. You can now sign in."}


@app.get("/api/me")
def get_me(user_id: int = Depends(get_current_user)):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _public_user(user)


@app.patch("/api/me")
def update_me(payload: UpdateProfileRequest, user_id: int = Depends(get_current_user)):
    existing = get_user_by_username(payload.username)
    if existing and existing["id"] != user_id:
        raise HTTPException(status_code=400, detail="Username already taken")

    update_username(user_id, payload.username)
    return _public_user(get_user_by_id(user_id))


@app.post("/api/me/password")
@limiter.limit("5/minute")
def change_password_endpoint(request: Request, payload: ChangePasswordRequest,
                             user_id: int = Depends(get_current_user)):
    user = get_user_by_id(user_id)
    if not user or not verify_password(payload.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    update_password(user_id, hash_password(payload.new_password))
    return {"message": "Password updated successfully"}


@app.delete("/api/me")
def delete_me(user_id: int = Depends(get_current_user)):
    delete_user(user_id)
    return {"message": "Account deleted"}


# Search is open (no login). The per-IP limit is the cost guard against abuse of
# the expensive pipeline, so it must count real client IPs — see --proxy-headers
# in the Procfile, which makes get_remote_address see the true IP behind Railway.
@app.post("/api/search", response_model=SearchResponse)
@limiter.limit("10/hour;30/day")
def search_endpoint(request: Request, payload: SearchRequest):
    try:
        # Cache on the raw user input so identical searches hit the cache without
        # paying for query normalization; normalize only on a cache miss.
        cache_key = payload.topic.strip().lower()

        cached = get_cached_search(cache_key)
        if cached:
            synthesis = json.loads(cached["synthesis"])
            paper_count = cached["paper_count"]
        else:
            topic = preprocess_query(payload.topic)
            papers = search_papers(topic)
            scored = run_filter_agent(papers, topic)
            enriched = run_evidence_agent(scored, topic)
            synthesis = run_summary_agent(enriched, topic)
            paper_count = len(scored)
            save_to_cache(cache_key, json.dumps(synthesis), paper_count)

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
        # index.html must never be cached: it points to hash-named JS/CSS bundles,
        # so a stale cached index.html keeps loading an old bundle after a deploy
        # (which is how users end up on outdated frontend code). The hashed assets
        # themselves are immutable and safe for the browser to cache.
        return FileResponse(
            f"{FRONTEND_DIST}/index.html",
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )
