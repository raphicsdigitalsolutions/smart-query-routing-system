'use client';

import { useState } from 'react';
import { CheckCircle2, GraduationCap } from 'lucide-react';
import { RoleGuard } from '@/components/auth/RoleGuard';
import { CreateTicketForm } from '@/components/tickets/CreateTicketForm';
import { TicketFilters } from '@/components/tickets/TicketFilters';
import { TicketTable } from '@/components/tickets/TicketTable';
import { Pagination } from '@/components/common/Pagination';
import { ErrorState } from '@/components/common/ErrorState';
import { PageHeader } from '@/components/common/PageHeader';
import { TableSkeleton } from '@/components/common/Skeleton';
import { useTickets } from '@/hooks/useTickets';
import { EMPTY_TICKET_FILTERS, type TicketFilters as TicketFiltersValue, type TicketResponse } from '@/lib/api/types';

const LIMIT = 10;

function StudentWorkspace() {
  const [filters, setFilters] = useState<TicketFiltersValue>({ ...EMPTY_TICKET_FILTERS });
  const [page, setPage] = useState(0);
  const [notice, setNotice] = useState('');
  const { items, total, loading, error, refresh } = useTickets({
    ...filters,
    skip: page * LIMIT,
    limit: LIMIT,
  });

  function handleCreated(ticket: TicketResponse) {
    setNotice(`${ticket.public_reference} submitted successfully.`);
    setFilters({ ...EMPTY_TICKET_FILTERS });
    setPage(0);
    refresh();
  }

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Student workspace"
        title="My queries"
        description="Submit requests and follow their progress from one place."
        icon={<GraduationCap className="h-6 w-6" aria-hidden="true" />}
      />

      {notice ? (
        <p role="status" className="flex items-center gap-2 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm font-medium text-teal-800">
          <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> {notice}
        </p>
      ) : null}

      <CreateTicketForm onCreated={handleCreated} />

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-navy-900">Submitted tickets</h3>
            <p className="text-xs text-slate-600">Only your own queries are listed.</p>
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

        {error ? <ErrorState title="Unable to load your tickets" message={error} onRetry={refresh} /> : null}
        {loading ? (
          <TableSkeleton rows={5} columns={6} />
        ) : (
          <TicketTable
            tickets={items}
            emptyTitle="No tickets yet"
            emptyMessage="Submit your first query above to get started. Once submitted, it will appear here with a public reference."
          />
        )}
        <Pagination page={page} limit={LIMIT} total={total} onPageChange={setPage} />
      </section>
    </div>
  );
}

export default function StudentPage() {
  return <RoleGuard roles={['student']}><StudentWorkspace /></RoleGuard>;
}
