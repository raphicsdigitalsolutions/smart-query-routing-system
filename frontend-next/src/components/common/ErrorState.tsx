'use client';

import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  compact?: boolean;
  className?: string;
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  compact = false,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn('rounded-xl border border-rose-200 bg-rose-50/80', compact ? 'p-3.5' : 'p-6', className)}
    >
      <div className="flex gap-3">
        <span className={cn('flex shrink-0 items-center justify-center rounded-lg bg-rose-100 text-rose-600', compact ? 'h-7 w-7' : 'h-9 w-9')}>
          <AlertCircle className={cn('h-4 w-4', !compact && 'h-5 w-5')} aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className={cn('font-semibold text-rose-900', compact ? 'text-xs' : 'text-sm')}>{title}</p>
          <p className={cn('mt-1 leading-relaxed text-rose-700', compact ? 'text-xs' : 'text-sm')}>{message}</p>
          {onRetry ? (
            <Button variant="outline" size="sm" className="mt-3 border-rose-200 bg-white text-rose-700 hover:bg-rose-50" onClick={onRetry}>
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Try again
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
