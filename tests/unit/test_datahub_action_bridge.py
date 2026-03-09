import pytest

from services.event_ingestion_service.app.datahub_action import DataHubMetaClassifierAction


class _MockResponse:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def raise_for_status(self) -> None:
        if self.should_fail:
            raise RuntimeError("http failure")


class _MockClient:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.calls: list[tuple[str, dict]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def post(self, url: str, json: dict):
        self.calls.append((url, json))
        return _MockResponse(should_fail=self.should_fail)


def test_action_forwards_to_ingestion_url(monkeypatch) -> None:
    mock = _MockClient()

    def fake_client(*args, **kwargs):
        return mock

    monkeypatch.setattr("services.event_ingestion_service.app.datahub_action.httpx.Client", fake_client)
    action = DataHubMetaClassifierAction({"event_ingestion_url": "http://event-ingestion:8001/ingest"})

    payload = {"id": "evt-bridge-1", "entityUrn": "urn:li:dataset:(a,b,c)", "changeType": "create"}
    action.act(payload)

    assert len(mock.calls) == 1
    assert mock.calls[0][0] == "http://event-ingestion:8001/ingest"
    assert mock.calls[0][1] == payload


def test_action_uses_env_default_url(monkeypatch) -> None:
    monkeypatch.setenv("EVENT_INGESTION_URL", "http://ingestion:8001/ingest")
    action = DataHubMetaClassifierAction({})
    assert action.ingestion_url == "http://ingestion:8001/ingest"


def test_action_propagates_non_2xx_failures(monkeypatch) -> None:
    mock = _MockClient(should_fail=True)

    def fake_client(*args, **kwargs):
        return mock

    monkeypatch.setattr("services.event_ingestion_service.app.datahub_action.httpx.Client", fake_client)
    action = DataHubMetaClassifierAction({"event_ingestion_url": "http://event-ingestion:8001/ingest"})

    payload = {"id": "evt-bridge-2", "entityUrn": "urn:li:dataset:(a,b,c)", "changeType": "create"}
    with pytest.raises(RuntimeError):
        action.act(payload)


def test_action_validates_required_identifiers() -> None:
    action = DataHubMetaClassifierAction({"event_ingestion_url": "http://event-ingestion:8001/ingest"})
    with pytest.raises(ValueError):
        action.act({"changeType": "create"})


def test_action_serializes_nested_event_objects(monkeypatch) -> None:
    mock = _MockClient()

    def fake_client(*args, **kwargs):
        return mock

    class _NestedObj:
        def to_obj(self):
            return {"nested": "value"}

    class _EventObj:
        def model_dump(self):
            return {
                "id": "evt-serial-1",
                "entityUrn": "urn:li:dataset:(a,b,c)",
                "changeType": "create",
                "extra": _NestedObj(),
            }

    class _Envelope:
        event = _EventObj()

    monkeypatch.setattr("services.event_ingestion_service.app.datahub_action.httpx.Client", fake_client)
    action = DataHubMetaClassifierAction({"event_ingestion_url": "http://event-ingestion:8001/ingest"})
    action.act(_Envelope())

    assert mock.calls[0][1]["extra"] == {"nested": "value"}
