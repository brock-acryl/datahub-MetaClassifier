from collections.abc import Iterable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.shared.models import (
    AuditLogModel,
    EventModel,
    FeedbackModel,
    PromptMemoryModel,
    ProposalModel,
    ProviderRunModel,
    RuleMemoryModel,
    SyncJobModel,
    TaxonomyProposalModel,
)
from services.shared.schemas import EventIn, EventType, MetricsOut, ProposalStatus


def log_event(db: Session, event: EventIn) -> EventModel:
    model = EventModel(
        event_id=event.event_id,
        urn=event.urn,
        event_type=event.event_type.value,
        change_summary=event.change_summary,
        raw_payload=event.raw_payload,
        status=ProposalStatus.PENDING_REVIEW.value,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def update_event_knowledge(db: Session, event_id: str, knowledge_snapshot: dict[str, Any]) -> None:
    item = db.scalar(select(EventModel).where(EventModel.event_id == event_id))
    if item:
        item.knowledge_snapshot = knowledge_snapshot
        db.commit()


def create_proposal(
    db: Session,
    event_id: str,
    urn: str,
    tags: list[str],
    glossary_terms: list[str],
    domain: str | None,
    unknown_concepts: list[str],
    confidence: float,
    rationale: str,
    model_metadata: dict[str, Any],
) -> ProposalModel:
    proposal = ProposalModel(
        event_id=event_id,
        urn=urn,
        tags=tags,
        glossary_terms=glossary_terms,
        domain=domain,
        unknown_concepts=unknown_concepts,
        confidence=confidence,
        rationale=rationale,
        model_metadata=model_metadata,
        status=ProposalStatus.PENDING_REVIEW.value,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


def list_events(db: Session) -> list[EventModel]:
    rows = db.scalars(select(EventModel).order_by(EventModel.created_at.desc())).all()
    return list(rows)


def list_proposals(db: Session, status: str | None = None) -> list[ProposalModel]:
    query = select(ProposalModel).order_by(ProposalModel.created_at.desc())
    if status:
        query = query.where(ProposalModel.status == status)
    rows = db.scalars(query).all()
    return list(rows)


def get_proposal(db: Session, proposal_id: int) -> ProposalModel | None:
    return db.scalar(select(ProposalModel).where(ProposalModel.id == proposal_id))


def set_proposal_status(
    db: Session, proposal_id: int, status: ProposalStatus, review_decision: str
) -> ProposalModel | None:
    proposal = get_proposal(db, proposal_id)
    if not proposal:
        return None
    proposal.status = status.value
    proposal.review_decision = review_decision
    db.commit()
    db.refresh(proposal)
    return proposal


def store_feedback(
    db: Session, proposal_id: int, verdict: str, comment: str, corrections: dict[str, Any]
) -> FeedbackModel:
    row = FeedbackModel(
        proposal_id=proposal_id,
        verdict=verdict,
        comment=comment,
        corrections=corrections,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def upsert_rule_memory(db: Session, key: str, value: dict[str, Any], source: str = "feedback") -> None:
    existing = db.scalar(select(RuleMemoryModel).where(RuleMemoryModel.key == key))
    if existing:
        existing.value = value
        existing.source = source
    else:
        db.add(RuleMemoryModel(key=key, value=value, source=source))
    db.commit()


def append_prompt_memory(db: Session, urn: str, example: dict[str, Any]) -> None:
    db.add(PromptMemoryModel(urn=urn, example=example))
    db.commit()


def record_provider_run(
    db: Session,
    event_id: str,
    provider: str,
    model: str,
    latency_ms: int,
    metadata: dict[str, Any],
) -> None:
    db.add(
        ProviderRunModel(
            event_id=event_id,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            run_metadata=metadata,
        )
    )
    db.commit()


def record_sync_job(db: Session, source: str, full_refresh: bool, details: dict[str, Any]) -> SyncJobModel:
    row = SyncJobModel(source=source, full_refresh=full_refresh, status="completed", details=details)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def record_audit(db: Session, action: str, actor: str, details: dict[str, Any]) -> None:
    db.add(AuditLogModel(action=action, actor=actor, details=details))
    db.commit()


def enqueue_taxonomy_proposals(db: Session, event_id: str, concepts: Iterable[str]) -> None:
    for concept in concepts:
        db.add(TaxonomyProposalModel(event_id=event_id, concept=concept))
    db.commit()


def list_taxonomy_proposals(db: Session) -> list[TaxonomyProposalModel]:
    rows = db.scalars(select(TaxonomyProposalModel).order_by(TaxonomyProposalModel.created_at.desc())).all()
    return list(rows)


def metrics(db: Session) -> MetricsOut:
    def count_rows(model: Any) -> int:
        return int(db.scalar(select(func.count()).select_from(model)) or 0)

    def count_proposals_by(status: ProposalStatus) -> int:
        return int(
            db.scalar(select(func.count()).select_from(ProposalModel).where(ProposalModel.status == status.value)) or 0
        )

    return MetricsOut(
        total_events=count_rows(EventModel),
        total_proposals=count_rows(ProposalModel),
        pending_review=count_proposals_by(ProposalStatus.PENDING_REVIEW),
        approved=count_proposals_by(ProposalStatus.APPROVED),
        rejected=count_proposals_by(ProposalStatus.REJECTED),
        applied=count_proposals_by(ProposalStatus.APPLIED),
    )


def event_type_from_datahub(entity_change_type: str) -> EventType:
    normalized = entity_change_type.lower()
    mapping = {
        "create": EventType.DATASET_CREATED,
        "schemafieldadd": EventType.SCHEMA_CHANGED,
        "addtag": EventType.TAG_CHANGED,
    }
    return mapping.get(normalized, EventType.SCHEMA_CHANGED)
