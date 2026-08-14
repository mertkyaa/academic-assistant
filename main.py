from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from paper_search import search_papers
from filter_agent import run_filter_agent
from summary_agent import run_summary_agent

from fastapi.middleware.cors import CORSMiddleware

# Pydantic models
class SearchRequest(BaseModel):
    topic: str

class SearchResponse(BaseModel):
    topic: str
    summary: str
    paper_count: int

# App 
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Academic Assistant API is running"}

@app.post("/api/search", response_model=SearchResponse)
def search_endpoint(request: SearchRequest):
    try:
        # 1. Search — üç kaynaktan makale çek
        papers = search_papers(request.topic)

        # 2. Filter — alakaya göre puanla
        scored = run_filter_agent(papers, request.topic)

        # 3. Summary — öğrenci diliyle özetle
        summary = run_summary_agent(scored, request.topic)

        # CrewAI alternatifi: from crew_pipeline import run_crew
        #                     result = run_crew(request.topic)

        return SearchResponse(
            topic=request.topic,
            summary=summary,
            paper_count=len(scored)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

