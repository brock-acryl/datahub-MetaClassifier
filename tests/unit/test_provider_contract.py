from services.classification_service.app.providers.base import ClassificationProvider
from services.classification_service.app.providers.openai_provider import OpenAIProvider
from services.shared.schemas import EventIn, EventType, KnowledgeSnapshot


def test_openai_provider_implements_contract() -> None:
    provider: ClassificationProvider = OpenAIProvider()
    proposal = provider.classify(
        EventIn(
            event_id="1",
            urn="urn:li:dataset:(analytics,users,PROD)",
            event_type=EventType.SCHEMA_CHANGED,
            change_summary="added pii column",
        ),
        KnowledgeSnapshot(domains=["analytics"], glossary_terms=["owner"], docs=[]),
        {"deny_tags": [], "force_tags": ["gold"]},
    )

    assert "gold" in proposal.tags
    assert proposal.confidence > 0
