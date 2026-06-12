# Forge — Requirements Intelligence

Forge is a full-stack portfolio project for turning structured feature descriptions into reviewable engineering artifacts:

- user stories and Given/When/Then acceptance criteria
- OpenAPI 3.0 contract scaffolds
- explicit state-machine definitions and Mermaid diagrams
- JIRA-ready tickets
- confidence flags that surface missing information and assumptions
- session history, human review, JSON editing, and export
- optional Jira Cloud OAuth 2.0 integration

This repository implements the product described in the Forge case study. It is deliberately configured to run in **mock mode by default**, so a reviewer can use the complete workflow without an API key.

## Architecture

```text
React + TypeScript + Vite
          |
          | /api/v1
          v
FastAPI + Pydantic + SQLAlchemy
    |             |              |
    |             |              +-- Jira Cloud REST API v3 (OAuth 2.0 3LO)
    |             +-- Claude API (or deterministic mock provider)
    +-- SQLite locally / PostgreSQL in Docker
```

## Fastest way to run it

### Option A — Docker Compose

1. Copy the environment file:

```bash
cp .env.example .env
```

2. Start the full stack:

```bash
docker compose up --build
```

3. Open <http://localhost:5173>.

Mock mode is enabled by default. To use Claude, set `FORGE_MOCK_LLM=false`, add `ANTHROPIC_API_KEY`, and restart the backend.

### Option B — Run locally without Docker

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e '.[dev]'
cp ../.env.example .env
uvicorn app.main:app --reload --port 8000
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. API documentation is available at <http://localhost:8000/docs>.

## Core workflow

1. Create an intake using the six-field taxonomy: objective, actor, data, dependencies, edge cases, and compliance context.
2. Select a generic, banking, customer-support, or compliance prompt pack.
3. Generate and persist an artifact run.
4. Review confidence flags before approving the run.
5. Edit and revalidate the artifact JSON when needed.
6. Export JSON, OpenAPI YAML, Mermaid, or a ZIP bundle.
7. Optionally connect Jira and create issues using configurable project field mapping.

## Jira setup

Forge uses Jira Cloud OAuth 2.0 authorization-code grants (3LO), not a browser-exposed API token.

1. Create an OAuth 2.0 app in the Atlassian developer console.
2. Add the callback URL shown in `.env.example`.
3. Add the scopes from `ATLASSIAN_SCOPES`.
4. Put the client ID and secret in `.env`.
5. Restart Forge and use **Connect Jira** in the review screen.

Jira projects differ substantially. Forge therefore asks for project key, issue type, and optional custom-field IDs rather than assuming one universal schema.

## Tests

Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm install
npm test
npm run build
```

Run the 14-item prompt corpus in mock mode:

```bash
cd backend
python scripts/evaluate_corpus.py
```

## Evidence and portfolio claims

The code proves that the product workflow exists. It does **not** prove claims such as “18 early adopters,” “94% API-contract accuracy,” “127 prompt variations,” or “4.2x faster” unless you have actually run and documented those studies. See `docs/CLAIMS_CHECKLIST.md` before publishing the case study.

## Production gaps

This is a strong portfolio-grade full-stack implementation, not a turnkey enterprise SaaS. Before handling real customer data, add organization-level authentication, per-user authorization, managed secrets, database migrations, centralized logging, rate limits, data-retention controls, and a formal threat model.

## License

MIT. See `LICENSE`.
