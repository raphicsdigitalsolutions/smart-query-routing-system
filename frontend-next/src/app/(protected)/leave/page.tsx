'use client';

import { useCallback, useEffect, useState } from 'react';
import { CalendarDays, Loader2, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { RoleGuard } from '@/components/auth/RoleGuard';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { PageHeader } from '@/components/common/PageHeader';
import { Skeleton } from '@/components/common/Skeleton';
import { StatusPill } from '@/components/common/StatusPill';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textArea';
import { leaveApi } from '@/lib/api/endpoints';
import { getApiErrorMessage } from '@/lib/api/errors';
import type { LeaveWindow } from '@/lib/api/types';
import { formatDateTime } from '@/lib/utils';

interface LeaveForm {
  start_at: string;
  end_at: string;
  reason: string;
  auto_reply: string;
}

const EMPTY_FORM: LeaveForm = { start_at: '', end_at: '', reason: '', auto_reply: '' };

function LeaveWorkspace() {
  const [items, setItems] = useState<LeaveWindow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<LeaveForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [busyId, setBusyId] = useState<number | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setItems(await leaveApi.list({ limit: 100 }));
    } catch (cause) {
      setError(getApiErrorMessage(cause, 'Unable to load leave windows.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSave() {
    if (!form.start_at || !form.end_at) {
      setFormError('Choose both a start and end date.');
      return;
    }
    if (new Date(form.end_at) <= new Date(form.start_at)) {
      setFormError('The end of the leave window must be after the start.');
      return;
    }
    setSaving(true);
    setFormError('');
    try {
      await leaveApi.create({
        start_at: new Date(form.start_at).toISOString(),
        end_at: new Date(form.end_at).toISOString(),
        reason: form.reason.trim() || null,
        auto_reply: form.auto_reply.trim(),
      });
      toast.success('Leave window created.');
      setDialogOpen(false);
      setForm(EMPTY_FORM);
      await load();
    } catch (cause) {
      setFormError(getApiErrorMessage(cause, 'Unable to create the leave window.'));
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(item: LeaveWindow) {
    setBusyId(item.id);
    try {
      await leaveApi.update(item.id, { is_active: !item.is_active });
      toast.success(item.is_active ? 'Leave window deactivated.' : 'Leave window activated.');
      await load();
    } catch (cause) {
      toast.error(getApiErrorMessage(cause, 'Unable to update the leave window.'));
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete() {
    if (deleteId === null) return;
    setBusyId(deleteId);
    try {
      await leaveApi.remove(deleteId);
      setDeleteId(null);
      toast.success('Leave window deleted.');
      await load();
    } catch (cause) {
      toast.error(getApiErrorMessage(cause, 'Unable to delete the leave window.'));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Workspace tools"
        title="Leave windows"
        description="Record absence periods and the auto-reply shown while you are away."
        icon={<CalendarDays className="h-6 w-6" aria-hidden="true" />}
        actions={<Button variant="teal" onClick={() => { setForm(EMPTY_FORM); setFormError(''); setDialogOpen(true); }}><Plus className="h-4 w-4" aria-hidden="true" /> Add leave window</Button>}
      />

      {error ? <ErrorState title="Leave windows unavailable" message={error} onRetry={() => void load()} /> : null}
      {loading ? (
        <div className="space-y-4"><Skeleton className="h-32" /><Skeleton className="h-32" /></div>
      ) : null}

      {!loading && !error && items.length === 0 ? (
        <EmptyState
          title="No leave windows recorded"
          message="Add a leave window to publish an automatic reply for the period you are away."
          icon={<CalendarDays className="h-5 w-5" aria-hidden="true" />}
        />
      ) : null}

      {!loading && !error && items.length > 0 ? (
        <ul className="space-y-4">
          {items.map((item) => (
            <li key={item.id}>
              <Card className="p-5 sm:p-6">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-navy-900">
                        {formatDateTime(item.start_at)} → {formatDateTime(item.end_at)}
                      </p>
                      <StatusPill status={item.is_active ? 'healthy' : 'closed'} label={item.is_active ? 'Active' : 'Inactive'} />
                    </div>
                    {item.user_name ? <p className="mt-1 text-xs text-slate-500">{item.user_name}</p> : null}
                    {item.reason ? <p className="mt-1 text-xs text-slate-500">Reason: {item.reason}</p> : null}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <Button variant="outline" size="sm" disabled={busyId === item.id} onClick={() => void toggleActive(item)}>
                      {busyId === item.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : null}
                      {item.is_active ? 'Deactivate' : 'Activate'}
                    </Button>
                    <Button variant="ghost" size="sm" className="text-rose-600 hover:bg-rose-50" onClick={() => setDeleteId(item.id)} aria-label="Delete leave window">
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    </Button>
                  </div>
                </div>
                <div className="mt-4 rounded-xl border border-teal-200 bg-teal-50/60 p-4">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-teal-800">Auto-reply text</p>
                  <p className="mt-1.5 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{item.auto_reply}</p>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      ) : null}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add a leave window</DialogTitle>
            <DialogDescription>Students will see your auto-reply while this window is active.</DialogDescription>
          </DialogHeader>

          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              void handleSave();
            }}
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="leave-start" className="field-label">Start</label>
                <input
                  id="leave-start"
                  type="datetime-local"
                  required
                  value={form.start_at}
                  onChange={(event) => setForm({ ...form, start_at: event.target.value })}
                  className="field-input"
                />
              </div>
              <div>
                <label htmlFor="leave-end" className="field-label">End</label>
                <input
                  id="leave-end"
                  type="datetime-local"
                  required
                  value={form.end_at}
                  onChange={(event) => setForm({ ...form, end_at: event.target.value })}
                  className="field-input"
                />
              </div>
            </div>
            <div>
              <label htmlFor="leave-reason" className="field-label">Reason <span className="font-normal text-slate-500">(optional)</span></label>
              <input
                id="leave-reason"
                maxLength={500}
                value={form.reason}
                onChange={(event) => setForm({ ...form, reason: event.target.value })}
                placeholder="e.g. Conference travel"
                className="field-input"
              />
            </div>
            <div>
              <label htmlFor="leave-reply" className="field-label">Auto-reply text</label>
              <Textarea
                id="leave-reply"
                required
                rows={5}
                value={form.auto_reply}
                onChange={(event) => setForm({ ...form, auto_reply: event.target.value })}
                placeholder="Thank you for your message. I am away and will respond when I return…"
              />
            </div>
            {formError ? <ErrorState compact title="Save failed" message={formError} /> : null}
            <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
              <Button variant="outline" onClick={() => setDialogOpen(false)} disabled={saving}>Cancel</Button>
              <Button type="submit" variant="teal" disabled={saving}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                Save leave window
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteId !== null} onOpenChange={(open) => { if (!open) setDeleteId(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this leave window?</DialogTitle>
            <DialogDescription>Its auto-reply will no longer be used. This cannot be undone.</DialogDescription>
          </DialogHeader>
          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button variant="outline" onClick={() => setDeleteId(null)} disabled={busyId !== null}>Cancel</Button>
            <Button variant="danger" onClick={() => void handleDelete()} disabled={busyId !== null}>
              {busyId !== null ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Trash2 className="h-4 w-4" aria-hidden="true" />}
              Delete leave window
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function LeavePage() {
  return <RoleGuard roles={['staff', 'hod', 'admin']}><LeaveWorkspace /></RoleGuard>;
}
