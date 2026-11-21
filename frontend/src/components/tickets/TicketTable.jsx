import { Link } from 'react-router-dom';
import { ArrowUpRight, Flag } from 'lucide-react';
import StatusPill from '../common/StatusPill';
import EmptyState from '../common/EmptyState';
import { formatDate } from '../../utils/format';

export default function TicketTable({ tickets = [], emptyTitle, emptyMessage }) {
  if (tickets.length === 0) {
    return <EmptyState title={emptyTitle} message={emptyMessage} />;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-3">Reference</th>
            <th className="px-4 py-3">Subject</th>
            <th className="px-4 py-3">Department</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Priority</th>
            <th className="px-4 py-3">Created</th>
            <th className="px-4 py-3"><span className="sr-only">Open</span></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {tickets.map((ticket) => (
            <tr key={ticket.id} className="hover:bg-slate-50">
              <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-navy-700">
                {ticket.public_reference}
              </td>
              <td className="px-4 py-3">
                <p className="font-medium text-navy-900">{ticket.subject}</p>
                <p className="mt-0.5 text-xs text-slate-500">{ticket.student_name || `Student #${ticket.student_id}`}</p>
              </td>
              <td className="px-4 py-3 text-slate-600">{ticket.department_name || `Dept #${ticket.department_id}`}</td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <StatusPill status={ticket.status} />
                  {ticket.is_escalated && (
                    <span title="Escalated"><Flag className="h-3.5 w-3.5 text-rose-500" aria-label="Escalated" /></span>
                  )}
                </div>
              </td>
              <td className="px-4 py-3"><StatusPill status={ticket.priority} label={ticket.priority} /></td>
              <td className="whitespace-nowrap px-4 py-3 text-slate-500">{formatDate(ticket.created_at)}</td>
              <td className="px-4 py-3 text-right">
                <Link
                  to={`/tickets/${ticket.id}`}
                  className="inline-flex items-center gap-1 text-sm font-semibold text-teal-700 hover:text-teal-600"
                  aria-label={`Open ${ticket.public_reference}`}
                >
                  Open <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
