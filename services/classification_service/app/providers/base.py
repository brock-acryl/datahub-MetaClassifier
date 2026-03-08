from abc import ABC, abstractmethod

from services.shared.schemas import ClassificationProposal, EventIn, KnowledgeSnapshot


class ClassificationProvider(ABC):
    @abstractmethod
    def classify(
        self,
        event_context: EventIn,
        knowledge_context: KnowledgeSnapshot,
        rules_context: dict,
    ) -> ClassificationProposal:
        raise NotImplementedError
