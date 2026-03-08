from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from services.shared.db import get_db, init_db
from services.shared.domain import normalize_datahub_event
from services.shared.repository import log_event, record_audit
from services.shared.schemas import EventIn

app = FastAPI(title="event-ingestion-service")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest", response_model=EventIn)
def ingest_datahub_event(payload: dict, db: Session = Depends(get_db)) -> EventIn:
    event = normalize_datahub_event(payload)
    log_event(db, event)
    record_audit(db, "event_ingested", "event-ingestion-service", {"event_id": event.event_id})
    return event
