'use client';

import { useState } from 'react';
import { Building2, Flag, Inbox } from 'lucide-react';
import { RoleGuard } from '@/components/auth/RoleGuard';
import { TicketFilters } from '@/components/tickets/TicketFilters';
import { TicketTable } from '@/components/tickets/TicketTable';
import { Pagination } from '@/components/common/Pagination';
import { ErrorState } from '@/components/common/ErrorState';
import { PageHeader } from '@/components/common/PageHeader';
import { StatCard } from '@/components/common/StatCard';
import { Skeleton, TableSkeleton } from '@/components/common/Skeleton';
import { useSession } from '@/hooks/useSession';
import { useTickets } from '@/hooks/useTickets';
import { EMPTY_TICKET_FILTERS, type TicketFilters as TicketFiltersValue } from '@/lib/api/types';

const LIMIT = 20;

function HodWorkspace() {
  const { user } = useSession();
  const [filters, setFilters] = useState<TicketFiltersValue>({ ...EMPTY_TICKET_FILTERS });
  const [page, setPage] = useState(0);
  const { items, total, loading, error, refresh } = useTickets({
    ...filters,
    skip: page * LIMIT,
    limit: LIMIT,
  });
  const escalated = items.filter((ticket) => ticket.is_escalated).length;

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Head of department"
        title="Department overview"
        description={`Department ${user?.department_id ?? '—'} · queue, assignment and escalation review.`}
        icon={<Building2 className="h-6 w-6" aria-hidden="true" />}
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard
          label="Tickets in view"
          value={error ? '—' : loading ? <Skeleton className="h-8 w-12" /> : total}
          hint="Scoped to your department"
          icon={<Inbox className="h-5 w-5" aria-hidden="true" />}
          tone="navy"
        />
        <StatCard
          label="Escalated on this page"
          value={loading ? <Skeleton className="h-8 w-12" /> : escalated}
          hint="Current page only"
          icon={<Flag className="h-5 w-5" aria-hidden="true" />}
          tone="rose"
        />
      </div>

      <TicketFilters
        value={filters}
        onChange={(next) => {
          setFilters(next);
          setPage(0);
        }}
      />

      {error ? <ErrorState title="Unable to load department queue" message={error} onRetry={refresh} /> : null}
      {loading ? (
        <TableSkeleton rows={7} columns={6} />
      ) : (
        <TicketTable
          tickets={items}
          emptyTitle="Department queue is clear"
          emptyMessage="No tickets match the current filters. Open a ticket from another view to assign it here."
        />
      )}
      <Pagination page={page} limit={LIMIT} total={total} onPageChange={setPage} />
      <p className="text-xs text-slate-500">
        Open any ticket to assign or reassign it, change its status, or review escalation.
      </p>
    </div>
  );
}

export default function HodPage() {
  return <RoleGuard roles={['hod']}><HodWorkspace /></RoleGuard>;
}
