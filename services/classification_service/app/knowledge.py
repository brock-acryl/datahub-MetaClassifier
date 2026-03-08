from services.shared.schemas import KnowledgeSnapshot


def resolve_knowledge_from_datahub(urn: str) -> KnowledgeSnapshot:
    """Stubbed DataHub knowledge resolver. Replace with GraphQL/REST fetch in production."""
    if "finance" in urn:
        return KnowledgeSnapshot(
            domains=["finance"],
            glossary_terms=["ledger", "revenue", "cost_center"],
            docs=["Finance data quality policy v2"],
        )
    return KnowledgeSnapshot(
        domains=["analytics"],
        glossary_terms=["dataset", "owner", "sla"],
        docs=["Default metadata governance guide"],
    )
