'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, CalendarClock, CheckCircle2, Flag } from 'lucide-react';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { StatusPill } from '@/components/common/StatusPill';
import { ErrorState } from '@/components/common/ErrorState';
import { DetailSkeleton } from '@/components/common/Skeleton';
import { TicketAttachments } from './TicketAttachments';
import { TicketConversation } from './TicketConversation';
import { TicketHistory } from './TicketHistory';
import { TicketWorkflowPanel } from './TicketWorkflowPanel';
import { AiAssistPanel } from './AiAssistPanel';
import { useSession } from '@/hooks/useSession';
import { ticketsApi, usersApi } from '@/lib/api/endpoints';
import { getApiErrorMessage } from '@/lib/api/errors';
import { hasRole } from '@/lib/auth/rbac';
import type {
  AssignableUserResponse,
  AttachmentCreateInput,
  AttachmentResponse,
  MessageResponse,
  MutationResponse,
  TicketHistoryResponse,
  TicketResponse,
  TicketStatus,
} from '@/lib/api/types';
import { formatDateTime } from '@/lib/utils';

interface TicketDetailProps {
  ticketId: string;
}

export function TicketDetail({ ticketId }: TicketDetailProps) {
  const { user } = useSession();
  const [ticket, setTicket] = useState<TicketResponse | null>(null);
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [attachments, setAttachments] = useState<AttachmentResponse[]>([]);
  const [history, setHistory] = useState<TicketHistoryResponse | null>(null);
  const [assignable, setAssignable] = useState<AssignableUserResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  const canManage = Boolean(user && hasRole(user, ['hod', 'admin']));
  const canWriteInternal = Boolean(user && hasRole(user, ['staff', 'hod', 'admin']));

  const load = useCallback(
    async (signal?: AbortSignal) => {
      const [ticketResult, messageResult, attachmentResult, historyResult, assignableResult] = await Promise.all([
        ticketsApi.get(ticketId, signal),
        ticketsApi.listMessages(ticketId, signal),
        ticketsApi.listAttachments(ticketId, signal),
        ticketsApi.history(ticketId, signal),
        canManage ? usersApi.listAssignable(signal) : Promise.resolve(null),
      ]);
      if (signal?.aborted) return;
      setTicket(ticketResult);
      setMessages(messageResult.items ?? []);
      setAttachments(attachmentResult.items ?? []);
      setHistory(historyResult);
      setAssignable(assignableResult?.items ?? []);
    },
    [ticketId, canManage],
  );

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setLoadError('');
    load(controller.signal)
      .catch((cause) => {
        if (controller.signal.aborted) return;
        setLoadError(getApiErrorMessage(cause, 'Unable to load this ticket.'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [load]);

  async function runAction(action: () => Promise<MutationResponse>, successMessage: string) {
    setBusy(true);
    setActionError('');
    setNotice('');
    try {
      const result = await action();
      if (result?.ticket) setTicket(result.ticket);
      setNotice(successMessage);
      toast.success(successMessage);
      await load().catch(() => undefined);
    } catch (cause) {
      const message = getApiErrorMessage(cause, 'Unable to update this ticket.');
      setActionError(message);
      toast.error(message);
    } finally {
      setBusy(false);
    }
  }

  async function handleSend(body: string, isInternal: boolean) {
    await ticketsApi.postMessage(ticketId, { message_body: body, is_internal: isInternal });
    toast.success(isInternal ? 'Internal note added.' : 'Reply sent.');
    await load().catch(() => undefined);
  }

  async function handleUpload(input: AttachmentCreateInput) {
    await ticketsApi.uploadAttachment(ticketId, input);
    toast.success(input.is_internal ? 'Internal attachment uploaded.' : 'Attachment uploaded.');
    await load().catch(() => undefined);
  }

  const backLink = (
    <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-medium text-teal-700 transition-colors hover:text-teal-800 hover:underline">
      <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to overview
    </Link>
  );

  if (loading) {
    return (
      <div className="space-y-6">
        {backLink}
        <DetailSkeleton />
      </div>
    );
  }

  if (loadError || !ticket || !user) {
    return (
      <div className="space-y-4">
        {backLink}
        <ErrorState title="Ticket unavailable" message={loadError || 'This ticket could not be loaded.'} />
      </div>
    );
  }

  const canChangeStatus =
    canManage || (hasRole(user, ['staff']) && user.id === ticket.assigned_to);

  return (
    <div className="space-y-6">
      {backLink}

      {notice ? (
        <p role="status" className="flex items-center gap-2 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm font-medium text-teal-800">
          <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> {notice}
        </p>
      ) : null}
      {actionError ? (
        <div className="rounded-xl">
          <ErrorState compact title="Action failed" message={actionError} />
        </div>
      ) : null}

      <Card className="overflow-hidden">
        <div className="border-b border-slate-100 bg-slate-50/50 px-5 py-4 sm:px-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="font-mono text-xs font-medium text-slate-500">{ticket.public_reference}</p>
            {ticket.is_escalated ? <StatusPill status="urgent" label="Escalated" /> : null}
          </div>
          <h2 className="mt-2 text-xl font-semibold tracking-tight text-navy-900 sm:text-2xl">{ticket.subject}</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            <StatusPill status={ticket.status} />
            <StatusPill status={ticket.priority} label={`Priority: ${ticket.priority}`} />
            {ticket.category ? <StatusPill status="planned" label={ticket.category} /> : null}
          </div>
        </div>

        <div className="p-5 sm:p-6">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{ticket.description}</p>

          <dl className="mt-6 grid gap-4 border-t border-slate-100 pt-5 sm:grid-cols-3">
            <div>
              <dt className="eyebrow">Student</dt>
              <dd className="mt-1.5 text-sm font-medium text-navy-900">{ticket.student_name}</dd>
            </div>
            <div>
              <dt className="eyebrow">Department</dt>
              <dd className="mt-1.5 text-sm font-medium text-navy-900">{ticket.department_name}</dd>
            </div>
            <div>
              <dt className="eyebrow">Assigned to</dt>
              <dd className="mt-1.5 flex items-center gap-1.5 text-sm font-medium text-navy-900">
                {ticket.assignee_name ?? 'Unassigned'}
                {ticket.is_escalated ? <Flag className="h-3.5 w-3.5 text-rose-600" aria-hidden="true" /> : null}
              </dd>
            </div>
          </dl>

          <p className="mt-5 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
            <CalendarClock className="h-3.5 w-3.5" aria-hidden="true" />
            Submitted {formatDateTime(ticket.created_at)} · Updated {formatDateTime(ticket.updated_at)}
          </p>
        </div>
      </Card>

      {canWriteInternal ? (
        <AiAssistPanel
          ticket={ticket}
          canUseAi={canWriteInternal}
          onApproved={() => load()}
        />
      ) : null}

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-6">
          <TicketConversation
            messages={messages}
            canReply={ticket.status !== 'closed'}
            canWriteInternal={canWriteInternal}
            isClosed={ticket.status === 'closed'}
            busy={busy}
            onSend={handleSend}
          />
          <TicketAttachments
            attachments={attachments}
            canUpload={ticket.status !== 'closed'}
            canWriteInternal={canWriteInternal}
            busy={busy}
            onUpload={handleUpload}
          />
        </div>
        {canManage || canChangeStatus ? (
          <TicketWorkflowPanel
            ticket={ticket}
            user={user}
            assignable={assignable}
            busy={busy}
            onAssign={(assigneeId) =>
              runAction(
                () => ticketsApi.assign(ticketId, assigneeId),
                assigneeId ? 'Assignment updated' : 'Ticket unassigned',
              )
            }
            onStatusChange={(status: TicketStatus) =>
              runAction(
                () => ticketsApi.update(ticketId, { status }),
                `Status changed to ${status.replaceAll('_', ' ')}`,
              )
            }
            onEscalate={(value) =>
              runAction(
                () => ticketsApi.update(ticketId, { is_escalated: value }),
                value ? 'Ticket escalated' : 'Escalation removed',
              )
            }
          />
        ) : null}
      </div>

      <TicketHistory history={history} />
    </div>
  );
}
