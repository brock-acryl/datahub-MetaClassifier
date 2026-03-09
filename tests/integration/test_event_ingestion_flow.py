from fastapi.testclient import TestClient

from services.event_ingestion_service.app.main import app


def test_ingest_happy_duplicate_failure_and_ignore_paths(monkeypatch) -> None:
    client = TestClient(app)
    calls: list[str] = []

    def fake_trigger(event_id: str):
        calls.append(event_id)
        if event_id == "evt-int-fail":
            return ("trigger_failed", "simulated failure")
        return ("triggered", None)

    monkeypatch.setattr("services.event_ingestion_service.app.main._trigger_classification", fake_trigger)

    happy_payload = {
        "id": "evt-int-1",
        "entityUrn": "urn:li:dataset:(analytics,orders,PROD)",
        "changeType": "create",
        "changeSummary": "new dataset",
    }
    duplicate_payload = happy_payload.copy()
    failing_payload = {
        "id": "evt-int-fail",
        "entityUrn": "urn:li:dataset:(analytics,orders,PROD)",
        "changeType": "schemaFieldAdd",
        "changeSummary": "schema changed",
    }
    ignored_payload = {
        "id": "evt-int-ignore",
        "entityUrn": "urn:li:dataset:(analytics,orders,PROD)",
        "changeType": "ownershipChanged",
        "changeSummary": "owner changed",
    }

    happy = client.post("/ingest", json=happy_payload)
    dup = client.post("/ingest", json=duplicate_payload)
    failing = client.post("/ingest", json=failing_payload)
    ignored = client.post("/ingest", json=ignored_payload)

    assert happy.status_code == 200
    assert happy.json()["classification_trigger_status"] == "triggered"

    assert dup.status_code == 200
    assert dup.json()["ingestion_status"] == "duplicate_ignored"
    assert dup.json()["classification_trigger_status"] == "not_attempted"

    assert failing.status_code == 202
    assert failing.json()["classification_trigger_status"] == "trigger_failed"

    assert ignored.status_code == 200
    assert ignored.json()["ingestion_status"] == "ignored_event_type"

    assert calls == ["evt-int-1", "evt-int-fail"]
