# RAG ATS Resume Generator (Starter)

This repo scaffolds a full-stack system for generating ATS-optimized, 1-page resumes via a RAG workflow.

## Architecture (current scaffold)
- Frontend (Next.js 15 + Tailwind) — job/profile input, run trigger, result display.
- Backend (FastAPI) — stubbed orchestrator + pipeline for keyword extraction, mapping, scoring, LaTeX assembly placeholder.
- Vector DB/Embeddings — not wired yet; slots left for Pinecone/Weaviate + embedding models.
- PDF generation — LaTeX body stub; hook to sandboxed `pdflatex` + page-count guardrail.

### Data flow (stubbed)
Client → `POST /resume/generate` → orchestrator → pipeline:
1) Keyword extract (naive tokenizer for now)
2) Semantic map (string contains; replace with embeddings/vector search)
3) ATS score (coverage + penalties)
4) LaTeX body stub (fixed sections)
→ response returns score/keywords/gaps and stub PDF URL.

### Tech stack
- Frontend: Next.js (App Router, TS), Tailwind CSS
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
