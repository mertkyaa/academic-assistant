# Academic Research Assistant

A multi-agent research assistant that turns a topic into a cited literature synthesis. It searches three academic databases, scores the results for relevance, extracts evidence from each abstract, and writes a structured overview aimed at a student meeting the field for the first time.

**Live:** https://academic-assistant-production-35e4.up.railway.app

[![E2E smoke tests](https://github.com/mertkyaa/academic-assistant/actions/workflows/e2e.yml/badge.svg)](https://github.com/mertkyaa/academic-assistant/actions/workflows/e2e.yml)

---

## What it does

Enter a research topic and the app returns:

- **Overview** — what the topic actually is, defined for a newcomer
- **Themes** — 2–4 narrative threads through the literature, each citing the papers behind it
- **Trends** — where the field is heading
- **Open problems** — what remains unanswered
- **Where to start** — 2–3 papers to read first, and why

Every claim links back to a real paper with authors, year, citation count and source. The synthesis exports as Markdown or a print-ready PDF.

No account is needed. Search is open to everyone and guarded by a per-IP rate limit.

---

## How it works

A request runs through a five-stage pipeline. Each agent is a separate Claude call with its own system prompt and a strict JSON contract, so a failure in one stage is contained rather than corrupting the whole response.

```
topic
  │
  ├─ 0. Cache lookup ─────────── hit (≤7 days old) ──→ return immediately
  │
  ├─ 1. Query normalization      Claude rewrites the topic into a clean English
  │                              academic phrase: translates non-English input and
  │                              disambiguates acronyms, so "Alp Dağları" becomes
  │                              "European Alps mountain range" rather than matching
  │                              papers about axion-like particles.
  │
  ├─ 2. Paper search             Semantic Scholar, then OpenAlex, then arXiv —
  │                              5 results each, deduplicated by normalized title
  │                              and sorted by citation count. Each source is
  │                              wrapped independently, so if one API is down the
  │                              search continues with the other two.
  │
  ├─ 3. Filter agent             Scores every paper 0–10 on relevance, recency and
  │                              impact. Drops anything below relevance 6 or missing
  │                              a URL or authors, so coincidental keyword matches
  │                              and unciteable entries never reach the synthesis.
  │
  ├─ 4. Evidence agent           Extracts problem / method / main finding /
  │                              limitations from each abstract, restricted to what
  │                              the abstract actually states.
  │
  └─ 5. Summary agent            Writes the synthesis, referencing papers only by
                                 the IDs it was given.
```

**Cost:** an uncached search is 4 Claude calls (~15k tokens total). A cached one is a single database read. Searches that find nothing relevant stop after stage 3, so they cost 2 calls instead of 4.

### Grounding

The pipeline is built so the model cannot invent sources:

- Paper metadata comes from the source APIs, never from the model. Scores are merged back onto papers by `paper_id`, and the original metadata wins on every shared field — so a paraphrased title or a hallucinated ID cannot overwrite a real URL.
- The evidence agent's output is rejected unless its `paper_id` is one that was actually sent.
- All three agents receive paper data inside explicit data tags with instructions never to follow text found inside them. `injection_test.py` covers this.
- A synthesis that does not parse as JSON is never cached and returns a retryable error.

---

## Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI, Python 3.11 |
| Frontend | React 19, Vite 8, Tailwind CSS 4 |
| Database | PostgreSQL (search cache) |
| LLM | Anthropic Claude (`claude-haiku-4-5`) |
| Rate limiting | slowapi, per client IP |
| Sources | arXiv, OpenAlex, Semantic Scholar |
| Tests | Playwright (E2E), GitHub Actions |
| Hosting | Railway, single service |

The built React app is served by FastAPI itself, so the whole thing deploys as one service with no separate frontend host and no cross-origin requests in production.

---

## API

### `GET /api/health`

```json
{ "status": "ok", "message": "Academic Assistant API is running" }
```

### `POST /api/search`

```json
{ "topic": "graph neural networks" }
```

```json
{
  "topic": "graph neural networks",
  "paper_count": 9,
  "synthesis": {
    "title": "Graph Neural Networks: Fundamentals, Expressiveness, and Applications",
    "overview": "...",
    "themes":        [{ "title": "...", "summary": "...", "paper_ids": ["..."] }],
    "trends":        [{ "trend": "...", "paper_ids": ["..."] }],
    "open_problems": [{ "problem": "...", "paper_ids": ["..."] }],
    "where_to_start":[{ "paper_id": "...", "reason": "..." }],
    "papers": { "<paper_id>": { "title": "...", "authors": [], "url": "...", "citation_count": 0, "source": "arxiv" } }
  }
}
```

`themes`, `trends`, `open_problems` and `where_to_start` reference papers by ID; resolve them against the `papers` map.

| Status | Meaning |
|---|---|
| `200` | Synthesis returned |
| `404` | No relevant papers found — try broader wording |
| `422` | Topic is shorter than 5 or longer than 200 characters |
| `429` | Rate limit reached (10/hour, 30/day per IP) |
| `503` | The summary agent produced unusable output; retry |
| `500` | Unexpected failure; details are logged server-side only |

---

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 20+
- A PostgreSQL database
- An [Anthropic API key](https://console.anthropic.com/)
- A [Semantic Scholar API key](https://www.semanticscholar.org/product/api) (optional — that source degrades gracefully without one)

### Setup

```bash
git clone https://github.com/mertkyaa/academic-assistant.git
cd academic-assistant

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cd frontend && npm install && cd ..
```

Create `.env` in the project root:

```bash
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://user:password@host:5432/dbname
SEMANTIC_SCHOLAR_KEY=...
```

Initialize the cache table:

```bash
python database.py
```

### Running locally

The frontend reads its API base URL from `frontend/.env`:

```bash
VITE_API_URL=http://localhost:8000
```

Two terminals:

```bash
# backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

```bash
# frontend
cd frontend && npm run dev
```

Open http://localhost:5173. Interactive API docs are at http://localhost:8000/docs.

To run the backend against the production build instead, run `npm run build` in `frontend/` and open http://localhost:8000 — FastAPI serves `frontend/dist` directly.

---

## Configuration

Behaviour is tuned through constants rather than environment variables, so the defaults are visible in the diff when they change.

| Setting | Location | Default |
|---|---|---|
| Claude model | `config.py` | `claude-haiku-4-5` |
| Rate limit | `main.py` | `10/hour;30/day` per IP |
| Topic length bounds | `main.py` | 5–200 characters |
| Cache lifetime | `database.py` | 7 days |
| Results per source | `paper_search.py` | 5 |
| Papers sent to agents | `search_agent.py` | 12 |
| Abstract truncation | `search_agent.py` | 3000 characters |
| Minimum relevance to keep | `filter_agent.py` | 6 / 10 |

`RATE_LIMIT_ENABLED=false` disables rate limiting; use it only for local test runs.

---

## Testing

```bash
cd frontend
npx playwright test -g "API health|landing page"   # free: no pipeline run
npx playwright test                                # includes a live paid search
```

CI runs only the free tests on every push. The full suite triggers a real pipeline run against the deployed app, so it is kept manual.

Backend checks:

```bash
python injection_test.py     # prompt-injection regression test
python paper_search.py       # exercise the three source clients
python config.py             # verify the API key loads
```

---

## Deployment

Railway builds from `requirements.txt` and runs the `Procfile`:

```
web: python -m uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"
```

`--proxy-headers` is required, not optional: without it every request appears to come from Railway's proxy and the per-IP rate limit — the only thing standing between the pipeline and an unbounded API bill — would apply to all users as one bucket.

Two things to know before deploying:

- **`frontend/dist/` is committed to the repository** and served by FastAPI. Any frontend change needs `npm run build` and the rebuilt bundle committed, or the deploy ships the previous one.
- `ALLOWED_ORIGINS` in `main.py` lists the deployed domain and the local Vite dev server. Add any new frontend origin there.

Set `ANTHROPIC_API_KEY`, `DATABASE_URL` and `SEMANTIC_SCHOLAR_KEY` in the Railway environment.

---

## Project structure

```
├── main.py                      FastAPI app: routes, validation, rate limiting, SPA serving
├── config.py                    API key and model selection
├── database.py                  Postgres connection and the search cache
├── query_utils.py               Stage 1 — query normalization
├── paper_search.py              Stage 2 — fan out to three sources, dedupe, sort
│   ├── arxiv_client.py
│   ├── openalex_client.py
│   └── semantic_scholar_client.py
├── filter_agent.py              Stage 3 — relevance / recency / impact scoring
├── evidence_agent.py            Stage 4 — per-abstract evidence extraction
├── summary_agent.py             Stage 5 — final synthesis
├── search_agent.py              Paper formatting shared by the agents
├── injection_test.py            Prompt-injection regression test
├── crew_pipeline.py             Standalone CrewAI implementation of the same pipeline
├── research.py                  CLI entry point for the pipeline
├── Procfile                     Railway process definition
└── frontend/
    ├── src/App.jsx              Single-page UI: search, results, exports
    ├── src/exportUtils.js       Markdown and print-ready HTML builders
    ├── e2e/app.spec.js          Playwright E2E tests
    └── dist/                    Committed production build, served by FastAPI
```

`crew_pipeline.py` reimplements the pipeline on CrewAI and is kept as a framework comparison — the API does not use it.

---

## Design notes

**Why separate agents instead of one prompt?** Each stage has a different failure mode. Scoring relevance is a judgement task, extracting evidence is a constrained reading task, and synthesis is a writing task. Splitting them means the evidence agent can be forbidden from using outside knowledge while the summary agent is explicitly allowed to define the topic from its own knowledge — a distinction a single prompt cannot hold.

**Why cache on the raw input?** The cache key is the lowercased topic as typed, so an identical repeat search skips query normalization too. Normalization only runs on a miss.

**Why no accounts?** Earlier versions had registration, login and saved history. They added friction to a tool whose value is immediate, and the search history was never read. The per-IP rate limit does the one job the login was really doing — capping cost.

---

## Context

Built as a mandatory internship project for the Computer Engineering programme at Bandırma Onyedi Eylül University, supervised by Doç. Dr. Mehmet Akif Çiftçi. Developed across 13 milestones, from a single tool-calling script to a deployed multi-agent application.

**Author:** Mert Kaya
