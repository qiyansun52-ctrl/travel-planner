import {
  ProviderError,
  SupplierProvider,
  SupplierReference,
} from "../types"

export class UnavailableSupplierProvider implements SupplierProvider {
  readonly name = "google" as const

  async health() {
    return { ok: false, reason: "Supplier provider is not configured" }
  }

  async getSampleReferences(): Promise<SupplierReference[]> {
    throw new ProviderError({
      provider: this.name,
      kind: "supplier",
      code: "capability_unavailable",
      message: "Supplier provider is not configured",
    })
  }
}

export function createUnavailableSupplierProvider(): SupplierProvider {
  return new UnavailableSupplierProvider()
}
