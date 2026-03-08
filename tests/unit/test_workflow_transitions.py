from services.shared.domain import can_transition
from services.shared.schemas import ProposalStatus


def test_workflow_transitions() -> None:
    assert can_transition(ProposalStatus.PENDING_REVIEW, ProposalStatus.APPROVED)
    assert can_transition(ProposalStatus.PENDING_REVIEW, ProposalStatus.REJECTED)
    assert not can_transition(ProposalStatus.APPLIED, ProposalStatus.APPROVED)
