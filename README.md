# RAG ATS Resume Generator

This is a full-stack system for generating ATS-optimized, 1-page resumes via a RAG workflow.

## Quick Start

### 1. Run Both Services
```bash
./start.sh
```

This starts:
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 2. Pre-Ingest Your Resume (One-Time Setup)

Use the Jupyter notebook to ingest your resume:

```bash
jupyter notebook ingest_profile.ipynb
```

In the notebook, choose one of three options:
- **Option 1**: Load from PDF file path
- **Option 2**: Load from URL
- **Option 3**: Paste plaintext resume

The notebook will:
- Extract and structure your resume sections
- Train embeddings locally
- Save profile and embeddings to `profile_cache/` directory
- Create a unique profile name (default: `my_profile`)

### 3. Generate Optimized Resumes

1. Open http://localhost:3000
2. Enter the profile name you saved (default: `my_profile`)
3. Fill in job details (title, company, location, description)
4. Click "Generate Resume"
5. Download your ATS-optimized PDF

## Architecture

- **Frontend** (Next.js 15 + Tailwind) — job input, resume generation, result display
- **Backend** (FastAPI) — orchestrator, pipeline, PDF generation
- **Embeddings** — Stored locally in `profile_cache/`
- **PDF** — Generated via LaTeX with 1-page guardrail

### Data Flow

1. **Pre-ingest** (Notebook): Resume → Extract sections → Train embeddings → Save to `profile_cache/`
2. **Generate** (Web UI): 
   - Load saved profile by name
   - Extract keywords from job description
   - Map to resume content (semantic matching)
   - Score ATS compatibility
   - Generate LaTeX + PDF

- Backend: FastAPI, Pydantic, Uvicorn
- Testing: pytest (backend), built-in Next.js tooling (frontend)

## Getting started
Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```
Set `NEXT_PUBLIC_API_BASE_URL` if backend is not on `http://localhost:8000`.

## Next steps
- Swap stub pipeline for real retrieval (chunking, embeddings, vector DB).
- Add iterative optimizer loop and guardrails for strict 1-page LaTeX render.
- Persist artifacts (object storage) and run state (Postgres) with durable workflows.
