"""
DataHub Action plugin scaffold.

Wire this class into DataHub Actions framework by configuring it as a custom action and
pointing EVENT_INGESTION_URL to this service.
"""

from typing import Any

import httpx


class DataHubMetaClassifierAction:
    def __init__(self, config: dict[str, Any]):
        self.ingestion_url = config.get("event_ingestion_url", "http://event-ingestion:8001/ingest")

    def act(self, event: dict[str, Any]) -> None:
        with httpx.Client(timeout=10.0) as client:
            client.post(self.ingestion_url, json=event).raise_for_status()
