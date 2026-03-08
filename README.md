# datahub-MetaClassifier

MetaClassifier is an event-driven metadata intelligence pipeline that listens to DataHub metadata events and automatically enriches datasets with domain knowledge and classifications.

## Architecture (v1)

- `event-ingestion-service`: DataHub Action ingress and event normalization.
- `classification-service`: domain-knowledge resolution + pluggable provider classification (OpenAI default adapter).
- `workflow-service`: approval/rejection state transitions.
- `writeback-service`: approved metadata writeback payload generation (tags, glossary terms, domain).
- `feedback-service`: good/bad feedback capture with rules memory updates.
- `control-api`: operator API for sync, logs, review queue, feedback, metrics, taxonomy queue.
- `control-ui`: internal web interface served by `control-api`.

Shared storage: Postgres for Compose/prod and SQLite for local development.

## Quickstart (local)

```bash
cp .env.example .env
pip install -e .[dev]
pytest
uvicorn services.control_api.app.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000).

## Run with Docker Compose

```bash
docker compose up --build
```

Services:

- `control-api`: `http://localhost:8000`
- `event-ingestion`: `http://localhost:8001`
- `classification`: `http://localhost:8002`
- `workflow`: `http://localhost:8003`
- `writeback`: `http://localhost:8004`
- `feedback`: `http://localhost:8005`

## DataHub Action integration scaffold

`services/event_ingestion_service/app/datahub_action.py` contains a plugin scaffold that forwards DataHub Action events to the ingestion endpoint.

## OpenAI endpoint configuration

The classifier supports both official OpenAI and any OpenAI-compatible local endpoint.

- Official OpenAI:
  - `OPENAI_BASE_URL=https://api.openai.com/v1`
  - `OPENAI_API_KEY=<your-key>`
- Local OpenAI-compatible endpoint (example):
  - `OPENAI_BASE_URL=http://localhost:11434/v1`
  - `OPENAI_API_KEY=` (optional; leave empty if local server does not require it)

If the endpoint is unavailable or returns invalid output, the service falls back to a deterministic heuristic classifier so the pipeline still runs.

## API Endpoints

- `POST /config/knowledge-sync`
- `GET /events`
- `GET /events/{id}/logs`
- `GET /proposals`
- `POST /proposals/{id}/approve`
- `POST /proposals/{id}/reject`
- `POST /feedback`
- `GET /metrics/classification-overview`
- `GET /taxonomy/proposals`

## Quality gates

- Lint: `ruff check .`
- Format: `black --check .`
- Types: `mypy services`
- Tests: `pytest`

GitHub Actions runs all checks on push and pull request.
