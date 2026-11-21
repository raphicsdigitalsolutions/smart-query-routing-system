import { useState } from 'react';
import { UsersRound } from 'lucide-react';
import TicketFilters, { EMPTY_FILTERS } from '../../components/tickets/TicketFilters';
import TicketTable from '../../components/tickets/TicketTable';
import ErrorState from '../../components/common/ErrorState';
import useTickets from '../../hooks/useTickets';

export default function StaffDashboardPage() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(0);
  const limit = 10;
  const { items, total, loading, error, refresh } = useTickets({ ...filters, skip: page * limit, limit });

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
          <UsersRound className="h-6 w-6" aria-hidden="true" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-navy-900">Assigned queue</h1>
          <p className="mt-1 text-sm text-slate-600">
            Queries assigned to you. Open a ticket to reply or update its workflow status.
          </p>
        </div>
      </div>

      <TicketFilters value={filters} onChange={(next) => { setFilters(next); setPage(0); }} />
      {error ? (
        <ErrorState title="Could not load your queue" message={error} onRetry={refresh} />
      ) : loading ? (
        <div className="rounded-xl border border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500">
          Loading assigned tickets…
        </div>
      ) : (
        <TicketTable
          tickets={items}
          emptyTitle="Queue is clear"
          emptyMessage="No tickets are assigned to you right now. HOD or admin users can assign tickets here."
        />
      )}
      <p className="text-sm text-slate-500">{total} ticket(s) in view</p>
    </div>
  );
}
