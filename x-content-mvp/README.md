# X Content Creation MVP

Monolith Web App for creating English X posts from URL / text / image input, with style learning, draft generation, scoring, and a draft library.

## 1. Implemented MVP Scope

- Input Hub: URL + text + image upload
- Insight Extractor: core claim, key points, evidence, novelty, audience value, tweetable angles
- Style Studio:
  - import historical post samples (textarea or txt/csv)
  - manual style guide
  - rebuild structured style profile
- Draft Composer:
  - post types: `hot_take`, `insight_post`, `thread`, `contrarian`, `personal_brand`
  - tones: `safe`, `sharp`, `bold`
- Draft Scoring:
  - `style_match`, `clarity`, `attention`, `novelty`, `overall`
- Draft Library:
  - query and browse all generated drafts

The app works even without API key (fallback heuristics). With API key configured, it runs full AI pipeline.

## 2. Project Structure

```text
X-Content-Creation-MVP/
├─ app/
│  ├─ main.py
│  ├─ db.py
│  ├─ config.py
│  ├─ services/
│  │  ├─ ai_client.py
│  │  ├─ ingest.py
│  │  ├─ style_engine.py
│  │  └─ content_pipeline.py
│  ├─ templates/
│  └─ static/
├─ docs/
│  └─ X内容创作工具-MVP技术方案.md
├─ data/
├─ requirements.txt
└─ .env.example
```

## 3. Setup

```bash
cd /Users/adam/Desktop/X-Content-Creation-MVP
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill your API key in `.env`:

```dotenv
OPENAI_API_KEY=your_key_here
```

Run:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## 4. API Endpoints

- `POST /api/sources` create source and run full pipeline (url + text)
- `POST /api/extract/{source_id}` rerun extraction only
- `POST /api/style/import` import style samples and rebuild profile
- `POST /api/drafts/generate/{source_id}` regenerate drafts for a source
- `POST /api/drafts/score/{source_id}` rescore latest drafts
- `GET /api/drafts` list drafts
- `GET /healthz` health check

## 5. Notes

- Uploaded images are stored in `data/uploads/`.
- Data is stored in SQLite at `data/x_content_mvp.db`.
- If AI response fails, the app falls back to deterministic heuristics so the product remains usable.
