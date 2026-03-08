import time

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.classification_service.app.knowledge import resolve_knowledge_from_datahub
from services.classification_service.app.providers.openai_provider import OpenAIProvider
from services.shared.config import settings
from services.shared.db import get_db, init_db
from services.shared.models import EventModel, RuleMemoryModel
from services.shared.repository import (
    create_proposal,
    enqueue_taxonomy_proposals,
    record_audit,
    record_provider_run,
    update_event_knowledge,
)
from services.shared.schemas import ClassificationResult, EventIn, EventType

app = FastAPI(title="classification-service")
provider = OpenAIProvider(
    base_url=settings.openai_base_url,
    api_key=settings.openai_api_key,
    model=settings.classifier_model,
    timeout_seconds=settings.openai_timeout_seconds,
)


class ClassifyRequest(BaseModel):
    event_id: str


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/classify", response_model=ClassificationResult)
def classify(req: ClassifyRequest, db: Session = Depends(get_db)) -> ClassificationResult:
    event = db.scalar(select(EventModel).where(EventModel.event_id == req.event_id))
    if not event:
        raise HTTPException(status_code=404, detail="event_not_found")

    event_in = EventIn(
        event_id=event.event_id,
        urn=event.urn,
        event_type=EventType(event.event_type),
        change_summary=event.change_summary,
        raw_payload=event.raw_payload,
    )

    start = time.time()
    knowledge = resolve_knowledge_from_datahub(event.urn)
    rules = {
        row.key: row.value
        for row in db.scalars(select(RuleMemoryModel).where(RuleMemoryModel.key.like("global:%"))).all()
    }
    flattened_rules = {
        "deny_tags": rules.get("global:deny_tags", {}).get("items", []),
        "force_tags": rules.get("global:force_tags", {}).get("items", []),
        "force_domain": rules.get("global:force_domain", {}).get("value"),
    }
    proposal = provider.classify(event_in, knowledge, flattened_rules)
    latency_ms = int((time.time() - start) * 1000)

    update_event_knowledge(db, event.event_id, knowledge.model_dump())
    saved = create_proposal(
        db,
        event_id=event.event_id,
        urn=event.urn,
        tags=proposal.tags,
        glossary_terms=proposal.glossary_terms,
        domain=proposal.domain,
        unknown_concepts=proposal.unknown_concepts,
        confidence=proposal.confidence,
        rationale=proposal.rationale,
        model_metadata={
            "provider": settings.classifier_provider,
            "model": settings.classifier_model,
            "base_url": settings.openai_base_url,
        },
    )

    if proposal.unknown_concepts:
        enqueue_taxonomy_proposals(db, event.event_id, proposal.unknown_concepts)

    record_provider_run(
        db,
        event_id=event.event_id,
        provider=settings.classifier_provider,
        model=settings.classifier_model,
        latency_ms=latency_ms,
        metadata={"proposal_id": saved.id},
    )
    record_audit(db, "classified", "classification-service", {"event_id": event.event_id})

    return ClassificationResult(
        event=event_in,
        knowledge_snapshot=knowledge,
        proposal=proposal,
        model_metadata={
            "provider": settings.classifier_provider,
            "model": settings.classifier_model,
            "base_url": settings.openai_base_url,
            "latency_ms": latency_ms,
        },
    )
