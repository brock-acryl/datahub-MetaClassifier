from pathlib import Path


def test_compose_has_actions_runner_service() -> None:
    root = Path(__file__).resolve().parents[2]
    compose_text = (root / "docker-compose.yml").read_text(encoding="utf-8")

    assert "actions-runner:" in compose_text
    assert "datahub actions -c /app/config/actions.yaml" in compose_text
    assert "DATAHUB_GMS_URL" in compose_text
