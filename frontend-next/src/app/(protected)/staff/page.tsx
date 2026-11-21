'use client';

import { useState } from 'react';
import { Inbox, UsersRound } from 'lucide-react';
import { RoleGuard } from '@/components/auth/RoleGuard';
import { TicketFilters } from '@/components/tickets/TicketFilters';
import { TicketTable } from '@/components/tickets/TicketTable';
import { Pagination } from '@/components/common/Pagination';
import { ErrorState } from '@/components/common/ErrorState';
import { PageHeader } from '@/components/common/PageHeader';
import { StatCard } from '@/components/common/StatCard';
import { Skeleton, TableSkeleton } from '@/components/common/Skeleton';
import { useTickets } from '@/hooks/useTickets';
import { EMPTY_TICKET_FILTERS, type TicketFilters as TicketFiltersValue } from '@/lib/api/types';

const LIMIT = 10;

function StaffWorkspace() {
  const [filters, setFilters] = useState<TicketFiltersValue>({ ...EMPTY_TICKET_FILTERS });
  const [page, setPage] = useState(0);
  const { items, total, loading, error, refresh } = useTickets({
    ...filters,
    skip: page * LIMIT,
    limit: LIMIT,
  });

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Staff workspace"
        title="Assigned queue"
        description="Work tickets assigned to you or visible in your department."
        icon={<UsersRound className="h-6 w-6" aria-hidden="true" />}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          label="Tickets in view"
          value={error ? '—' : loading ? <Skeleton className="h-8 w-12" /> : total}
          hint="Assigned to you or your department"
          icon={<Inbox className="h-5 w-5" aria-hidden="true" />}
        />
      </div>

      <TicketFilters
        value={filters}
        onChange={(next) => {
          setFilters(next);
          setPage(0);
        }}
      />

      {error ? <ErrorState title="Unable to load your queue" message={error} onRetry={refresh} /> : null}
      {loading ? (
        <TableSkeleton rows={6} columns={6} />
      ) : (
        <TicketTable
          tickets={items}
          emptyTitle="Queue is clear"
          emptyMessage="No tickets are assigned to you right now. An HOD or admin can assign tickets from any ticket's workflow panel."
        />
      )}
      <Pagination page={page} limit={LIMIT} total={total} onPageChange={setPage} />
    </div>
  );
}

export default function StaffPage() {
  return <RoleGuard roles={['staff', 'hod']}><StaffWorkspace /></RoleGuard>;
}
