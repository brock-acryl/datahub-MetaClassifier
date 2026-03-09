import httpx
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from services.shared.config import settings
from services.shared.db import get_db, init_db
from services.shared.domain import is_supported_datahub_event, normalize_datahub_event
from services.shared.logging import get_logger
from services.shared.repository import get_event_by_event_id, log_event, record_audit
from services.shared.schemas import (
    ClassificationTriggerStatus,
    IngestionResult,
    IngestionStatus,
)

app = FastAPI(title="event-ingestion-service")
logger = get_logger("event-ingestion-service")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _trigger_classification(event_id: str) -> tuple[ClassificationTriggerStatus, str | None]:
    try:
        with httpx.Client(timeout=settings.classification_timeout_seconds) as client:
            response = client.post(settings.classification_service_url, json={"event_id": event_id})
            response.raise_for_status()
        return ClassificationTriggerStatus.TRIGGERED, None
    except Exception as exc:
        return ClassificationTriggerStatus.TRIGGER_FAILED, str(exc)


@app.post("/ingest", response_model=IngestionResult)
def ingest_datahub_event(payload: dict, db: Session = Depends(get_db)) -> IngestionResult | JSONResponse:
    event = normalize_datahub_event(payload)
    correlation = {"correlation_id": event.event_id}

    if not is_supported_datahub_event(payload):
        logger.info("Ignored unsupported event type", extra=correlation)
        result = IngestionResult(
            event=event,
            ingestion_status=IngestionStatus.IGNORED_EVENT_TYPE,
            classification_trigger_status=ClassificationTriggerStatus.NOT_ATTEMPTED,
        )
        return result

    existing = get_event_by_event_id(db, event.event_id)
    if existing:
        logger.info("Duplicate event ignored", extra=correlation)
        record_audit(
            db,
            "event_duplicate_ignored",
            "event-ingestion-service",
            {"event_id": event.event_id},
        )
        return IngestionResult(
            event=event,
            ingestion_status=IngestionStatus.DUPLICATE_IGNORED,
            classification_trigger_status=ClassificationTriggerStatus.NOT_ATTEMPTED,
        )

    log_event(db, event)
    record_audit(db, "event_ingested", "event-ingestion-service", {"event_id": event.event_id})
    logger.info("Event ingested", extra=correlation)

    trigger_status, trigger_error = _trigger_classification(event.event_id)
    if trigger_status == ClassificationTriggerStatus.TRIGGER_FAILED:
        record_audit(
            db,
            "classification_trigger_failed",
            "event-ingestion-service",
            {"event_id": event.event_id, "error": trigger_error},
        )
        logger.info("Classification trigger failed", extra=correlation)
        result = IngestionResult(
            event=event,
            ingestion_status=IngestionStatus.STORED,
            classification_trigger_status=trigger_status,
            classification_error=trigger_error,
        )
        return JSONResponse(status_code=202, content=result.model_dump(mode="json"))

    record_audit(
        db,
        "classification_triggered",
        "event-ingestion-service",
        {"event_id": event.event_id},
    )
    logger.info("Classification triggered", extra=correlation)
    return IngestionResult(
        event=event,
        ingestion_status=IngestionStatus.STORED,
        classification_trigger_status=ClassificationTriggerStatus.TRIGGERED,
    )
