from services.shared.domain import normalize_datahub_event
from services.shared.schemas import EventType


def test_normalize_datahub_event_dataset_created() -> None:
    payload = {
        "event": {
            "id": "evt-1",
            "entityUrn": "urn:li:dataset:(finance,sales,PROD)",
            "changeType": "create",
        },
        "changeSummary": "new dataset",
    }

    event = normalize_datahub_event(payload)

    assert event.event_id == "evt-1"
    assert event.urn.startswith("urn:li:dataset")
    assert event.event_type == EventType.DATASET_CREATED
    assert event.change_summary == "new dataset"
