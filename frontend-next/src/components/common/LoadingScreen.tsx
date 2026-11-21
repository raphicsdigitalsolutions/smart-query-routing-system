import { cn } from '@/lib/utils';

interface LoadingScreenProps {
  label?: string;
  fullScreen?: boolean;
  className?: string;
}

export function LoadingScreen({
  label = 'Loading workspace…',
  fullScreen = true,
  className,
}: LoadingScreenProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-center gap-3 text-sm font-medium text-slate-500',
        fullScreen ? 'min-h-screen' : 'min-h-32',
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-navy-100 border-t-teal-600" aria-hidden="true" />
      {label}
    </div>
  );
}

export function LoadingInline({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-10 text-sm text-slate-500" role="status" aria-live="polite">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-navy-100 border-t-teal-600" aria-hidden="true" />
      {label}
    </div>
  );
}
