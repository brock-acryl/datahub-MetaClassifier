from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from services.shared.db import get_db, init_db
from services.shared.repository import (
    get_proposal,
    record_audit,
    store_feedback,
    upsert_rule_memory,
)
from services.shared.schemas import FeedbackPayload

app = FastAPI(title="feedback-service")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/feedback")
def feedback(payload: FeedbackPayload, db: Session = Depends(get_db)) -> dict:
    proposal = get_proposal(db, payload.proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="proposal_not_found")

    item = store_feedback(
        db,
        proposal_id=payload.proposal_id,
        verdict=payload.verdict,
        comment=payload.comment,
        corrections=payload.corrections,
    )

    if payload.corrections.get("force_domain"):
        upsert_rule_memory(
            db,
            "global:force_domain",
            {"value": payload.corrections["force_domain"]},
            source="feedback",
        )
    if payload.corrections.get("deny_tags"):
        upsert_rule_memory(
            db,
            "global:deny_tags",
            {"items": payload.corrections["deny_tags"]},
            source="feedback",
        )
    if payload.corrections.get("force_tags"):
        upsert_rule_memory(
            db,
            "global:force_tags",
            {"items": payload.corrections["force_tags"]},
            source="feedback",
        )

    record_audit(db, "feedback_recorded", "feedback-service", {"feedback_id": item.id})
    return {"feedback_id": item.id, "status": "recorded"}
