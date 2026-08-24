# Akademik Asistan — M11 Deploy Devir Teslim

## Proje Özeti
Akademik Makale Takip & Özetleme Asistanı. Kullanıcı araştırma konusu giriyor → arXiv + Semantic Scholar + OpenAlex'ten makale çekiliyor → Filter Agent puanlıyor → Evidence Agent zenginleştiriyor → Summary Agent öğrenci diliyle özetliyor.

## Tech Stack
- **Backend:** Python, FastAPI, Anthropic SDK (Claude API), CrewAI
- **Frontend:** React (Vite + Tailwind CSS), `frontend/` klasöründe
- **DB:** PostgreSQL (Railway hosted) — `psycopg2` ile bağlantı
- **Auth:** bcrypt + PyJWT (JWT token-based)
- **Deploy hedefi:** Railway (backend + frontend tek serviste)

## Tamamlanan Milestone'lar (M0-M10)
- M0-M4: Proje kurulumu, tool-calling, API entegrasyonu
- M5-M6: Manuel multi-agent → CrewAI geçişi
- M7: n8n otomasyon (Railway'de çalışıyor)
- M8: FastAPI backend (`main.py`)
- M9: React frontend (PaperCard, SourceList, skeleton, autocomplete)
- M10: PostgreSQL + Auth (database.py, auth.py, login modal)

## Şu Anki Durum — M11: Deploy (In Progress)

### Yapılanlar:
1. PostgreSQL Railway'de kuruldu ve çalışıyor
2. `database.py` SQLite'tan PostgreSQL'e geçirildi (`psycopg2`, `%s` placeholder, `SERIAL`, `RealDictCursor`)
3. Backend Railway'e deploy edildi ve çalışıyor: `https://academic-assistant-production-35e4.up.railway.app`
4. `Procfile` oluşturuldu: `web: python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
5. `auth.py` SECRET_KEY'i `.env`'den okuyor
6. `App.jsx`'te API URL `import.meta.env.VITE_API_URL` kullanıyor
7. Railway'de environment variables ayarlandı (ANTHROPIC_API_KEY, SEMANTIC_SCHOLAR_KEY, SECRET_KEY, DATABASE_URL)

### Kalan İşler:

**1. main.py'de `preprocess_query` hatası düzeltilmeli:**
`search_endpoint` fonksiyonunda `try:` bloğunun hemen altına şu satır eklenmeli:
```python
topic = preprocess_query(request.topic)
```
Sonra fonksiyondaki `request.topic` geçen yerleri (search, filter, evidence, summary çağrılarında) `topic` ile değiştir. `save_search`'te `request.topic` kalmalı (orijinal girdiyi kaydetmek için).

**2. Frontend build + FastAPI'den statik dosya sunma:**
Frontend'i aynı Railway servisinden sunacağız (ayrı Vercel yok). Plan:
- `frontend/.env.production` dosyasında `VITE_API_URL=` (boş — relative URL kullanacak)
- `cd frontend && npm run build` → `frontend/dist/` oluşur
- `main.py`'ye `StaticFiles` mount ekle:
```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# API route'lardan SONRA, en alta:
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

@app.get("/{path:path}")
def serve_frontend(path: str):
    return FileResponse("frontend/dist/index.html")
```
- Bu sayede `/api/*` istekleri FastAPI'ye, diğer her şey React'e yönlendirilir

**3. Railway'e push ve test:**
- Commit + push
- Railway otomatik redeploy edecek
- `https://academic-assistant-production-35e4.up.railway.app` adresinden hem frontend hem API erişilebilir olmalı

**4. `academic.db` Git'ten çıkarılmalı:**
```bash
git rm --cached academic.db
```
`.gitignore`'da `academic.db` satırı olmalı.

## Önemli Dosyalar ve Yapıları

### Proje Kökü
```
~/Desktop/Akademik-Asistan/
├── main.py              # FastAPI — search, register, login, history endpoints
├── database.py          # PostgreSQL bağlantı + helper fonksiyonlar
├── auth.py              # bcrypt hashing + JWT token
├── paper_search.py      # arXiv + Semantic Scholar + OpenAlex arama
├── filter_agent.py      # Makale filtreleme agent'ı
├── evidence_agent.py    # Kanıt zenginleştirme agent'ı
├── summary_agent.py     # Özet oluşturma agent'ı
├── query_utils.py       # Kısaltma açma (ML → machine learning)
├── config.py            # API key'ler (.env'den okur)
├── crew_pipeline.py     # CrewAI pipeline (alternatif)
├── research.py          # Manuel pipeline (alternatif)
├── Procfile             # Railway deploy komutu
├── requirements.txt     # Python bağımlılıkları
├── .env                 # Local environment variables
└── frontend/
    ├── src/
    │   └── App.jsx      # React ana bileşen
    ├── .env             # VITE_API_URL=http://localhost:8000
    ├── .env.production  # VITE_API_URL= (boş)
    └── dist/            # npm run build çıktısı (henüz oluşturulmadı)
```

### Railway Environment Variables
- `ANTHROPIC_API_KEY` — Claude API
- `SEMANTIC_SCHOLAR_KEY` — Semantic Scholar API
- `SECRET_KEY` — JWT imzalama
- `DATABASE_URL` — PostgreSQL internal URL (gerçek değer Railway panelinde; repoda tutma): `postgresql://postgres:<REDACTED>@postgres-bf.railway.internal:5432/railway`

### PostgreSQL Public URL (local dev için)
Gerçek bağlantı dizesi Railway panelinden alınır, repoya yazılmaz: `postgresql://postgres:<REDACTED>@altaria.proxy.rlwy.net:22882/railway`

### Railway Backend URL
`https://academic-assistant-production-35e4.up.railway.app`

## Bilinen Kalıplar
- **Token optimization:** `format_papers_for_agent()` abstractları 500 char'a keser, 12 makale limiti
- **Prompt injection defense:** XML boundary tag'leri (`<search_results>`, `<paper>`, `<abstract>`)
- **Markdown fence stripping:** `json.loads()` öncesinde model çıktısından code fence temizliği
- **PostgreSQL patterns:** `%s` placeholder, `SERIAL`, `RealDictCursor`, `psycopg2`
- **CORS:** Şu an `allow_origins=["*"]` — deploy sonrası kısıtlanabilir

## Talimatlar
- Açıklamaları Türkçe yap, kod ve yorumlar İngilizce kalsın
- Kod yazarken kavramları "neden böyle yapıyoruz" diye açıkla
- Hata düzeltmede tam dosyayı ver (diff değil)
- Her adımı test et, sonraki adıma geçmeden önce çalıştığını doğrula
- API çağrıları maliyet yaratır, gereksiz test araması yapma
