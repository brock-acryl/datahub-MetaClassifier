import json
from typing import Any

import httpx

from services.classification_service.app.providers.base import ClassificationProvider
from services.shared.config import settings
from services.shared.domain import apply_rules
from services.shared.schemas import ClassificationProposal, EventIn, KnowledgeSnapshot


class OpenAIProvider(ClassificationProvider):
    """OpenAI-compatible provider with heuristic fallback."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (base_url or settings.openai_base_url).strip()
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.model = model or settings.classifier_model
        self.timeout_seconds = timeout_seconds or settings.openai_timeout_seconds

    def classify(
        self,
        event_context: EventIn,
        knowledge_context: KnowledgeSnapshot,
        rules_context: dict,
    ) -> ClassificationProposal:
        remote_proposal = self._classify_via_openai_compatible(event_context, knowledge_context)
        if remote_proposal is not None:
            return apply_rules(remote_proposal, rules_context)

        return apply_rules(self._heuristic_proposal(event_context, knowledge_context), rules_context)

    def _classify_via_openai_compatible(
        self,
        event_context: EventIn,
        knowledge_context: KnowledgeSnapshot,
    ) -> ClassificationProposal | None:
        try:
            response_json = self._request_chat_completion(event_context, knowledge_context)
            content = self._extract_text_content(response_json)
            data = json.loads(content)
            return ClassificationProposal(**data)
        except Exception:
            return None

    def _request_chat_completion(self, event_context: EventIn, knowledge_context: KnowledgeSnapshot) -> dict[str, Any]:
        url = self._chat_completions_url(self.base_url)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You classify DataHub metadata events. "
                        "Return JSON with keys: tags (string[]), glossary_terms (string[]), "
                        "domain (string or null), unknown_concepts (string[]), rationale (string), "
                        "confidence (number from 0 to 1)."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "event": event_context.model_dump(),
                            "knowledge_snapshot": knowledge_context.model_dump(),
                        }
                    ),
                },
            ],
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return dict(response.json())

    @staticmethod
    def _chat_completions_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if not normalized.endswith("/v1"):
            normalized = f"{normalized}/v1"
        return f"{normalized}/chat/completions"

    @staticmethod
    def _extract_text_content(response_json: dict[str, Any]) -> str:
        choices = response_json.get("choices", [])
        if not choices:
            raise ValueError("No choices in completion response")

        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
            return "".join(text_parts)
        if not isinstance(content, str):
            raise ValueError("Unexpected content type in completion response")
        return content

    @staticmethod
    def _heuristic_proposal(
        event_context: EventIn,
        knowledge_context: KnowledgeSnapshot,
    ) -> ClassificationProposal:
        tags = ["auto_classified"]
        if "pii" in event_context.change_summary.lower():
            tags.append("sensitive")

        domain = knowledge_context.domains[0] if knowledge_context.domains else "general"
        unknown_concepts: list[str] = []
        if "unknown" in event_context.change_summary.lower():
            unknown_concepts.append("unknown-concept")

        return ClassificationProposal(
            tags=tags,
            glossary_terms=knowledge_context.glossary_terms[:3],
            domain=domain,
            unknown_concepts=unknown_concepts,
            rationale="Heuristic baseline classification with DataHub context.",
            confidence=0.72,
        )
