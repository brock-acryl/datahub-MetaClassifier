from fastapi.testclient import TestClient

from services.classification_service.app.main import app as classification_app
from services.control_api.app.main import app as control_api_app
from services.shared.db import SessionLocal
from services.shared.repository import log_event
from services.shared.schemas import EventIn, EventType
from services.writeback_service.app.main import app as writeback_app


def test_end_to_end_classify_approve_writeback() -> None:
    db = SessionLocal()
    log_event(
        db,
        EventIn(
            event_id="evt-e2e-1",
            urn="urn:li:dataset:(finance,payments,PROD)",
            event_type=EventType.SCHEMA_CHANGED,
            change_summary="added pii field",
        ),
    )
    db.close()

    classify_client = TestClient(classification_app)
    classify_resp = classify_client.post("/classify", json={"event_id": "evt-e2e-1"})
    assert classify_resp.status_code == 200

    control_client = TestClient(control_api_app)
    proposals = control_client.get("/proposals?status=pending_review").json()
    assert len(proposals) >= 1
    proposal_id = proposals[0]["id"]

    approve_resp = control_client.post(
        f"/proposals/{proposal_id}/approve",
        json={"reviewer": "qa", "reason": "looks good"},
    )
    assert approve_resp.status_code == 200

    writeback_client = TestClient(writeback_app)
    writeback_resp = writeback_client.post(f"/writeback/{proposal_id}")
    assert writeback_resp.status_code == 200
    assert writeback_resp.json()["status"] == "applied"


def test_unknown_concept_routes_to_taxonomy_queue() -> None:
    db = SessionLocal()
    log_event(
        db,
        EventIn(
            event_id="evt-e2e-2",
            urn="urn:li:dataset:(analytics,unknown_source,PROD)",
            event_type=EventType.SCHEMA_CHANGED,
            change_summary="unknown business concept found",
        ),
    )
    db.close()

    classify_client = TestClient(classification_app)
    classify_resp = classify_client.post("/classify", json={"event_id": "evt-e2e-2"})
    assert classify_resp.status_code == 200

    control_client = TestClient(control_api_app)
    taxonomy = control_client.get("/taxonomy/proposals").json()
    assert any(row["event_id"] == "evt-e2e-2" for row in taxonomy)
