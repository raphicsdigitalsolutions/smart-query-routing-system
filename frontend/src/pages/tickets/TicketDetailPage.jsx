import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, MessageSquare, Send, StickyNote } from 'lucide-react';
import StatusPill from '../../components/common/StatusPill';
import ErrorState from '../../components/common/ErrorState';
import EmptyState from '../../components/common/EmptyState';
import { useAuth } from '../../context/AuthContext';
import {
  assignTicket,
  getApiErrorMessage,
  getTicket,
  getTicketHistory,
  listAssignableUsers,
  listMessages,
  patchTicket,
  postMessage,
} from '../../services/api';
import { formatDate } from '../../utils/format';

const TRANSITIONS = {
  new: ['assigned', 'in_progress', 'closed'],
  assigned: ['in_progress', 'waiting_for_student', 'resolved', 'new'],
  in_progress: ['waiting_for_student', 'resolved', 'assigned'],
  waiting_for_student: ['in_progress', 'resolved', 'closed'],
  resolved: ['closed', 'in_progress'],
  closed: [],
};
const STAFF_TARGETS = ['in_progress', 'waiting_for_student', 'resolved', 'closed'];

export default function TicketDetailPage() {
  const { ticketId } = useParams();
  const { user, hasRole } = useAuth();
  const [ticket, setTicket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [history, setHistory] = useState({ status_changes: [], assignments: [] });
  const [assignable, setAssignable] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const [draft, setDraft] = useState('');
  const [isInternal, setIsInternal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [assigneeId, setAssigneeId] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [ticketData, messageData, historyData] = await Promise.all([
        getTicket(ticketId),
        listMessages(ticketId),
        getTicketHistory(ticketId),
      ]);
      setTicket(ticketData);
      setMessages(messageData.items || []);
      setHistory(historyData);
      setAssigneeId(ticketData.assigned_to ? String(ticketData.assigned_to) : '');
      if (hasRole('hod', 'admin')) {
        const users = await listAssignableUsers();
        setAssignable(users.items || []);
      }
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to load this ticket.'));
    } finally {
      setLoading(false);
    }
  }, [ticketId, hasRole]);

  useEffect(() => { load(); }, [load]);

  async function runAction(action, successMessage) {
    setBusy(true);
    setActionError('');
    setNotice('');
    try {
      const result = await action();
      if (result?.ticket) setTicket(result.ticket);
      if (successMessage) setNotice(successMessage);
      await load();
    } catch (err) {
      setActionError(getApiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleReply(event) {
    event.preventDefault();
    if (!draft.trim()) return;
    await runAction(
      () => postMessage(ticketId, { message_body: draft.trim(), is_internal: isInternal && !hasRole('student') }),
      isInternal ? 'Internal note added.' : 'Reply sent.',
    );
    setDraft('');
    setIsInternal(false);
  }

  const canManage = hasRole('hod', 'admin');
  const canChangeStatus = hasRole('hod', 'admin') || (hasRole('staff') && user?.id === ticket?.assigned_to);
  const targets = (TRANSITIONS[ticket?.status] || []).filter(
    (target) => !hasRole('staff') || STAFF_TARGETS.includes(target),
  );

  if (loading) {
    return <div className="rounded-xl border border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500">Loading ticket…</div>;
  }
  if (error) return <ErrorState title="Ticket unavailable" message={error} onRetry={load} />;
  if (!ticket) return null;

  return (
    <div className="space-y-6">
      <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-sm font-medium text-navy-700 hover:text-teal-700">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to overview
      </Link>

      {notice && <p role="status" className="rounded-lg border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-800">{notice}</p>}
      {actionError && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{actionError}</p>}

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-mono text-xs text-teal-700">{ticket.public_reference}</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-navy-900">{ticket.subject}</h1>
            <p className="mt-2 max-w-3xl whitespace-pre-wrap text-sm text-slate-600">{ticket.description}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusPill status={ticket.status} />
            <StatusPill status={ticket.priority} label={`Priority: ${ticket.priority}`} />
            {ticket.is_escalated && <StatusPill status="urgent" label="Escalated" />}
          </div>
        </div>
        <dl className="mt-6 grid gap-4 border-t border-slate-100 pt-5 text-sm sm:grid-cols-3">
          <div><dt className="text-xs uppercase tracking-wide text-slate-500">Student</dt><dd className="mt-1 font-medium text-navy-900">{ticket.student_name || `#${ticket.student_id}`}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-slate-500">Department</dt><dd className="mt-1 font-medium text-navy-900">{ticket.department_name || `#${ticket.department_id}`}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-slate-500">Assigned to</dt><dd className="mt-1 font-medium text-navy-900">{ticket.assignee_name || 'Unassigned'}</dd></div>
        </dl>
      </section>

      {(canManage || canChangeStatus) && (
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Workflow controls</h2>
          <div className="mt-4 flex flex-wrap items-end gap-4">
            {canManage && (
              <div className="min-w-[220px]">
                <label htmlFor="assign-select" className="block text-xs font-semibold text-slate-600">Assignment</label>
                <div className="mt-1 flex gap-2">
                  <select
                    id="assign-select"
                    value={assigneeId}
                    onChange={(event) => setAssigneeId(event.target.value)}
                    className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  >
                    <option value="">Unassigned</option>
                    {assignable.map((candidate) => (
                      <option key={candidate.id} value={candidate.id}>{candidate.full_name} ({candidate.role})</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => runAction(
                      () => assignTicket(ticketId, assigneeId ? Number(assigneeId) : null),
                      'Assignment updated.',
                    )}
                    className="rounded-lg bg-navy-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
                  >Save</button>
                </div>
              </div>
            )}
            {canManage && (
              <label className="flex items-center gap-2 text-sm text-navy-800">
                <input
                  type="checkbox"
                  checked={ticket.is_escalated}
                  disabled={busy}
                  onChange={(event) => runAction(
                    () => patchTicket(ticketId, { is_escalated: event.target.checked }),
                    'Escalation flag updated.',
                  )}
                  className="h-4 w-4 rounded border-slate-300 text-teal-700"
                />
                Escalated
              </label>
            )}
            {canChangeStatus && targets.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-slate-600">Change status</p>
                <div className="mt-1 flex flex-wrap gap-2">
                  {targets.map((target) => (
                    <button
                      key={target}
                      type="button"
                      disabled={busy}
                      onClick={() => runAction(
                        () => patchTicket(ticketId, { status: target }),
                        `Status changed to ${target.replaceAll('_', ' ')}.`,
                      )}
                      className="rounded-lg border border-teal-600 px-3 py-1.5 text-xs font-semibold text-teal-700 hover:bg-teal-50 disabled:opacity-60"
                    >
                      {target.replaceAll('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <h2 className="flex items-center gap-2 text-base font-semibold text-navy-900">
          <MessageSquare className="h-5 w-5 text-teal-700" aria-hidden="true" /> Conversation
        </h2>
        {messages.length === 0 ? (
          <div className="mt-4">
            <EmptyState title="No messages yet" message="Start the conversation using the form below." />
          </div>
        ) : (
          <div className="mt-5 space-y-4">
            {messages.map((message) => (
              <article
                key={message.id}
                className={`rounded-lg border p-4 ${message.is_internal ? 'border-amber-200 bg-amber-50' : 'border-slate-200 bg-slate-50'}`}
              >
                <div className="flex items-center justify-between gap-4">
                  <p className="text-sm font-semibold text-navy-900">{message.sender_name || `User #${message.sender_id}`}</p>
                  <p className="text-xs text-slate-500">{formatDate(message.created_at)}</p>
                </div>
                {message.is_internal && (
                  <p className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-amber-700">
                    <StickyNote className="h-3.5 w-3.5" aria-hidden="true" /> Internal note — staff only
                  </p>
                )}
                <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{message.message_body}</p>
              </article>
            ))}
          </div>
        )}

        {ticket.status !== 'closed' && (
          <form className="mt-6 border-t border-slate-100 pt-5" onSubmit={handleReply}>
            <label htmlFor="reply-body" className="block text-sm font-medium text-navy-800">Write a reply</label>
            <textarea
              id="reply-body"
              rows={3}
              required
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Type your message…"
              className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-600"
            />
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
              {!hasRole('student') && (
                <label className="flex items-center gap-2 text-sm text-navy-800">
                  <input
                    type="checkbox"
                    checked={isInternal}
                    onChange={(event) => setIsInternal(event.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-amber-600"
                  />
                  Internal note (hidden from students)
                </label>
              )}
              <button
                type="submit"
                disabled={busy || !draft.trim()}
                className="inline-flex items-center gap-2 rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-60"
              >
                <Send className="h-4 w-4" aria-hidden="true" /> {isInternal ? 'Add note' : 'Send reply'}
              </button>
            </div>
          </form>
        )}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Activity history</h2>
        <div className="mt-4 grid gap-6 md:grid-cols-2">
          <div>
            <h3 className="text-xs font-semibold text-navy-800">Status changes</h3>
            {history.status_changes.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">No status changes recorded.</p>
            ) : (
              <ul className="mt-2 space-y-2 text-sm text-slate-600">
                {history.status_changes.map((row) => (
                  <li key={row.id} className="rounded-lg bg-slate-50 px-3 py-2">
                    {row.from_status || '—'} → {row.to_status} · {formatDate(row.created_at)}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <h3 className="text-xs font-semibold text-navy-800">Assignments</h3>
            {history.assignments.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">No assignments recorded.</p>
            ) : (
              <ul className="mt-2 space-y-2 text-sm text-slate-600">
                {history.assignments.map((row) => (
                  <li key={row.id} className="rounded-lg bg-slate-50 px-3 py-2">
                    {row.from_assignee_id || 'Unassigned'} → {row.to_assignee_id || 'Unassigned'} · {formatDate(row.created_at)}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
