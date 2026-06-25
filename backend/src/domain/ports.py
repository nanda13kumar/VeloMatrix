"""Domain ports (interfaces) — hexagonal boundary."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from domain.collection import EvidenceCollectionPayload
from domain.schemas import BindingSpec, EvidenceRecord, ProductScoreSnapshot


class IScoreRepository(ABC):
    """Persist and load score snapshots (replace with DB adapter)."""

    @abstractmethod
    async def get_latest_snapshot(self, product_id: str) -> ProductScoreSnapshot | None:
        ...

    @abstractmethod
    async def save_snapshot(self, snapshot: ProductScoreSnapshot) -> None:
        ...


class IEvidenceRepository(ABC):
    """Evidence ledger for provenance."""

    @abstractmethod
    async def list_for_subdimension(
        self, product_id: str, subdimension_id: str, limit: int = 20
    ) -> list[EvidenceRecord]:
        ...


class IAIExplainer(ABC):
    """GenAI explanations (live API or deterministic stub)."""

    @abstractmethod
    async def explain_subdimension(
        self,
        *,
        product_id: str,
        subdimension_id: str,
        user_question: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        ...


class IEvidenceConnector(ABC):
    """Pluggable datasource — registered in adapters.connectors.registry."""

    key: ClassVar[str] = "abstract"

    @abstractmethod
    async def collect(
        self,
        *,
        product_id: str,
        binding: BindingSpec,
    ) -> EvidenceCollectionPayload:
        ...
