'use client';

import { useState } from 'react';
import { Building2, Loader2, Pencil, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { StatusPill } from '@/components/common/StatusPill';
import { departmentsApi } from '@/lib/api/endpoints';
import { getApiErrorMessage } from '@/lib/api/errors';
import type { DepartmentResponse } from '@/lib/api/types';

interface DepartmentManagerProps {
  departments: DepartmentResponse[];
  onChanged: () => void;
}

export function DepartmentManager({ departments, onChanged }: DepartmentManagerProps) {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<DepartmentResponse | null>(null);
  const [form, setForm] = useState({ name: '', description: '', is_active: true });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  function openCreate() {
    setEditing(null);
    setForm({ name: '', description: '', is_active: true });
    setError('');
    setOpen(true);
  }

  function openEdit(department: DepartmentResponse) {
    setEditing(department);
    setForm({
      name: department.name,
      description: department.description ?? '',
      is_active: department.is_active,
    });
    setError('');
    setOpen(true);
  }

  async function handleSave() {
    setBusy(true);
    setError('');
    try {
      if (editing) {
        await departmentsApi.update(editing.id, {
          name: form.name.trim(),
          description: form.description.trim() || null,
          is_active: form.is_active,
        });
        toast.success('Department updated.');
      } else {
        await departmentsApi.create({
          name: form.name.trim(),
          description: form.description.trim() || null,
        });
        toast.success('Department created.');
      }
      setOpen(false);
      onChanged();
    } catch (cause) {
      setError(getApiErrorMessage(cause, 'Unable to save department.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-5 sm:p-6">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-700 ring-1 ring-teal-100">
            <Building2 className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-base font-semibold text-navy-900">Department management</h2>
            <p className="text-xs text-slate-500">Create and maintain routing destinations.</p>
          </div>
        </div>
        <Button variant="teal" size="sm" onClick={openCreate}>
          <Plus className="h-4 w-4" aria-hidden="true" /> New department
        </Button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[600px] text-left text-sm" aria-label="Departments">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-bold uppercase tracking-wider text-slate-500">
              <th scope="col" className="px-5 py-3">Name</th>
              <th scope="col" className="px-5 py-3">Description</th>
              <th scope="col" className="px-5 py-3">Status</th>
              <th scope="col" className="px-5 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {departments.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-5 py-10 text-center text-sm text-slate-500">
                  No departments configured yet.
                </td>
              </tr>
            ) : (
              departments.map((department) => (
                <tr key={department.id} className="transition-colors hover:bg-slate-50/80">
                  <td className="px-5 py-3.5 font-medium text-navy-900">{department.name}</td>
                  <td className="max-w-sm px-5 py-3.5 text-slate-600">{department.description ?? '—'}</td>
                  <td className="px-5 py-3.5">
                    <StatusPill
                      status={department.is_active ? 'healthy' : 'closed'}
                      label={department.is_active ? 'Active' : 'Inactive'}
                    />
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(department)}>
                      <Pencil className="h-3.5 w-3.5" aria-hidden="true" /> Edit
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Dialog open={open} onOpenChange={(next) => { if (!next) setOpen(false); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit department' : 'Create department'}</DialogTitle>
            <DialogDescription>
              {editing ? 'Update the details of this routing destination.' : 'Add a new routing destination for student queries.'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <label htmlFor="department-name" className="field-label">Name</label>
              <input
                id="department-name"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                minLength={2}
                maxLength={120}
                required
                className="field-input"
              />
            </div>
            <div>
              <label htmlFor="department-description" className="field-label">Description <span className="font-normal text-slate-500">(optional)</span></label>
              <textarea
                id="department-description"
                value={form.description}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
                maxLength={2000}
                rows={3}
                className="field-input h-auto min-h-[84px] resize-y py-2.5"
              />
            </div>
            {editing ? (
              <label className="flex cursor-pointer items-center gap-2.5 rounded-lg border border-slate-200 bg-slate-50/60 px-3 py-2.5 text-sm text-navy-900">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
                  className="h-4 w-4 rounded border-slate-300 text-teal-700 focus:ring-teal-500"
                />
                Active routing destination
              </label>
            ) : null}
            {error ? <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</p> : null}
          </div>

          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button variant="teal" disabled={busy || !form.name.trim()} onClick={() => void handleSave()}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
              {busy ? 'Saving…' : 'Save department'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
