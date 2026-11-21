import { useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import TicketFilters, { EMPTY_FILTERS } from '../../components/tickets/TicketFilters';
import TicketTable from '../../components/tickets/TicketTable';
import ErrorState from '../../components/common/ErrorState';
import useTickets from '../../hooks/useTickets';

export default function AdminDashboardPage() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(0);
  const limit = 20;
  const { items, total, loading, error, refresh } = useTickets({ ...filters, skip: page * limit, limit });

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
          <ShieldCheck className="h-6 w-6" aria-hidden="true" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-navy-900">Ticket overview</h1>
          <p className="mt-1 text-sm text-slate-600">
            All tickets across departments, with assignment and administrative controls on each detail page.
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-600">Tickets in view</p>
          <p className="mt-3 text-3xl font-semibold text-navy-900">{loading ? '—' : total}</p>
          <p className="mt-2 text-xs text-slate-500">Live count from the database (respects filters above)</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-600">Escalated in view</p>
          <p className="mt-3 text-3xl font-semibold text-navy-900">
            {loading ? '—' : items.filter((ticket) => ticket.is_escalated).length}
          </p>
          <p className="mt-2 text-xs text-slate-500">On the current page only</p>
        </div>
      </div>

      <TicketFilters value={filters} onChange={(next) => { setFilters(next); setPage(0); }} />
      {error ? (
        <ErrorState title="Could not load tickets" message={error} onRetry={refresh} />
      ) : loading ? (
        <div className="rounded-xl border border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500">
          Loading tickets…
        </div>
      ) : (
        <TicketTable
          tickets={items}
          emptyTitle="No tickets"
          emptyMessage="No tickets exist in the database yet."
        />
      )}
      {total > limit && (
        <div className="flex items-center justify-end gap-3 text-sm">
          <button
            type="button"
            disabled={page === 0}
            onClick={() => setPage((value) => Math.max(0, value - 1))}
            className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-50"
          >Previous</button>
          <span className="text-slate-500">Page {page + 1} of {Math.ceil(total / limit)}</span>
          <button
            type="button"
            disabled={(page + 1) * limit >= total}
            onClick={() => setPage((value) => value + 1)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-50"
          >Next</button>
        </div>
      )}
    </div>
  );
}
