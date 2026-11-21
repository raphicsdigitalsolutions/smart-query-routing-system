'use client';

import { useEffect, useState } from 'react';
import { ChevronDown, Loader2, UserRoundCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { AssignableUserResponse, TicketResponse } from '@/lib/api/types';

interface AssignTicketDialogProps {
  open: boolean;
  ticket: TicketResponse;
  assignable: AssignableUserResponse[];
  busy: boolean;
  onClose: () => void;
  onAssign: (assigneeId: number | null) => Promise<void>;
}

export function AssignTicketDialog({ open, ticket, assignable, busy, onClose, onAssign }: AssignTicketDialogProps) {
  const [assignee, setAssignee] = useState<string>(ticket.assigned_to ? String(ticket.assigned_to) : '');

  useEffect(() => {
    setAssignee(ticket.assigned_to ? String(ticket.assigned_to) : '');
  }, [ticket.assigned_to, ticket.id]);

  async function handleAssign() {
    await onAssign(assignee ? Number(assignee) : null);
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next) onClose(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign ticket</DialogTitle>
          <DialogDescription className="break-words font-mono text-xs text-slate-500">
            {ticket.public_reference} · {ticket.subject}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <label htmlFor="assignee" className="field-label flex items-center gap-2">
            <UserRoundCheck className="h-4 w-4 text-teal-700" aria-hidden="true" /> Assignee
          </label>
          <span className="relative block">
            <select
              id="assignee"
              value={assignee}
              onChange={(event) => setAssignee(event.target.value)}
              className="field-input appearance-none pr-9"
            >
              <option value="">Unassigned</option>
              {assignable.map((person) => (
                <option key={person.id} value={String(person.id)}>
                  {person.full_name} · {person.role}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
          </span>
        </div>

        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="teal" disabled={busy} onClick={() => void handleAssign()}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
            {busy ? 'Saving…' : 'Save assignment'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
