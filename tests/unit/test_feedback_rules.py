from services.shared.domain import apply_rules
from services.shared.schemas import ClassificationProposal


def test_feedback_rules_are_applied() -> None:
    proposal = ClassificationProposal(
        tags=["auto_classified", "deprecated"],
        glossary_terms=["owner"],
        domain="analytics",
        unknown_concepts=[],
        rationale="",
        confidence=0.5,
    )

    updated = apply_rules(
        proposal,
        {"deny_tags": ["deprecated"], "force_tags": ["critical"], "force_domain": "finance"},
    )

    assert "deprecated" not in updated.tags
    assert "critical" in updated.tags
    assert updated.domain == "finance"
