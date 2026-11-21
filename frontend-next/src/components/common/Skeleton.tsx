import { cn } from '@/lib/utils';

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('skeleton', className)} aria-hidden="true" />;
}

export function TableSkeleton({ rows = 5, columns = 5 }: { rows?: number; columns?: number }) {
  return (
    <div className="surface-card overflow-hidden" role="status" aria-label="Loading records" aria-live="polite">
      <div className="flex items-center gap-4 border-b border-slate-100 bg-slate-50/70 px-5 py-3">
        {Array.from({ length: columns }).map((_, index) => (
          <Skeleton key={index} className="h-3 flex-1" />
        ))}
      </div>
      <div className="divide-y divide-slate-100">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="flex items-center gap-4 px-5 py-4">
            {Array.from({ length: columns }).map((_, columnIndex) => (
              <Skeleton key={columnIndex} className={cn('h-4 flex-1', columnIndex === columns - 1 && 'max-w-10')} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function StatSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className={cn('grid gap-4', count === 2 ? 'sm:grid-cols-2' : 'sm:grid-cols-2 lg:grid-cols-3')} aria-label="Loading statistics">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="surface-card p-5">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="mt-4 h-8 w-16" />
          <Skeleton className="mt-3 h-3 w-32" />
        </div>
      ))}
    </div>
  );
}

export function DetailSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading ticket" aria-live="polite">
      <Skeleton className="h-4 w-28" />
      <div className="surface-card space-y-4 p-6">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-7 w-2/3" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <div className="grid gap-4 pt-4 sm:grid-cols-3">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="surface-card h-72 p-6"><Skeleton className="h-full w-full" /></div>
        <div className="surface-card h-72 p-6"><Skeleton className="h-full w-full" /></div>
      </div>
    </div>
  );
}
