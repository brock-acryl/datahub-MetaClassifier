from services.shared.domain import writeback_payload
from services.shared.schemas import ClassificationProposal


def test_writeback_payload_shape() -> None:
    payload = writeback_payload(
        "urn:li:dataset:(analytics,users,PROD)",
        ClassificationProposal(
            tags=["sensitive"],
            glossary_terms=["pii"],
            domain="analytics",
            unknown_concepts=[],
            rationale="test",
            confidence=0.9,
        ),
    )

    assert payload["entityUrn"].startswith("urn:li:dataset")
    assert payload["tags"] == ["sensitive"]
    assert payload["domain"] == "analytics"
