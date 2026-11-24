# Job Match

A thin, working slice of the full job-matching platform: upload a resume, get it parsed, and
see ranked job matches with an explanation for each score. No auth, no queues, no workflow
engine — just enough to prove the core loop end to end.

## Stack

- **apps/web** — Next.js 14 (App Router) + TypeScript + Tailwind
- **apps/api** — FastAPI (Python), SQLAlchemy async, Postgres + pgvector
- **Postgres (pgvector/pgvector:pg16)** — via Docker Compose
- **Mistral OCR** — extracts raw text from uploaded PDFs/images
- **Mistral Embeddings (`mistral-embed`)** — embeddings for semantic search and skill/requirement matching
- **Gemini 2.5 Flash** — structured resume parsing only (not used for scoring — see below)
- **Arbeitnow** — free public job-board API, live-searched on every upload (no static job data)

There's a single mock candidate (no login) — every upload overwrites that one profile and
recomputes matches.

## How matching works

There is no pre-seeded/static job table. The database starts empty; every resume upload
triggers a live search, end to end:

1. **Parse:** the uploaded resume goes through Mistral OCR, then Gemini 2.5 Flash extracts a
   structured `CandidateProfile` (skills, experience, seniority, etc). This is the only LLM
   call in the whole pipeline — Gemini is never used for scoring.
2. **Live job search:** the upload handler immediately calls Arbeitnow's free public API
   (`arbeitnow.com/api/job-board-api`, no auth) for a fresh batch of postings, strips HTML from
   descriptions, and upserts them into `job_postings` keyed on `(source, external_id)` — so
   repeated uploads are cheap (only new/changed postings get re-fetched content), but the
   catalog is always refreshed from the live source, never stale static data. **Arbeitnow's API
   has no keyword-search parameter** (only `remote`/`visa_sponsorship` filters exist) — so
   "adequate to this candidate" filtering can't happen server-side on their end; it happens in
   the next two steps, on our side.
3. **Semantic search (coarse retrieval):** the candidate profile and every job are embedded via
   `mistral-embed`, and a pgvector cosine-distance query shortlists the top 30 most relevant
   jobs out of the freshly-fetched catalog. This is what makes "adequate search" work despite
   Arbeitnow itself not supporting it.
4. **Hungarian algorithm (fine-grained scoring):** each shortlisted job is scored against the
   candidate's **skills, experience (titles + highlights), and education** — not skills alone.
   All of these are embedded as one pool of "candidate items", a similarity cost matrix is
   built against the job's requirements, and `scipy.optimize.linear_sum_assignment` finds the
   optimal one-to-one pairing. This matters because some requirements (e.g. "5+ years
   experience", "distributed systems") can only plausibly be satisfied by an experience entry,
   not a bare skill tag. Score and rationale come directly from that assignment (which item
   covered which requirement, and what's missing) — fully deterministic, no LLM call.

Every job shown to a candidate carries Arbeitnow's real posting URL — since there's no more
fake seed data, "View posting" links always point to the real listing you'd land on if you
searched Arbeitnow yourself.

`POST /jobs/ingest?pages=N` still exists as a manual/admin trigger for bulk pre-warming the
catalog with more pages than the default upload-triggered fetch (2 pages) pulls.

## Cover letters

Each match card has a **Generate cover letter** button (`POST /matches/{id}/cover-letter`) that
asks Gemini 2.5 Flash to draft a short, specific letter from the candidate profile and that
job's actual description/requirements — not generic filler. The draft is persisted on the
`Match` row (`cover_letter_subject`/`cover_letter_body`) so it survives a page reload, and a
"Regenerate" option replaces it. This only ever produces a draft for the candidate to read and
copy themselves — there's no email-sending integration, matching the "never auto-send"
principle from the original architecture doc.

**Requirement quality:** Arbeitnow's `tags` field is inconsistent — alongside genuine domain
categories ("Software Development", "Finance"), it sometimes also contains contract-type,
seniority, or education-level descriptors ("bachelor's degree", "Remote", "berufserfahren").
Matching skills against those produces nonsense pairings (e.g. "Git" → "Remote"), so
`services/arbeitnow.py` filters known non-skill tags out of `requirements` via an explicit
denylist (`_NON_SKILL_TAGS`/`_is_skill_tag`). `job_types` is used only to derive `seniority`,
never treated as a requirement. The remaining tags are still coarse domain categories, not
literal skill lists, which is a real limit of this free data source.

**Threshold caveat:** `STRONG_MATCH_THRESHOLD` in `matcher.py` (currently `0.72`) was raised
from an initial `0.5` after real usage showed real `mistral-embed` similarities for short,
generic phrases run higher than intuition suggests — 0.5 let clearly-unrelated pairs through.
This value hasn't been rigorously tuned against a labeled test set; if matches now look too
strict (everything near 0%) or still too loose, that constant is the first thing to adjust.

**Known limitation:** Arbeitnow's `tags`/`job_types` (used as `requirements`) are coarse
categories (e.g. "IT", "Management"), not literal skill lists — so a job sometimes scores lower
than its full description would justify, even though the description itself is what powers the
semantic-search shortlisting in step 3.

## Run it

1. Start Postgres:
   ```
   docker compose up -d
   ```

2. Backend:
   ```
   cd apps/api
   python -m venv .venv && .venv/Scripts/activate   # or source .venv/bin/activate on macOS/Linux
   pip install -r requirements.txt
   cp .env.example .env   # fill in MISTRAL_API_KEY and GEMINI_API_KEY
   uvicorn app.main:app --reload --port 8001
   ```

3. Frontend:
   ```
   cd apps/web
   pnpm install   # or npm install
   cp .env.local.example .env.local
   pnpm dev       # or npm run dev
   ```

4. Open http://localhost:3000, go to **Upload**, drop a PDF/PNG/JPEG resume, then view
   **Matches**. The first upload will be slower than later ones — it's embedding ~200 freshly
   fetched jobs from scratch.

## API keys

- `MISTRAL_API_KEY` — https://console.mistral.ai (used for OCR and embeddings)
- `GEMINI_API_KEY` — https://aistudio.google.com/apikey (used for resume parsing)

## What's deliberately missing (see the full build-prompts doc for the target architecture)

- Auth (Keycloak/OAuth), multi-tenant RBAC, row-level security
- NestJS gateway, other MCP job-board connectors, LangGraph workflows/Celery, MinIO, Vault
- Cover letter generation + email send with human-approval gates
- Background/async ingestion (the live Arbeitnow fetch runs synchronously inside the upload
  request — fine for an MVP, but a real system would do this as a background job so upload
  latency doesn't depend on Arbeitnow's response time)
- Observability (OpenTelemetry/Langfuse), CI/CD, audit log

These are the next slices to build once this core loop is validated.
