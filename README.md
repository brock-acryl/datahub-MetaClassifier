# datahub-MetaClassifier

MetaClassifier is an event-driven metadata intelligence pipeline that listens to DataHub metadata events and automatically enriches datasets with domain knowledge and classifications.

## Architecture (v1)

- `actions-runner`: DataHub Actions runtime that listens to DataHub and invokes the custom MetaClassifier action.
- `event-ingestion-service`: internal ingress endpoint for action handoff and event normalization.
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
- `actions-runner`: DataHub Actions listener process (no HTTP port)

## DataHub Action integration

MetaClassifier now uses a real DataHub Actions runner via `docker compose`:

- Runner command: `datahub actions -c /app/config/actions.yaml`
- Actions config: `config/actions.yaml`
- Custom action class: `services/event_ingestion_service/app/datahub_action.py`
- Handoff target: `http://event-ingestion:8001/ingest`

Required runtime env vars:

- `DATAHUB_GMS_URL` (for example `http://datahub-gms:8080`)
- `DATAHUB_GMS_TOKEN` (optional)

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

### Event ingestion behavior

`POST /ingest` is idempotent by `event_id` and now returns:

- `event` (normalized event)
- `ingestion_status`: `stored` | `duplicate_ignored` | `ignored_event_type`
- `classification_trigger_status`: `triggered` | `trigger_failed` | `not_attempted`
- `classification_error` (nullable)

On classification trigger failure, ingestion returns HTTP `202` and still persists the event.

### Verifying DataHub listening

```bash
docker compose up --build -d
docker compose logs -f actions-runner event-ingestion
```

Action ingestion failures are visible in `actions-runner` logs and in MetaClassifier audit rows.

`actions-runner` bind-mounts `config/actions.yaml`, so changes to action config do not require image rebuilds.  
After editing the file, restart only the runner:

```bash
docker compose restart actions-runner
```

## Quality gates

- Lint: `ruff check .`
- Format: `black --check .`
- Types: `mypy services`
- Tests: `pytest`

GitHub Actions runs all checks on push and pull request.
