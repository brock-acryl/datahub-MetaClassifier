from fastapi.testclient import TestClient

from services.event_ingestion_service.app.main import app
from services.shared.db import SessionLocal
from services.shared.models import EventModel


def test_unsupported_event_is_ignored_and_not_stored() -> None:
    client = TestClient(app)

    payload = {
        "id": "evt-ignored-1",
        "entityUrn": "urn:li:dataset:(analytics,orders,PROD)",
        "changeType": "ownershipChanged",
        "changeSummary": "owner changed",
    }

    resp = client.post("/ingest", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ingestion_status"] == "ignored_event_type"
    assert body["classification_trigger_status"] == "not_attempted"

    db = SessionLocal()
    try:
        found = db.query(EventModel).filter(EventModel.event_id == "evt-ignored-1").first()
        assert found is None
    finally:
        db.close()


def test_duplicate_event_is_idempotent(monkeypatch) -> None:
    client = TestClient(app)

    calls: list[str] = []

    def fake_trigger(event_id: str):
        calls.append(event_id)
        return ("triggered", None)

    monkeypatch.setattr("services.event_ingestion_service.app.main._trigger_classification", fake_trigger)

    payload = {
        "id": "evt-dup-1",
        "entityUrn": "urn:li:dataset:(analytics,orders,PROD)",
        "changeType": "schemaFieldAdd",
        "changeSummary": "added field",
    }

    first = client.post("/ingest", json=payload)
    second = client.post("/ingest", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["ingestion_status"] == "stored"
    assert second.json()["ingestion_status"] == "duplicate_ignored"
    assert len(calls) == 1


def test_trigger_failure_returns_202_and_persists_event(monkeypatch) -> None:
    client = TestClient(app)

    def fake_trigger(_event_id: str):
        return ("trigger_failed", "classification timeout")

    monkeypatch.setattr("services.event_ingestion_service.app.main._trigger_classification", fake_trigger)

    payload = {
        "id": "evt-fail-1",
        "entityUrn": "urn:li:dataset:(analytics,orders,PROD)",
        "changeType": "addTag",
        "changeSummary": "tag changed",
    }

    resp = client.post("/ingest", json=payload)
    assert resp.status_code == 202
    body = resp.json()
    assert body["ingestion_status"] == "stored"
    assert body["classification_trigger_status"] == "trigger_failed"
    assert "timeout" in body["classification_error"]

    db = SessionLocal()
    try:
        found = db.query(EventModel).filter(EventModel.event_id == "evt-fail-1").first()
        assert found is not None
    finally:
        db.close()
