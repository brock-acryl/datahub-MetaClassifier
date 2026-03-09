"""
DataHub Action plugin scaffold.

Wire this class into DataHub Actions framework by configuring it as a custom action and
pointing EVENT_INGESTION_URL to this service.
"""

import os
from typing import Any

import httpx

try:
    from datahub_actions.action.action import Action
    from datahub_actions.event.event_envelope import EventEnvelope
    from datahub_actions.pipeline.pipeline_context import PipelineContext
except Exception:  # pragma: no cover - local fallback when DataHub Actions runtime isn't installed

    class Action:  # type: ignore[no-redef]
        pass

    EventEnvelope = Any  # type: ignore[misc,assignment]
    PipelineContext = Any  # type: ignore[misc,assignment]


class DataHubMetaClassifierAction(Action):
    def __init__(self, config: dict[str, Any], ctx: PipelineContext | None = None):
        self.ctx = ctx
        self.ingestion_url = config.get(
            "event_ingestion_url",
            os.getenv("EVENT_INGESTION_URL", "http://event-ingestion:8001/ingest"),
        )

    @classmethod
    def create(cls, config_dict: dict[str, Any], ctx: PipelineContext) -> "Action":
        return cls(config=config_dict, ctx=ctx)

    def act(self, event: EventEnvelope) -> None:
        payload = self._to_payload_dict(event)
        self._validate_event(payload)
        with httpx.Client(timeout=10.0) as client:
            client.post(self.ingestion_url, json=payload).raise_for_status()

    def close(self) -> None:
        return None

    @staticmethod
    def _to_payload_dict(event: EventEnvelope) -> dict[str, Any]:
        if isinstance(event, dict):
            return DataHubMetaClassifierAction._to_jsonable(event)
        raw_event = getattr(event, "event", None)
        payload_obj = raw_event if raw_event is not None else event
        payload = DataHubMetaClassifierAction._to_jsonable(payload_obj)
        if not isinstance(payload, dict):
            raise ValueError("Unable to convert DataHub event envelope to payload dict")
        return payload

    @staticmethod
    def _to_jsonable(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(k): DataHubMetaClassifierAction._to_jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [DataHubMetaClassifierAction._to_jsonable(v) for v in value]
        if hasattr(value, "model_dump"):
            try:
                return DataHubMetaClassifierAction._to_jsonable(value.model_dump(mode="json"))
            except TypeError:
                return DataHubMetaClassifierAction._to_jsonable(value.model_dump())
        if hasattr(value, "to_obj"):
            return DataHubMetaClassifierAction._to_jsonable(value.to_obj())
        if hasattr(value, "dict"):
            return DataHubMetaClassifierAction._to_jsonable(value.dict())
        if hasattr(value, "__dict__"):
            return DataHubMetaClassifierAction._to_jsonable(vars(value))
        return str(value)

    @staticmethod
    def _validate_event(event: dict[str, Any]) -> None:
        if not isinstance(event, dict):
            raise ValueError("Event payload must be a JSON object")
        if not (
            event.get("id")
            or event.get("event", {}).get("id")
            or event.get("entityUrn")
            or event.get("event", {}).get("entityUrn")
            or event.get("urn")
        ):
            raise ValueError("Event payload missing required identifier fields")
