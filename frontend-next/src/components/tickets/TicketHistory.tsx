import { ArrowRight, Clock3, Flag, History, UserRoundCheck } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { StatusPill } from '@/components/common/StatusPill';
import type { TicketHistoryResponse } from '@/lib/api/types';
import { formatDateTime } from '@/lib/utils';

interface TicketHistoryProps {
  history: TicketHistoryResponse | null;
}

export function TicketHistory({ history }: TicketHistoryProps) {
  const statusChanges = history?.status_changes ?? [];
  const assignments = history?.assignments ?? [];
  const escalations = history?.escalations ?? [];

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-2.5">
        <History className="h-5 w-5 text-teal-700" aria-hidden="true" />
        <div>
          <h2 className="text-sm font-semibold text-navy-900">Recorded history</h2>
          <p className="text-xs text-slate-600">Status transitions, assignment changes, and escalation activity.</p>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="overflow-hidden">
          <div className="flex items-center gap-2 border-b border-slate-100 px-5 py-3.5">
            <Clock3 className="h-4 w-4 text-slate-400" aria-hidden="true" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Status changes</h3>
          </div>
          <div className="p-5">
            {statusChanges.length === 0 ? (
              <p className="text-sm text-slate-500">No status changes recorded for this ticket.</p>
            ) : (
              <ol className="space-y-3">
                {statusChanges.map((item) => (
                  <li key={item.id} className="rounded-lg border border-slate-200 bg-slate-50/50 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      {item.from_status ? <StatusPill status={item.from_status} /> : <span className="text-xs text-slate-500">Created</span>}
                      <ArrowRight className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
                      <StatusPill status={item.to_status} />
                    </div>
                    <p className="mt-2 text-[11px] text-slate-500">
                      {formatDateTime(item.created_at)}
                      {item.changed_by_name ? ` · ${item.changed_by_name}` : ''}
                      {item.note ? ` · ${item.note}` : ''}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </Card>

        <Card className="overflow-hidden">
          <div className="flex items-center gap-2 border-b border-slate-100 px-5 py-3.5">
            <UserRoundCheck className="h-4 w-4 text-slate-400" aria-hidden="true" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Assignments</h3>
          </div>
          <div className="p-5">
            {assignments.length === 0 ? (
              <p className="text-sm text-slate-500">No assignments recorded for this ticket.</p>
            ) : (
              <ol className="space-y-3">
                {assignments.map((item) => {
                  const fromLabel =
                    item.from_assignee_name ?? (item.from_assignee_id ? `User #${item.from_assignee_id}` : 'Unassigned');
                  const toLabel =
                    item.to_assignee_name ?? (item.to_assignee_id ? `User #${item.to_assignee_id}` : 'Unassigned');
                  return (
                    <li key={item.id} className="rounded-lg border border-slate-200 bg-slate-50/50 p-3">
                      <p className="flex flex-wrap items-center gap-2 text-sm text-navy-900">
                        <span>{fromLabel}</span>
                        <ArrowRight className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
                        <span className="font-medium">{toLabel}</span>
                      </p>
                      <p className="mt-1 text-[11px] text-slate-500">
                        {formatDateTime(item.created_at)}
                        {item.changed_by_name ? ` · ${item.changed_by_name}` : ''}
                      </p>
                    </li>
                  );
                })}
              </ol>
            )}
          </div>
        </Card>

        <Card className="overflow-hidden">
          <div className="flex items-center gap-2 border-b border-slate-100 px-5 py-3.5">
            <Flag className="h-4 w-4 text-rose-600" aria-hidden="true" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Escalations</h3>
          </div>
          <div className="p-5">
            {escalations.length === 0 ? (
              <p className="text-sm text-slate-500">No escalation events recorded for this ticket.</p>
            ) : (
              <ol className="space-y-3">
                {escalations.map((item) => (
                  <li key={item.id} className="rounded-lg border border-slate-200 bg-slate-50/50 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusPill
                        status={item.from_escalated ? 'urgent' : 'closed'}
                        label={item.from_escalated ? 'Escalated' : 'Not escalated'}
                      />
                      <ArrowRight className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
                      <StatusPill
                        status={item.to_escalated ? 'urgent' : 'closed'}
                        label={item.to_escalated ? 'Escalated' : 'Not escalated'}
                      />
                    </div>
                    <p className="mt-2 text-[11px] text-slate-500">
                      {formatDateTime(item.created_at)}
                      {item.actor_name ? ` · ${item.actor_name}` : ''}
                      {item.actor_role ? ` (${item.actor_role.toUpperCase()})` : ''}
                      {item.note ? ` · ${item.note}` : ''}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </Card>
      </div>
    </section>
  );
}
