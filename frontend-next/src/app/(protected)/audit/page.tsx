'use client';

import { useCallback, useEffect, useState } from 'react';
import { Loader2, PlayCircle, ScrollText, ShieldAlert } from 'lucide-react';
import { toast } from 'sonner';
import { RoleGuard } from '@/components/auth/RoleGuard';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { PageHeader } from '@/components/common/PageHeader';
import { Pagination } from '@/components/common/Pagination';
import { TableSkeleton } from '@/components/common/Skeleton';
import { StatusPill } from '@/components/common/StatusPill';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { auditApi, escalationApi } from '@/lib/api/endpoints';
import { getApiErrorMessage } from '@/lib/api/errors';
import type { AuditLogEntry } from '@/lib/api/types';
import { formatDateTime, prettyLabel } from '@/lib/utils';

const LIMIT = 20;
const ROLE_OPTIONS = ['student', 'staff', 'hod', 'admin'];

function AuditWorkspace() {
  const [items, setItems] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(0);
  const [filters, setFilters] = useState({ action: '', entity_type: '', actor_role: '', override: '' });
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await auditApi.list({
        action: filters.action.trim() || undefined,
        entity_type: filters.entity_type.trim() || undefined,
        actor_role: filters.actor_role || undefined,
        is_override: filters.override || undefined,
        skip: page * LIMIT,
        limit: LIMIT,
      });
      setItems(result.items);
      setTotal(result.total);
    } catch (cause) {
      setError(getApiErrorMessage(cause, 'Unable to load the audit log.'));
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function runEscalation() {
    setRunning(true);
    try {
      const result = await escalationApi.run();
      toast.success(`Escalation check complete · ${result.scanned} scanned, ${result.escalated} escalated.`);
    } catch (cause) {
      toast.error(getApiErrorMessage(cause, 'Unable to run the escalation check.'));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Workspace tools"
        title="Audit log"
        description="A real record of sensitive actions and overrides. Backend authorization remains authoritative."
        icon={<ScrollText className="h-6 w-6" aria-hidden="true" />}
        actions={
          <Button variant="outline" onClick={() => void runEscalation()} disabled={running}>
            {running ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <PlayCircle className="h-4 w-4" aria-hidden="true" />}
            Run escalation check
          </Button>
        }
      />

      <Card className="p-5 sm:p-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label htmlFor="audit-action" className="field-label">Action</label>
            <input
              id="audit-action"
              value={filters.action}
              onChange={(event) => { setFilters({ ...filters, action: event.target.value }); setPage(0); }}
              placeholder="e.g. ticket.assign"
              className="field-input"
            />
          </div>
          <div>
            <label htmlFor="audit-entity" className="field-label">Entity type</label>
            <input
              id="audit-entity"
              value={filters.entity_type}
              onChange={(event) => { setFilters({ ...filters, entity_type: event.target.value }); setPage(0); }}
              placeholder="e.g. ticket"
              className="field-input"
            />
          </div>
          <div>
            <label htmlFor="audit-role" className="field-label">Actor role</label>
            <select
              id="audit-role"
              value={filters.actor_role}
              onChange={(event) => { setFilters({ ...filters, actor_role: event.target.value }); setPage(0); }}
              className="field-input"
            >
              <option value="">All roles</option>
              {ROLE_OPTIONS.map((role) => <option key={role} value={role}>{prettyLabel(role)}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="audit-override" className="field-label">Override</label>
            <select
              id="audit-override"
              value={filters.override}
              onChange={(event) => { setFilters({ ...filters, override: event.target.value }); setPage(0); }}
              className="field-input"
            >
              <option value="">All entries</option>
              <option value="true">Overrides only</option>
              <option value="false">Standard actions</option>
            </select>
          </div>
        </div>
      </Card>

      {error ? <ErrorState title="Audit log unavailable" message={error} onRetry={() => void load()} /> : null}
      {loading ? <TableSkeleton rows={8} columns={6} /> : null}

      {!loading && !error && items.length === 0 ? (
        <EmptyState
          title="No audit entries found"
          message="No recorded actions match the current filters."
          icon={<ShieldAlert className="h-5 w-5" aria-hidden="true" />}
        />
      ) : null}

      {!loading && !error && items.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full min-w-[820px] text-left text-sm" aria-label="Audit log entries">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                <th scope="col" className="px-4 py-3">When</th>
                <th scope="col" className="px-4 py-3">Actor</th>
                <th scope="col" className="px-4 py-3">Action</th>
                <th scope="col" className="px-4 py-3">Entity</th>
                <th scope="col" className="px-4 py-3">Override</th>
                <th scope="col" className="px-4 py-3">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((entry) => (
                <tr key={entry.id} className="hover:bg-slate-50/70">
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-600">{formatDateTime(entry.created_at)}</td>
                  <td className="px-4 py-3">
                    <p className="font-medium text-navy-900">{entry.actor_id ?? 'System'}</p>
                    <p className="text-xs text-slate-500">{entry.actor_role ? prettyLabel(entry.actor_role) : '—'}</p>
                  </td>
                  <td className="px-4 py-3 font-medium text-navy-900">{entry.action}</td>
                  <td className="px-4 py-3 text-slate-600">{entry.entity_type} <span className="text-xs text-slate-400">#{entry.entity_id}</span></td>
                  <td className="px-4 py-3">
                    <StatusPill status={entry.is_override ? 'urgent' : 'closed'} label={entry.is_override ? 'Override' : 'Standard'} />
                  </td>
                  <td className="max-w-xs px-4 py-3 text-xs text-slate-600">
                    {entry.details && Object.keys(entry.details).length > 0 ? (
                      <details>
                        <summary className="cursor-pointer font-medium text-teal-700">View details</summary>
                        <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-2 text-[11px] text-slate-700">
                          {JSON.stringify(entry.details, null, 2)}
                        </pre>
                      </details>
                    ) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <Pagination page={page} limit={LIMIT} total={total} onPageChange={setPage} />
    </div>
  );
}

export default function AuditPage() {
  return <RoleGuard roles={['admin']}><AuditWorkspace /></RoleGuard>;
}
