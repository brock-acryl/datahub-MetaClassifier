from fastapi.testclient import TestClient

from services.event_ingestion_service.app.main import app


def test_ingest_response_contract_includes_status_fields(monkeypatch) -> None:
    client = TestClient(app)

    def fake_trigger(_event_id: str):
        return ("triggered", None)

    monkeypatch.setattr("services.event_ingestion_service.app.main._trigger_classification", fake_trigger)

    payload = {
        "id": "evt-contract-1",
        "entityUrn": "urn:li:dataset:(analytics,orders,PROD)",
        "changeType": "create",
        "changeSummary": "new dataset",
    }

    resp = client.post("/ingest", json=payload)
    assert resp.status_code == 200
    body = resp.json()

    assert "event" in body
    assert "ingestion_status" in body
    assert "classification_trigger_status" in body
    assert "classification_error" in body
    assert body["event"]["event_id"] == "evt-contract-1"
