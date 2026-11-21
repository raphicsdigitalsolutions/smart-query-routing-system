'use client';

import { useState } from 'react';
import { Flag, SlidersHorizontal, UserRoundCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { StatusPill } from '@/components/common/StatusPill';
import { AssignTicketDialog } from './AssignTicketDialog';
import { hasRole } from '@/lib/auth/rbac';
import {
  STAFF_ALLOWED_TRANSITIONS,
  STATUS_TRANSITIONS,
  type AssignableUserResponse,
  type TicketResponse,
  type TicketStatus,
  type UserResponse,
} from '@/lib/api/types';
import { prettyLabel } from '@/lib/utils';

interface TicketWorkflowPanelProps {
  ticket: TicketResponse;
  user: UserResponse;
  assignable: AssignableUserResponse[];
  busy: boolean;
  onAssign: (assigneeId: number | null) => Promise<void>;
  onStatusChange: (status: TicketStatus) => Promise<void>;
  onEscalate: (value: boolean) => Promise<void>;
}

export function TicketWorkflowPanel({
  ticket,
  user,
  assignable,
  busy,
  onAssign,
  onStatusChange,
  onEscalate,
}: TicketWorkflowPanelProps) {
  const [assignmentOpen, setAssignmentOpen] = useState(false);
  const canManage = hasRole(user, ['hod', 'admin']);
  const canChangeStatus =
    canManage || (hasRole(user, ['staff']) && user.id === ticket.assigned_to);
  const targets = STATUS_TRANSITIONS[ticket.status].filter(
    (status) => canManage || STAFF_ALLOWED_TRANSITIONS.includes(status),
  );

  if (!canManage && !canChangeStatus) return null;

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-50 text-teal-700 ring-1 ring-teal-100">
          <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
        </span>
        <h2 className="text-sm font-semibold text-navy-900">Workflow controls</h2>
      </div>

      <div className="space-y-5 p-5">
        <div>
          <p className="field-label">Current status</p>
          <StatusPill status={ticket.status} />
        </div>

        {canChangeStatus ? (
          <div>
            <p className="field-label">Change status</p>
            <Select
              value=""
              disabled={busy || targets.length === 0}
              onValueChange={(value) => void onStatusChange(value as TicketStatus)}
            >
              <SelectTrigger aria-label="Change status">
                <SelectValue placeholder={targets.length ? 'Choose next status…' : 'No transitions available'} />
              </SelectTrigger>
              <SelectContent>
                {targets.map((status) => (
                  <SelectItem key={status} value={status}>{prettyLabel(status)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        ) : null}

        {canManage ? (
          <>
            <div className="border-t border-slate-100 pt-5">
              <p className="field-label">Assignment</p>
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50/60 p-3">
                <div className="flex min-w-0 items-center gap-2 text-sm text-navy-900">
                  <UserRoundCheck className="h-4 w-4 shrink-0 text-teal-700" aria-hidden="true" />
                  <span className="truncate">{ticket.assignee_name ?? 'Unassigned'}</span>
                </div>
                <Button variant="outline" size="sm" disabled={busy} onClick={() => setAssignmentOpen(true)}>
                  Assign / reassign
                </Button>
              </div>
            </div>

            <label className="flex cursor-pointer items-center gap-2.5 rounded-xl border border-slate-200 p-3 text-sm text-navy-900 transition-colors hover:bg-slate-50">
              <input
                type="checkbox"
                checked={ticket.is_escalated}
                disabled={busy}
                onChange={(event) => void onEscalate(event.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-teal-700 focus:ring-teal-500"
              />
              <Flag className="h-4 w-4 text-rose-600" aria-hidden="true" />
              Escalated
            </label>

            <AssignTicketDialog
              open={assignmentOpen}
              ticket={ticket}
              assignable={assignable}
              busy={busy}
              onClose={() => setAssignmentOpen(false)}
              onAssign={onAssign}
            />
          </>
        ) : null}
      </div>
    </Card>
  );
}
