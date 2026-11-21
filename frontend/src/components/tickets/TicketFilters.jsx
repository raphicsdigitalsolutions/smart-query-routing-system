import { Search } from 'lucide-react';

const EMPTY = { status: '', priority: '', escalated: '', search: '' };

export default function TicketFilters({ value, onChange }) {
  const update = (field) => (event) => onChange({ ...value, [field]: event.target.value });
  const active = Object.values(value).some(Boolean);

  return (
    <form
      className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
      onSubmit={(event) => event.preventDefault()}
    >
      <div className="min-w-[180px] flex-1">
        <label htmlFor="filter-search" className="block text-xs font-semibold text-slate-600">Search</label>
        <div className="relative mt-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
          <input
            id="filter-search"
            type="search"
            value={value.search}
            onChange={update('search')}
            placeholder="Subject or description"
            className="w-full rounded-lg border border-slate-300 py-2 pl-9 pr-3 text-sm outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-600"
          />
        </div>
      </div>
      <div>
        <label htmlFor="filter-status" className="block text-xs font-semibold text-slate-600">Status</label>
        <select id="filter-status" value={value.status} onChange={update('status')} className="mt-1 rounded-lg border border-slate-300 px-3 py-2 text-sm">
          <option value="">All</option>
          <option value="new">New</option>
          <option value="assigned">Assigned</option>
          <option value="in_progress">In progress</option>
          <option value="waiting_for_student">Waiting for student</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
      </div>
      <div>
        <label htmlFor="filter-priority" className="block text-xs font-semibold text-slate-600">Priority</label>
        <select id="filter-priority" value={value.priority} onChange={update('priority')} className="mt-1 rounded-lg border border-slate-300 px-3 py-2 text-sm">
          <option value="">All</option>
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
      </div>
      <div>
        <label htmlFor="filter-escalated" className="block text-xs font-semibold text-slate-600">Escalated</label>
        <select id="filter-escalated" value={value.escalated} onChange={update('escalated')} className="mt-1 rounded-lg border border-slate-300 px-3 py-2 text-sm">
          <option value="">All</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      </div>
      {active && (
        <button type="button" onClick={() => onChange({ ...EMPTY })} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">
          Clear
        </button>
      )}
    </form>
  );
}

export { EMPTY as EMPTY_FILTERS };
