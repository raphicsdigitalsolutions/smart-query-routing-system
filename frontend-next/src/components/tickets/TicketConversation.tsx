'use client';

import { useState } from 'react';
import { LockKeyhole, MessageSquare, Send, StickyNote } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textArea';
import { EmptyState } from '@/components/common/EmptyState';
import type { MessageResponse } from '@/lib/api/types';
import { formatDateTime, initials } from '@/lib/utils';
import { cn } from '@/lib/utils';

interface TicketConversationProps {
  messages: MessageResponse[];
  canReply: boolean;
  canWriteInternal: boolean;
  isClosed: boolean;
  busy: boolean;
  onSend: (body: string, isInternal: boolean) => Promise<void>;
}

export function TicketConversation({
  messages,
  canReply,
  canWriteInternal,
  isClosed,
  busy,
  onSend,
}: TicketConversationProps) {
  const [draft, setDraft] = useState('');
  const [isInternal, setIsInternal] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!draft.trim()) return;
    setError('');
    const body = draft.trim();
    const internal = isInternal && canWriteInternal;
    try {
      await onSend(body, internal);
      setDraft('');
      setIsInternal(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to send your message.');
    }
  }

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-4 sm:px-6">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-50 text-teal-700 ring-1 ring-teal-100">
            <MessageSquare className="h-4 w-4" aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-navy-900">Conversation</h2>
            <p className="text-xs text-slate-500">{messages.length} {messages.length === 1 ? 'message' : 'messages'}</p>
          </div>
        </div>
        {canWriteInternal ? (
          <span className="hidden items-center gap-1.5 text-[11px] font-medium text-amber-700 sm:flex">
            <StickyNote className="h-3.5 w-3.5" aria-hidden="true" /> Internal notes visible to staff
          </span>
        ) : null}
      </div>

      <div className="p-5 sm:p-6">
        {messages.length === 0 ? (
          <EmptyState
            title="No messages yet"
            message="Start the conversation with a public reply. Students will see public replies on this ticket."
          />
        ) : (
          <ol className="space-y-4">
            {messages.map((message) => {
              const internal = message.is_internal;
              return (
                <li
                  key={message.id}
                  className={cn(
                    'rounded-xl border p-4',
                    internal ? 'border-amber-200 bg-amber-50/70' : 'border-slate-200 bg-white',
                  )}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <span
                        className={cn(
                          'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[11px] font-semibold',
                          internal ? 'bg-amber-100 text-amber-800' : 'bg-navy-50 text-navy-700',
                        )}
                        aria-hidden="true"
                      >
                        {initials(message.sender_name)}
                      </span>
                      <div className="min-w-0">
                        <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-navy-900">
                          {message.sender_name}
                          {internal ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800">
                              <LockKeyhole className="h-3 w-3" aria-hidden="true" /> Internal note
                            </span>
                          ) : null}
                        </p>
                        <time className="text-[11px] text-slate-500" dateTime={message.created_at}>
                          {formatDateTime(message.created_at)}
                        </time>
                      </div>
                    </div>
                  </div>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{message.message_body}</p>
                </li>
              );
            })}
          </ol>
        )}

        {canReply && !isClosed ? (
          <form onSubmit={handleSubmit} className="mt-6 space-y-3 border-t border-slate-100 pt-6">
            <label htmlFor="reply-body" className="field-label">
              {canWriteInternal ? 'Add a reply or internal note' : 'Reply to this ticket'}
            </label>
            <Textarea
              id="reply-body"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Write a clear, helpful response…"
              rows={4}
              required
            />
            {canWriteInternal ? (
              <label className="flex cursor-pointer items-center gap-2.5 rounded-lg border border-slate-200 bg-slate-50/60 px-3 py-2.5 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={isInternal}
                  onChange={(event) => setIsInternal(event.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-teal-700 focus:ring-teal-500"
                />
                <StickyNote className="h-4 w-4 text-amber-600" aria-hidden="true" />
                Internal note — visible to staff only
              </label>
            ) : null}
            {error ? <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</p> : null}
            <div className="flex justify-end">
              <Button type="submit" variant="teal" disabled={busy || !draft.trim()}>
                <Send className="h-4 w-4" aria-hidden="true" />
                {busy ? 'Sending…' : isInternal && canWriteInternal ? 'Add note' : 'Send reply'}
              </Button>
            </div>
          </form>
        ) : null}

        {isClosed ? (
          <p className="mt-6 flex items-center gap-2 rounded-xl bg-slate-100 px-4 py-3 text-sm text-slate-600">
            <LockKeyhole className="h-4 w-4" aria-hidden="true" /> This ticket is closed. New replies are disabled.
          </p>
        ) : null}
      </div>
    </Card>
  );
}
