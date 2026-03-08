from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    DATASET_CREATED = "dataset_created"
    SCHEMA_CHANGED = "schema_changed"
    TAG_CHANGED = "tag_changed"


class ProposalStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class EventIn(BaseModel):
    event_id: str
    urn: str
    event_type: EventType
    change_summary: str
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSnapshot(BaseModel):
    domains: list[str] = Field(default_factory=list)
    glossary_terms: list[str] = Field(default_factory=list)
    docs: list[str] = Field(default_factory=list)


class ClassificationProposal(BaseModel):
    tags: list[str] = Field(default_factory=list)
    glossary_terms: list[str] = Field(default_factory=list)
    domain: str | None = None
    unknown_concepts: list[str] = Field(default_factory=list)
    rationale: str
    confidence: float


class ClassificationResult(BaseModel):
    event: EventIn
    knowledge_snapshot: KnowledgeSnapshot
    proposal: ClassificationProposal
    model_metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecision(BaseModel):
    reviewer: str = "system"
    reason: str = ""


class FeedbackPayload(BaseModel):
    proposal_id: int
    verdict: str
    comment: str = ""
    corrections: dict[str, Any] = Field(default_factory=dict)


class ProposalOut(BaseModel):
    id: int
    event_id: str
    urn: str
    status: ProposalStatus
    review_decision: str | None
    confidence: float
    rationale: str
    tags: list[str]
    glossary_terms: list[str]
    domain: str | None
    unknown_concepts: list[str]
    created_at: datetime
    updated_at: datetime


class EventOut(BaseModel):
    event_id: str
    urn: str
    event_type: EventType
    status: ProposalStatus
    change_summary: str
    created_at: datetime


class MetricsOut(BaseModel):
    total_events: int
    total_proposals: int
    pending_review: int
    approved: int
    rejected: int
    applied: int


class KnowledgeSyncRequest(BaseModel):
    source: str = "datahub"
    full_refresh: bool = False


class AuditRecord(BaseModel):
    action: str
    actor: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
