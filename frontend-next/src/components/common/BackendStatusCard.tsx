'use client';

import { Activity, Server } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { StatusPill } from './StatusPill';
import { ErrorState } from './ErrorState';
import { useBackendStatus } from '@/hooks/useBackendStatus';
import { API_BASE_URL } from '@/lib/config';

const PILL: Record<string, string> = {
  checking: 'checking',
  online: 'healthy',
  offline: 'offline',
};

export function BackendStatusCard() {
  const { status, data, error, refresh } = useBackendStatus();

  return (
    <Card className="p-5 sm:p-6" aria-live="polite">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-navy-50 text-navy-700 ring-1 ring-navy-100">
            <Server className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <p className="text-sm font-semibold text-navy-900">Backend connection</p>
            <p className="text-xs text-slate-500">FastAPI service health</p>
          </div>
        </div>
        <StatusPill status={PILL[status] ?? 'offline'} />
      </div>

      <div className="mt-5 text-sm">
        {status === 'checking' ? (
          <p className="text-slate-500">Checking backend connection…</p>
        ) : status === 'online' ? (
          <div className="rounded-xl border border-teal-100 bg-teal-50/70 p-4">
            <p className="flex items-center gap-2 font-medium text-teal-900">
              <Activity className="h-4 w-4" aria-hidden="true" /> Connected and healthy
            </p>
            <p className="mt-1.5 text-xs text-teal-800">Reported status: {data?.status ?? 'healthy'}</p>
            <p className="mt-2 break-all rounded-md bg-white/70 px-2 py-1.5 font-mono text-[11px] text-teal-800">
              {API_BASE_URL}
            </p>
          </div>
        ) : (
          <ErrorState compact title="Backend unavailable" message={error} onRetry={refresh} />
        )}
      </div>
    </Card>
  );
}
