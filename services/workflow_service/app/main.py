from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from services.shared.db import get_db, init_db
from services.shared.domain import can_transition
from services.shared.repository import get_proposal, record_audit, set_proposal_status
from services.shared.schemas import ApprovalDecision, ProposalStatus

app = FastAPI(title="workflow-service")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/proposals/{proposal_id}/approve")
def approve(proposal_id: int, decision: ApprovalDecision, db: Session = Depends(get_db)) -> dict[str, str | int]:
    proposal = get_proposal(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="proposal_not_found")

    current = ProposalStatus(proposal.status)
    if not can_transition(current, ProposalStatus.APPROVED):
        raise HTTPException(status_code=400, detail="invalid_transition")

    updated = set_proposal_status(db, proposal_id, ProposalStatus.APPROVED, "approved")
    if not updated:
        raise HTTPException(status_code=500, detail="proposal_update_failed")
    record_audit(
        db,
        "proposal_approved",
        decision.reviewer,
        {"proposal_id": proposal_id, "reason": decision.reason},
    )
    return {"proposal_id": proposal_id, "status": str(updated.status)}


@app.post("/proposals/{proposal_id}/reject")
def reject(proposal_id: int, decision: ApprovalDecision, db: Session = Depends(get_db)) -> dict[str, str | int]:
    proposal = get_proposal(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="proposal_not_found")

    current = ProposalStatus(proposal.status)
    if not can_transition(current, ProposalStatus.REJECTED):
        raise HTTPException(status_code=400, detail="invalid_transition")

    updated = set_proposal_status(db, proposal_id, ProposalStatus.REJECTED, "rejected")
    if not updated:
        raise HTTPException(status_code=500, detail="proposal_update_failed")
    record_audit(
        db,
        "proposal_rejected",
        decision.reviewer,
        {"proposal_id": proposal_id, "reason": decision.reason},
    )
    return {"proposal_id": proposal_id, "status": str(updated.status)}
