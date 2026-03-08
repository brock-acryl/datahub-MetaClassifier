from services.shared.domain import normalize_datahub_event
from services.shared.schemas import EventType


def test_datahub_payload_compatibility() -> None:
    payload = {
        "id": "evt-2",
        "entityUrn": "urn:li:dataset:(analytics,orders,PROD)",
        "changeType": "addTag",
        "changeSummary": "tag changed",
    }

    event = normalize_datahub_event(payload)

    assert event.event_id == "evt-2"
    assert event.event_type == EventType.TAG_CHANGED
