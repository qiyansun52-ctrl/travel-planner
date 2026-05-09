export function isContinueDisabled(selectedCardIds: string[]): boolean {
  return normalizeSelectedCardIds(selectedCardIds).length === 0
}

export function hasDensityWarning(selectedCount: number, durationDays: number): boolean {
  return selectedCount > durationDays * 5
}

export function normalizeSelectedCardIds(selectedCardIds: string[]): string[] {
  return Array.from(new Set(selectedCardIds.filter(Boolean)))
}
