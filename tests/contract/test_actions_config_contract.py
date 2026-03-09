from pathlib import Path


def test_actions_config_references_metaclassifier_action_and_ingestion_url() -> None:
    root = Path(__file__).resolve().parents[2]
    config_text = (root / "config" / "actions.yaml").read_text(encoding="utf-8")

    assert "services.event_ingestion_service.app.datahub_action:DataHubMetaClassifierAction" in config_text
    assert "event_ingestion_url: http://event-ingestion:8001/ingest" in config_text
    assert "type: datahub-cloud" in config_text
    assert "datahub:" in config_text
    assert "server: ${DATAHUB_GMS_URL:-http://datahub-gms:8080}" in config_text
