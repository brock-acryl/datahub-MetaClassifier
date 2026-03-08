import json

from services.classification_service.app.providers.openai_provider import OpenAIProvider
from services.shared.schemas import EventIn, EventType, KnowledgeSnapshot


def _event() -> EventIn:
    return EventIn(
        event_id="e1",
        urn="urn:li:dataset:(analytics,users,PROD)",
        event_type=EventType.SCHEMA_CHANGED,
        change_summary="added pii field",
    )


def _knowledge() -> KnowledgeSnapshot:
    return KnowledgeSnapshot(domains=["analytics"], glossary_terms=["owner"], docs=[])


def test_chat_completion_url_normalization() -> None:
    assert (
        OpenAIProvider._chat_completions_url("https://api.openai.com") == "https://api.openai.com/v1/chat/completions"
    )
    assert (
        OpenAIProvider._chat_completions_url("http://localhost:11434/v1")
        == "http://localhost:11434/v1/chat/completions"
    )


def test_openai_compatible_response_parsing(monkeypatch) -> None:
    provider = OpenAIProvider(base_url="http://localhost:11434/v1", api_key="", model="local-model")

    def fake_request(*_args, **_kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "tags": ["sensitive"],
                                "glossary_terms": ["pii"],
                                "domain": "analytics",
                                "unknown_concepts": [],
                                "rationale": "model",
                                "confidence": 0.91,
                            }
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(provider, "_request_chat_completion", fake_request)

    proposal = provider.classify(_event(), _knowledge(), {})

    assert proposal.tags == ["sensitive"]
    assert proposal.domain == "analytics"
    assert proposal.confidence == 0.91


def test_openai_compatible_failure_falls_back_to_heuristic(monkeypatch) -> None:
    provider = OpenAIProvider(base_url="http://localhost:9999/v1", api_key="", model="local-model")

    def fail_request(*_args, **_kwargs):
        raise RuntimeError("endpoint down")

    monkeypatch.setattr(provider, "_request_chat_completion", fail_request)

    proposal = provider.classify(_event(), _knowledge(), {})

    assert "auto_classified" in proposal.tags
    assert proposal.domain == "analytics"
