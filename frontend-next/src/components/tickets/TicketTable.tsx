'use client';

import Link from 'next/link';
import { ArrowUpRight, Flag } from 'lucide-react';
import { EmptyState } from '@/components/common/EmptyState';
import { StatusPill } from '@/components/common/StatusPill';
import type { TicketResponse } from '@/lib/api/types';
import { formatDate } from '@/lib/utils';

interface TicketTableProps {
  tickets: TicketResponse[];
  emptyTitle?: string;
  emptyMessage?: string;
}

export function TicketTable({
  tickets,
  emptyTitle = 'No tickets found',
  emptyMessage = 'Try adjusting the filters or submit a new query.',
}: TicketTableProps) {
  if (tickets.length === 0) return <EmptyState title={emptyTitle} message={emptyMessage} />;

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[860px] text-left text-sm" aria-label="Tickets">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/80 text-[11px] font-bold uppercase tracking-wider text-slate-500">
              <th scope="col" className="px-4 py-3">Reference</th>
              <th scope="col" className="px-4 py-3">Subject</th>
              <th scope="col" className="px-4 py-3">Department</th>
              <th scope="col" className="px-4 py-3">Status</th>
              <th scope="col" className="px-4 py-3">Priority</th>
              <th scope="col" className="px-4 py-3">Created</th>
              <th scope="col" className="px-4 py-3 text-right">Open</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {tickets.map((ticket) => (
              <tr key={ticket.id} className="group transition-colors hover:bg-slate-50/80">
                <td className="whitespace-nowrap px-4 py-3.5 font-mono text-xs text-slate-600">{ticket.public_reference}</td>
                <td className="max-w-xs px-4 py-3.5">
                  <p className="truncate font-medium text-navy-900">{ticket.subject}</p>
                  <p className="mt-0.5 truncate text-xs text-slate-500">{ticket.student_name}</p>
                </td>
                <td className="whitespace-nowrap px-4 py-3.5 text-slate-600">{ticket.department_name}</td>
                <td className="px-4 py-3.5">
                  <div className="flex items-center gap-2">
                    <StatusPill status={ticket.status} />
                    {ticket.is_escalated ? (
                      <span title="Escalated" aria-label="Escalated">
                        <Flag className="h-3.5 w-3.5 text-rose-600" aria-hidden="true" />
                      </span>
                    ) : null}
                  </div>
                </td>
                <td className="px-4 py-3.5"><StatusPill status={ticket.priority} /></td>
                <td className="whitespace-nowrap px-4 py-3.5 text-xs text-slate-500">{formatDate(ticket.created_at)}</td>
                <td className="px-4 py-3.5 text-right">
                  <Link
                    href={`/tickets/${ticket.id}`}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-teal-700 transition-colors hover:bg-teal-50"
                    aria-label={`Open ${ticket.public_reference}`}
                  >
                    <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="border-t border-slate-100 bg-white px-4 py-2.5 text-[11px] text-slate-500 sm:hidden">
        Scroll horizontally to see all columns.
      </p>
    </div>
  );
}
