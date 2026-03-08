from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from services.shared.db import get_db, init_db
from services.shared.repository import (
    list_events,
    list_proposals,
    list_taxonomy_proposals,
    metrics,
    record_audit,
    record_sync_job,
    set_proposal_status,
)
from services.shared.schemas import (
    ApprovalDecision,
    FeedbackPayload,
    KnowledgeSyncRequest,
    ProposalStatus,
)

app = FastAPI(title="control-api")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def control_ui() -> FileResponse:
    root = Path(__file__).resolve().parents[3]
    return FileResponse(root / "services" / "control_ui" / "index.html")


@app.post("/config/knowledge-sync")
def knowledge_sync(req: KnowledgeSyncRequest, db: Session = Depends(get_db)) -> dict:
    job = record_sync_job(
        db,
        source=req.source,
        full_refresh=req.full_refresh,
        details={"status": "completed", "notes": "Stubbed DataHub knowledge sync"},
    )
    return {"sync_job_id": job.id, "status": job.status}


@app.get("/events")
def get_events(db: Session = Depends(get_db)) -> list[dict]:
    rows = list_events(db)
    return [
        {
            "event_id": e.event_id,
            "urn": e.urn,
            "event_type": e.event_type,
            "change_summary": e.change_summary,
            "status": e.status,
            "created_at": e.created_at,
        }
        for e in rows
    ]


@app.get("/events/{event_id}/logs")
def get_event_logs(event_id: str, db: Session = Depends(get_db)) -> dict:
    for event in list_events(db):
        if event.event_id == event_id:
            return {"event_id": event.event_id, "logs": event.logs}
    return {"event_id": event_id, "logs": []}


@app.get("/proposals")
def get_proposals(status: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    rows = list_proposals(db, status=status)
    return [
        {
            "id": p.id,
            "event_id": p.event_id,
            "urn": p.urn,
            "status": p.status,
            "review_decision": p.review_decision,
            "confidence": p.confidence,
            "rationale": p.rationale,
            "tags": p.tags,
            "glossary_terms": p.glossary_terms,
            "domain": p.domain,
            "unknown_concepts": p.unknown_concepts,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
        for p in rows
    ]


@app.post("/proposals/{proposal_id}/approve")
def approve(proposal_id: int, decision: ApprovalDecision, db: Session = Depends(get_db)) -> dict:
    updated = set_proposal_status(db, proposal_id, ProposalStatus.APPROVED, "approved")
    if not updated:
        return {"error": "proposal_not_found"}
    record_audit(db, "proposal_approved", decision.reviewer, {"proposal_id": proposal_id})
    return {"proposal_id": proposal_id, "status": updated.status}


@app.post("/proposals/{proposal_id}/reject")
def reject(proposal_id: int, decision: ApprovalDecision, db: Session = Depends(get_db)) -> dict:
    updated = set_proposal_status(db, proposal_id, ProposalStatus.REJECTED, "rejected")
    if not updated:
        return {"error": "proposal_not_found"}
    record_audit(db, "proposal_rejected", decision.reviewer, {"proposal_id": proposal_id})
    return {"proposal_id": proposal_id, "status": updated.status}


@app.post("/feedback")
def capture_feedback(payload: FeedbackPayload, db: Session = Depends(get_db)) -> dict:
    # Minimal pass-through for UI/API parity. Full rule updates are handled by feedback-service.
    record_audit(
        db,
        "feedback_received_via_control_api",
        "control-api",
        {"proposal_id": payload.proposal_id, "verdict": payload.verdict},
    )
    return {"status": "accepted"}


@app.get("/metrics/classification-overview")
def get_metrics(db: Session = Depends(get_db)) -> dict:
    return metrics(db).model_dump()


@app.get("/taxonomy/proposals")
def taxonomy_proposals(db: Session = Depends(get_db)) -> list[dict]:
    rows = list_taxonomy_proposals(db)
    return [
        {
            "id": p.id,
            "event_id": p.event_id,
            "concept": p.concept,
            "status": p.status,
            "created_at": p.created_at,
        }
        for p in rows
    ]
