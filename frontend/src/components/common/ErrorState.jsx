import { AlertCircle, RefreshCw } from 'lucide-react';

export default function ErrorState({
  title = 'Something went wrong',
  message = 'Please try again in a moment.',
  onRetry,
  compact = false,
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 text-center ${compact ? 'px-4 py-5' : 'px-6 py-12'}`}
      role="alert"
    >
      <AlertCircle className={`${compact ? 'h-6 w-6' : 'h-8 w-8'} text-rose-500`} aria-hidden="true" />
      <p className={`${compact ? 'mt-2 text-sm' : 'mt-3 text-base'} font-semibold text-navy-900`}>
        {title}
      </p>
      <p className="mt-1 max-w-md text-sm text-slate-500">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-navy-900 px-3.5 py-2 text-sm font-semibold text-white hover:bg-navy-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          Try again
        </button>
      )}
    </div>
  );
}
