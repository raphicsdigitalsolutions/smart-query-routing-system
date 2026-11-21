'use client';

import { useCallback, useEffect, useState } from 'react';
import { Loader2, Megaphone, Pencil, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
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
import { announcementsApi, departmentsApi } from '@/lib/api/endpoints';
import { getApiErrorMessage } from '@/lib/api/errors';
import { ROLES, type Announcement, type DepartmentResponse, type Role } from '@/lib/api/types';
import { useSession } from '@/hooks/useSession';
import { formatDateTime, prettyLabel } from '@/lib/utils';

interface AnnouncementForm {
  title: string;
  body: string;
  roles: Role[];
  department_id: string;
}

const EMPTY_FORM: AnnouncementForm = { title: '', body: '', roles: [], department_id: '' };

export default function AnnouncementsPage() {
  const { hasRole } = useSession();
  const isAdmin = hasRole('admin');
  const [items, setItems] = useState<Announcement[]>([]);
  const [departments, setDepartments] = useState<DepartmentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Announcement | null>(null);
  const [form, setForm] = useState<AnnouncementForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [busyId, setBusyId] = useState<number | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setItems(await announcementsApi.list({ limit: 100 }));
    } catch (cause) {
      setError(getApiErrorMessage(cause, 'Unable to load announcements.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    if (isAdmin) {
      departmentsApi.list().then((result) => setDepartments(result.items ?? [])).catch(() => setDepartments([]));
    }
  }, [load, isAdmin]);

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setFormError('');
    setDialogOpen(true);
  }

  function openEdit(item: Announcement) {
    setEditing(item);
    setForm({
      title: item.title,
      body: item.body,
      roles: item.audience_roles_json ?? item.audience_roles ?? [],
      department_id: item.department_id ? String(item.department_id) : '',
    });
    setFormError('');
    setDialogOpen(true);
  }

  function toggleRole(role: Role) {
    setForm((current) => ({
      ...current,
      roles: current.roles.includes(role) ? current.roles.filter((value) => value !== role) : [...current.roles, role],
    }));
  }

  async function handleSave() {
    setSaving(true);
    setFormError('');
    try {
      const payload = {
        title: form.title.trim(),
        body: form.body.trim(),
        audience_roles: form.roles,
        department_id: form.department_id ? Number(form.department_id) : null,
      };
      if (editing) {
        await announcementsApi.update(editing.id, {
          title: payload.title,
          body: payload.body,
          audience_roles: payload.audience_roles,
          department_id: payload.department_id,
        });
        toast.success('Announcement updated.');
      } else {
        await announcementsApi.create(payload);
        toast.success('Announcement published.');
      }
      setDialogOpen(false);
      await load();
    } catch (cause) {
      setFormError(getApiErrorMessage(cause, 'Unable to save the announcement.'));
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(item: Announcement) {
    setBusyId(item.id);
    try {
      await announcementsApi.update(item.id, { is_active: !item.is_active });
      toast.success(item.is_active ? 'Announcement deactivated.' : 'Announcement reactivated.');
      await load();
    } catch (cause) {
      toast.error(getApiErrorMessage(cause, 'Unable to update the announcement.'));
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete() {
    if (deleteId === null) return;
    setBusyId(deleteId);
    try {
      await announcementsApi.remove(deleteId);
      setDeleteId(null);
      toast.success('Announcement deleted.');
      await load();
    } catch (cause) {
      toast.error(getApiErrorMessage(cause, 'Unable to delete the announcement.'));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Workspace tools"
        title="Announcements"
        description="University broadcasts visible to your role and department."
        icon={<Megaphone className="h-6 w-6" aria-hidden="true" />}
        actions={isAdmin ? <Button variant="teal" onClick={openCreate}><Plus className="h-4 w-4" aria-hidden="true" /> New announcement</Button> : null}
      />

      {error ? <ErrorState title="Announcements unavailable" message={error} onRetry={() => void load()} /> : null}
      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      ) : null}

      {!loading && !error && items.length === 0 ? (
        <EmptyState
          title="No announcements yet"
          message="Published announcements for your role will appear here."
          icon={<Megaphone className="h-5 w-5" aria-hidden="true" />}
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
                      <h2 className="text-base font-semibold tracking-tight text-navy-900">{item.title}</h2>
                      <StatusPill status={item.is_active ? 'healthy' : 'closed'} label={item.is_active ? 'Active' : 'Inactive'} />
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      {formatDateTime(item.published_at ?? item.created_at)}
                      {(item.audience_roles_json ?? item.audience_roles ?? []).length > 0
                        ? ` · ${(item.audience_roles_json ?? item.audience_roles ?? []).map(prettyLabel).join(', ')}`
                        : ' · All roles'}
                    </p>
                  </div>
                  {isAdmin ? (
                    <div className="flex flex-wrap gap-1.5">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(item)}><Pencil className="h-3.5 w-3.5" aria-hidden="true" /> Edit</Button>
                      <Button variant="outline" size="sm" disabled={busyId === item.id} onClick={() => void toggleActive(item)}>
                        {busyId === item.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : null}
                        {item.is_active ? 'Deactivate' : 'Activate'}
                      </Button>
                      <Button variant="ghost" size="sm" className="text-rose-600 hover:bg-rose-50" onClick={() => setDeleteId(item.id)} aria-label={`Delete ${item.title}`}>
                        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                      </Button>
                    </div>
                  ) : null}
                </div>
                <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{item.body}</p>
              </Card>
            </li>
          ))}
        </ul>
      ) : null}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit announcement' : 'New announcement'}</DialogTitle>
            <DialogDescription>Choose who should see this broadcast before publishing.</DialogDescription>
          </DialogHeader>

          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              void handleSave();
            }}
          >
            <div>
              <label htmlFor="announcement-title" className="field-label">Title</label>
              <input
                id="announcement-title"
                required
                maxLength={255}
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
                className="field-input"
              />
            </div>
            <div>
              <label htmlFor="announcement-body" className="field-label">Message</label>
              <Textarea
                id="announcement-body"
                required
                rows={6}
                value={form.body}
                onChange={(event) => setForm({ ...form, body: event.target.value })}
              />
            </div>
            <fieldset>
              <legend className="field-label">Audience roles</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {ROLES.map((role) => (
                  <label key={role} className="flex min-h-11 cursor-pointer items-center gap-2.5 rounded-lg border border-slate-200 bg-slate-50/60 px-3 text-sm text-navy-900">
                    <input
                      type="checkbox"
                      checked={form.roles.includes(role)}
                      onChange={() => toggleRole(role)}
                      className="h-4 w-4 rounded border-slate-300 text-teal-700 focus:ring-teal-500"
                    />
                    {prettyLabel(role)}
                  </label>
                ))}
              </div>
              <p className="mt-1.5 text-xs text-slate-500">Leave all unchecked to target every role.</p>
            </fieldset>
            <div>
              <label htmlFor="announcement-department" className="field-label">Department <span className="font-normal text-slate-500">(optional)</span></label>
              <select
                id="announcement-department"
                value={form.department_id}
                onChange={(event) => setForm({ ...form, department_id: event.target.value })}
                className="field-input"
              >
                <option value="">All departments</option>
                {departments.map((department) => (
                  <option key={department.id} value={String(department.id)}>{department.name}</option>
                ))}
              </select>
            </div>
            {formError ? <ErrorState compact title="Save failed" message={formError} /> : null}
            <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
              <Button variant="outline" onClick={() => setDialogOpen(false)} disabled={saving}>Cancel</Button>
              <Button type="submit" variant="teal" disabled={saving || !form.title.trim() || !form.body.trim()}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                {editing ? 'Save changes' : 'Publish announcement'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteId !== null} onOpenChange={(open) => { if (!open) setDeleteId(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this announcement?</DialogTitle>
            <DialogDescription>It will no longer be visible to its audience. This cannot be undone.</DialogDescription>
          </DialogHeader>
          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button variant="outline" onClick={() => setDeleteId(null)} disabled={busyId !== null}>Cancel</Button>
            <Button variant="danger" onClick={() => void handleDelete()} disabled={busyId !== null}>
              {busyId !== null ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Trash2 className="h-4 w-4" aria-hidden="true" />}
              Delete announcement
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
