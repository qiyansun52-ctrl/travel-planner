import { Skeleton } from "@/components/ui/Skeleton"

export function DiscoveryCardSkeleton() {
  return (
    <div
      data-testid="discovery-card-skeleton"
      className="flex min-h-64 flex-col overflow-hidden rounded-[var(--radius-card)] border border-slate-200 bg-white shadow-[var(--shadow-card)]"
    >
      <Skeleton className="h-40 w-full rounded-none" />
      <div className="flex flex-1 flex-col gap-3 p-4">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <div className="flex gap-2">
          <Skeleton className="h-5 w-12" />
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-5 w-10" />
        </div>
        <div className="mt-auto flex items-center justify-between">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-9 w-16 rounded-md" />
        </div>
      </div>
    </div>
  )
}
