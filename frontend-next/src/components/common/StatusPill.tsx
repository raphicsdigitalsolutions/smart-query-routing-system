import { PRETTY_LABELS } from '@/lib/api/types';
import { cn } from '@/lib/utils';

const STYLES: Record<string, string> = {
  healthy: 'bg-teal-50 text-teal-800 ring-teal-200/70',
  online: 'bg-teal-50 text-teal-800 ring-teal-200/70',
  completed: 'bg-teal-50 text-teal-800 ring-teal-200/70',
  checking: 'bg-sky-50 text-sky-700 ring-sky-200/70',
  new: 'bg-sky-50 text-sky-700 ring-sky-200/70',
  assigned: 'bg-indigo-50 text-indigo-700 ring-indigo-200/70',
  in_progress: 'bg-teal-50 text-teal-800 ring-teal-200/70',
  waiting_for_student: 'bg-amber-50 text-amber-800 ring-amber-200/70',
  resolved: 'bg-emerald-50 text-emerald-800 ring-emerald-200/70',
  closed: 'bg-slate-100 text-slate-600 ring-slate-200',
  planned: 'bg-slate-100 text-slate-600 ring-slate-200',
  urgent: 'bg-rose-50 text-rose-700 ring-rose-200/70',
  high: 'bg-amber-50 text-amber-800 ring-amber-200/70',
  normal: 'bg-slate-100 text-slate-600 ring-slate-200',
  low: 'bg-slate-100 text-slate-600 ring-slate-200',
  offline: 'bg-rose-50 text-rose-700 ring-rose-200/70',
  failed: 'bg-rose-50 text-rose-700 ring-rose-200/70',
};

interface StatusPillProps {
  status: string;
  label?: string;
  className?: string;
}

export function StatusPill({ status, label, className }: StatusPillProps) {
  const style = STYLES[status] ?? STYLES.planned;
  const text = label ?? PRETTY_LABELS[status] ?? status.replaceAll('_', ' ');
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1 ring-inset',
        style,
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      {text}
    </span>
  );
}
