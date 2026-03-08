from services.classification_service.app.knowledge import resolve_knowledge_from_datahub


def test_knowledge_resolver_finance() -> None:
    result = resolve_knowledge_from_datahub("urn:li:dataset:(finance,ledger,PROD)")
    assert result.domains == ["finance"]
    assert "ledger" in result.glossary_terms
