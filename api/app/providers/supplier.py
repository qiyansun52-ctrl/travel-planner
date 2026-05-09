"""Supplier provider fallback for MVP."""
from __future__ import annotations

from app.providers.types import ProviderError, ProviderHealth, SupplierReference, SupplierRequest


class UnavailableSupplierProvider:
    name = "google"

    async def health(self) -> ProviderHealth:
        return ProviderHealth(ok=False, reason="Supplier provider is not configured")

    async def get_sample_references(self, request: SupplierRequest) -> list[SupplierReference]:
        raise ProviderError(
            provider=self.name,
            kind="supplier",
            code="capability_unavailable",
            message="Supplier provider is not configured",
        )


def create_unavailable_supplier_provider() -> UnavailableSupplierProvider:
    return UnavailableSupplierProvider()
