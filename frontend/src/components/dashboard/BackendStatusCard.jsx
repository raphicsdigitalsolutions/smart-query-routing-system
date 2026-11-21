import { RefreshCw, Server } from 'lucide-react';
import useBackendStatus from '../../hooks/useBackendStatus';
import { API_BASE_URL } from '../../services/api';
import StatusPill from '../common/StatusPill';
import ErrorState from '../common/ErrorState';

export default function BackendStatusCard() {
  const { status, data, error, refresh } = useBackendStatus();

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm" aria-live="polite">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy-50 text-navy-800">
            <Server className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-navy-900">Backend connection</h3>
            <p className="mt-0.5 text-xs text-slate-500">FastAPI service via /health</p>
          </div>
        </div>
        <StatusPill status={status === 'checking' ? 'checking' : status === 'online' ? 'healthy' : 'offline'} />
      </div>

      <div className="mt-4">
        {status === 'checking' && (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" />
            Checking backend connection…
          </div>
        )}

        {status === 'online' && (
          <div className="rounded-lg bg-teal-50 px-4 py-3 text-sm text-teal-800">
            <p className="font-medium">API is responding normally.</p>
            <p className="mt-1 text-xs">
              Status: {data?.status} · Version: {data?.version} · {API_BASE_URL}
            </p>
          </div>
        )}

        {status === 'offline' && (
          <ErrorState
            compact
            title="Backend unreachable"
            message={`${error} Start the API on ${API_BASE_URL} or check VITE_API_BASE_URL.`}
            onRetry={refresh}
          />
        )}
      </div>
    </section>
  );
}
