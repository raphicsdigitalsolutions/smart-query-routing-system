'use client';

import { useCallback, useEffect, useState } from 'react';
import { Building2, Flag, Inbox, ShieldCheck, UsersRound } from 'lucide-react';
import { RoleGuard } from '@/components/auth/RoleGuard';
import { DepartmentManager } from '@/components/admin/DepartmentManager';
import { TicketFilters } from '@/components/tickets/TicketFilters';
import { TicketTable } from '@/components/tickets/TicketTable';
import { Pagination } from '@/components/common/Pagination';
import { ErrorState } from '@/components/common/ErrorState';
import { PageHeader } from '@/components/common/PageHeader';
import { StatCard } from '@/components/common/StatCard';
import { Skeleton, TableSkeleton } from '@/components/common/Skeleton';
import { Card } from '@/components/ui/card';
import { StatusPill } from '@/components/common/StatusPill';
import { useTickets } from '@/hooks/useTickets';
import { departmentsApi, usersApi } from '@/lib/api/endpoints';
import { getApiErrorMessage } from '@/lib/api/errors';
import {
  EMPTY_TICKET_FILTERS,
  type AssignableUserResponse,
  type DepartmentResponse,
  type TicketFilters as TicketFiltersValue,
} from '@/lib/api/types';
import { prettyLabel } from '@/lib/utils';

const LIMIT = 20;

function AdminWorkspace() {
  const [filters, setFilters] = useState<TicketFiltersValue>({ ...EMPTY_TICKET_FILTERS });
  const [page, setPage] = useState(0);
  const [departments, setDepartments] = useState<DepartmentResponse[]>([]);
  const [assignable, setAssignable] = useState<AssignableUserResponse[]>([]);
  const [lookupsLoading, setLookupsLoading] = useState(true);
  const [lookupError, setLookupError] = useState('');
  const { items, total, loading, error, refresh } = useTickets({
    ...filters,
    skip: page * LIMIT,
    limit: LIMIT,
  });

  const loadLookups = useCallback(() => {
    const controller = new AbortController();
    setLookupError('');
    setLookupsLoading(true);
    Promise.all([departmentsApi.list(controller.signal), usersApi.listAssignable(controller.signal)])
      .then(([departmentResult, userResult]) => {
        if (controller.signal.aborted) return;
        setDepartments(departmentResult.items ?? []);
        setAssignable(userResult.items ?? []);
      })
      .catch((cause) => {
        if (controller.signal.aborted) return;
        setLookupError(getApiErrorMessage(cause, 'Unable to load administrative data.'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLookupsLoading(false);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => loadLookups(), [loadLookups]);

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Administration"
        title="Administration"
        description="Tickets, departments and assignment control across the university."
        icon={<ShieldCheck className="h-6 w-6" aria-hidden="true" />}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          label="Tickets in view"
          value={error ? '—' : loading ? <Skeleton className="h-8 w-12" /> : total}
          hint="All departments"
          icon={<Inbox className="h-5 w-5" aria-hidden="true" />}
          tone="navy"
        />
        <StatCard
          label="Escalated on this page"
          value={loading ? <Skeleton className="h-8 w-12" /> : items.filter((ticket) => ticket.is_escalated).length}
          hint="Current page only"
          icon={<Flag className="h-5 w-5" aria-hidden="true" />}
          tone="rose"
        />
        <StatCard
          label="Departments"
          value={lookupsLoading ? <Skeleton className="h-8 w-12" /> : departments.length}
          hint="Active routing destinations"
          icon={<Building2 className="h-5 w-5" aria-hidden="true" />}
        />
      </div>

      {lookupError ? <ErrorState compact title="Administrative data unavailable" message={lookupError} onRetry={loadLookups} /> : null}

      {lookupsLoading ? (
        <div className="surface-card h-64 p-6"><Skeleton className="h-full w-full" /></div>
      ) : (
        <DepartmentManager departments={departments} onChanged={loadLookups} />
      )}

      <Card className="overflow-hidden">
        <div className="flex items-start gap-3 border-b border-slate-100 p-5 sm:p-6">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-700 ring-1 ring-teal-100">
            <UsersRound className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <h3 className="text-base font-semibold text-navy-900">Assignable users</h3>
            <p className="mt-0.5 text-xs text-slate-500">Staff, HOD and admin accounts available for ticket assignment.</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm" aria-label="Assignable users">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                <th scope="col" className="px-5 py-3">Name</th>
                <th scope="col" className="px-5 py-3">Email</th>
                <th scope="col" className="px-5 py-3">Role</th>
                <th scope="col" className="px-5 py-3">Department</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {assignable.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-5 py-10 text-center text-sm text-slate-500">
                    No assignable users found.
                  </td>
                </tr>
              ) : (
                assignable.map((person) => (
                  <tr key={person.id} className="transition-colors hover:bg-slate-50/70">
                    <td className="px-5 py-3 font-medium text-navy-900">{person.full_name}</td>
                    <td className="px-5 py-3 text-slate-600">{person.email}</td>
                    <td className="px-5 py-3"><StatusPill status={person.role} label={prettyLabel(person.role)} /></td>
                    <td className="px-5 py-3 text-slate-600">{person.department_id ? `Dept #${person.department_id}` : '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <p className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
          Assignment is performed from a ticket’s workflow panel. There is no user-creation endpoint in the backend.
        </p>
      </Card>

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-navy-900">Ticket overview</h3>
            <p className="text-xs text-slate-500">All tickets visible to an administrator.</p>
          </div>
          <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-600 ring-1 ring-slate-200">{total} total</span>
        </div>
        <TicketFilters
          value={filters}
          onChange={(next) => {
            setFilters(next);
            setPage(0);
          }}
        />
        {error ? <ErrorState title="Unable to load tickets" message={error} onRetry={refresh} /> : null}
        {loading ? (
          <TableSkeleton rows={7} columns={6} />
        ) : (
          <TicketTable tickets={items} emptyTitle="No tickets" emptyMessage="No tickets match the current filters." />
        )}
        <Pagination page={page} limit={LIMIT} total={total} onPageChange={setPage} />
      </section>
    </div>
  );
}

export default function AdminPage() {
  return <RoleGuard roles={['admin']}><AdminWorkspace /></RoleGuard>;
}
