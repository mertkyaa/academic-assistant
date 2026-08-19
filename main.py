import json
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from query_utils import preprocess_query

from paper_search import search_papers
from filter_agent import run_filter_agent
from evidence_agent import run_evidence_agent
from summary_agent import run_summary_agent
from database import init_db, create_user, get_user_by_email, save_search, get_user_history
from auth import hash_password, verify_password, create_token, verify_token


# Pydantic models
class SearchRequest(BaseModel):
    topic: str

class SearchResponse(BaseModel):
    topic: str
    synthesis: dict
    paper_count: int

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str


# App
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Academic Assistant API is running"}


@app.post("/api/register")
def register_endpoint(request: RegisterRequest):
    existing = get_user_by_email(request.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(request.password)
    user = create_user(request.email, hashed)
    token = create_token(user["id"])

    return {"message": "Registration successful", "token": token, "email": user["email"]}


@app.post("/api/login")
def login_endpoint(request: LoginRequest):
    user = get_user_by_email(request.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user["id"])
    return {"message": "Login successful", "token": token, "email": user["email"]}


@app.post("/api/search", response_model=SearchResponse)
def search_endpoint(request: SearchRequest, user_id: int = Depends(get_current_user)):
    try:
        papers = search_papers(topic)
        scored = run_filter_agent(papers, topic)
        enriched = run_evidence_agent(scored, topic)
        synthesis = run_summary_agent(enriched, topic)
        save_search(user_id, request.topic, json.dumps(synthesis), len(scored))

        return SearchResponse(
            topic=request.topic,
            synthesis=synthesis,
            paper_count=len(scored)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
def history_endpoint(user_id: int = Depends(get_current_user)):
    history = get_user_history(user_id)
    return {"history": history}