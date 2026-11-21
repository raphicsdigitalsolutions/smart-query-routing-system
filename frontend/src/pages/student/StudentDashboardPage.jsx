import { useState } from 'react';
import { GraduationCap } from 'lucide-react';
import CreateTicketForm from '../../components/tickets/CreateTicketForm';
import TicketFilters, { EMPTY_FILTERS } from '../../components/tickets/TicketFilters';
import TicketTable from '../../components/tickets/TicketTable';
import ErrorState from '../../components/common/ErrorState';
import useTickets from '../../hooks/useTickets';

export default function StudentDashboardPage() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(0);
  const [notice, setNotice] = useState('');
  const limit = 10;
  const { items, total, loading, error, refresh } = useTickets({ ...filters, skip: page * limit, limit });

  function handleCreated(ticket) {
    setNotice(`${ticket.public_reference} submitted successfully.`);
    setFilters({ ...EMPTY_FILTERS });
    setPage(0);
    refresh();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
          <GraduationCap className="h-6 w-6" aria-hidden="true" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-navy-900">My queries</h1>
          <p className="mt-1 text-sm text-slate-600">Submit a query and follow every reply from university staff.</p>
        </div>
      </div>

      {notice && (
        <div className="rounded-lg border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-800" role="status">
          {notice}
        </div>
      )}

      <CreateTicketForm onCreated={handleCreated} />

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-navy-900">Submitted tickets</h2>
          <span className="text-sm text-slate-500">{total} total</span>
        </div>
        <TicketFilters value={filters} onChange={(next) => { setFilters(next); setPage(0); }} />
        {error ? (
          <ErrorState title="Could not load tickets" message={error} onRetry={refresh} />
        ) : loading ? (
          <div className="rounded-xl border border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500">
            Loading your tickets…
          </div>
        ) : (
          <TicketTable
            tickets={items}
            emptyTitle="No queries yet"
            emptyMessage="Submit your first query using the form above."
          />
        )}
        {total > limit && (
          <div className="flex items-center justify-end gap-3 text-sm">
            <button
              type="button"
              disabled={page === 0}
              onClick={() => setPage((value) => Math.max(0, value - 1))}
              className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-slate-500">Page {page + 1} of {Math.ceil(total / limit)}</span>
            <button
              type="button"
              disabled={(page + 1) * limit >= total}
              onClick={() => setPage((value) => value + 1)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
