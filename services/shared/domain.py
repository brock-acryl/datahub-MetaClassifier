from typing import Any

from services.shared.schemas import (
    ClassificationProposal,
    EventIn,
    EventType,
    KnowledgeSnapshot,
    ProposalStatus,
)


def extract_change_type(payload: dict[str, Any]) -> str:
    return str(payload.get("changeType") or payload.get("event", {}).get("changeType") or "schemaFieldAdd").lower()


def is_supported_datahub_event(payload: dict[str, Any]) -> bool:
    change_type = extract_change_type(payload)
    if change_type in {"create", "datasetcreated"}:
        return True
    if "schema" in change_type:
        return True
    if "tag" in change_type:
        return True
    return False


def normalize_datahub_event(payload: dict[str, Any]) -> EventIn:
    event_id = str(payload.get("event", {}).get("id") or payload.get("id") or "")
    urn = str(payload.get("entityUrn") or payload.get("event", {}).get("entityUrn") or payload.get("urn") or "")
    change_type = extract_change_type(payload)

    if change_type in {"create", "datasetcreated"}:
        event_type = EventType.DATASET_CREATED
    elif "tag" in change_type:
        event_type = EventType.TAG_CHANGED
    else:
        event_type = EventType.SCHEMA_CHANGED

    if not event_id:
        event_id = f"{urn}:{change_type}"

    summary = str(payload.get("changeSummary") or payload.get("summary") or "DataHub metadata change")
    return EventIn(
        event_id=event_id,
        urn=urn,
        event_type=event_type,
        change_summary=summary,
        raw_payload=payload,
    )


def apply_rules(base: ClassificationProposal, rules: dict[str, Any]) -> ClassificationProposal:
    deny_tags = set(rules.get("deny_tags", []))
    forced_tags = set(rules.get("force_tags", []))
    filtered_tags = [tag for tag in base.tags if tag not in deny_tags]
    filtered_tags.extend(sorted(forced_tags - set(filtered_tags)))
    base.tags = filtered_tags
    if rules.get("force_domain"):
        base.domain = str(rules["force_domain"])
    return base


def can_transition(current: ProposalStatus, target: ProposalStatus) -> bool:
    allowed = {
        ProposalStatus.PENDING_REVIEW: {ProposalStatus.APPROVED, ProposalStatus.REJECTED},
        ProposalStatus.APPROVED: {ProposalStatus.APPLIED, ProposalStatus.REJECTED},
        ProposalStatus.REJECTED: {ProposalStatus.PENDING_REVIEW},
        ProposalStatus.APPLIED: set(),
    }
    return target in allowed[current]


def writeback_payload(urn: str, proposal: ClassificationProposal) -> dict[str, Any]:
    return {
        "entityUrn": urn,
        "tags": proposal.tags,
        "glossaryTerms": proposal.glossary_terms,
        "domain": proposal.domain,
    }


def merge_knowledge(primary: KnowledgeSnapshot, supplemental: KnowledgeSnapshot) -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        domains=sorted(set(primary.domains + supplemental.domains)),
        glossary_terms=sorted(set(primary.glossary_terms + supplemental.glossary_terms)),
        docs=primary.docs + supplemental.docs,
    )
