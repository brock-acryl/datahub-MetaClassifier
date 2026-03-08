from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from services.shared.db import get_db, init_db
from services.shared.domain import writeback_payload
from services.shared.repository import get_proposal, record_audit, set_proposal_status
from services.shared.schemas import ClassificationProposal, ProposalStatus

app = FastAPI(title="writeback-service")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/writeback/{proposal_id}")
def apply_writeback(proposal_id: int, db: Session = Depends(get_db)) -> dict:
    proposal = get_proposal(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="proposal_not_found")
    if proposal.status != ProposalStatus.APPROVED.value:
        raise HTTPException(status_code=400, detail="proposal_not_approved")

    payload = writeback_payload(
        proposal.urn,
        ClassificationProposal(
            tags=proposal.tags,
            glossary_terms=proposal.glossary_terms,
            domain=proposal.domain,
            unknown_concepts=proposal.unknown_concepts,
            rationale=proposal.rationale,
            confidence=proposal.confidence,
        ),
    )

    set_proposal_status(db, proposal_id, ProposalStatus.APPLIED, "applied")
    record_audit(db, "writeback_applied", "writeback-service", {"proposal_id": proposal_id})
    return {"proposal_id": proposal_id, "writeback_payload": payload, "status": "applied"}
