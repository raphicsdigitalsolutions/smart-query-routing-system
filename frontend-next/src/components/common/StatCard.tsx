import type { ReactNode } from 'react';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

type StatTone = 'navy' | 'teal' | 'amber' | 'rose';

const ICON_TONES: Record<StatTone, string> = {
  navy: 'bg-navy-50 text-navy-700 ring-navy-100',
  teal: 'bg-teal-50 text-teal-700 ring-teal-100',
  amber: 'bg-amber-50 text-amber-700 ring-amber-100',
  rose: 'bg-rose-50 text-rose-600 ring-rose-100',
};

interface StatCardProps {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: ReactNode;
  tone?: StatTone;
  className?: string;
}

export function StatCard({ label, value, hint, icon, tone = 'teal', className }: StatCardProps) {
  return (
    <Card className={cn('group relative overflow-hidden p-5', className)}>
      <span className="absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r from-teal-500/70 to-teal-500/0" aria-hidden="true" />
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="eyebrow">{label}</p>
          <p className="mt-2 text-[1.75rem] font-semibold leading-none tracking-tight text-navy-900 tabular-nums">{value}</p>
          {hint ? <p className="mt-2 text-xs leading-relaxed text-slate-500">{hint}</p> : null}
        </div>
        {icon ? (
          <span className={cn('flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ring-1', ICON_TONES[tone])}>
            {icon}
          </span>
        ) : null}
      </div>
    </Card>
  );
}
