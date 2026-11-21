'use client';

import { useEffect, useState } from 'react';
import { ChevronDown, CircleHelp, Loader2, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textArea';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { ErrorState } from '@/components/common/ErrorState';
import { departmentsApi, ticketsApi } from '@/lib/api/endpoints';
import { getApiErrorMessage } from '@/lib/api/errors';
import { TICKET_CHANNELS, TICKET_PRIORITIES, type DepartmentResponse, type TicketChannel, type TicketPriority, type TicketResponse } from '@/lib/api/types';
import { prettyLabel } from '@/lib/utils';

interface CreateTicketFormProps {
  onCreated: (ticket: TicketResponse) => void;
}

export function CreateTicketForm({ onCreated }: CreateTicketFormProps) {
  const [departments, setDepartments] = useState<DepartmentResponse[]>([]);
  const [loadingDepartments, setLoadingDepartments] = useState(true);
  const [departmentError, setDepartmentError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [form, setForm] = useState({
    subject: '',
    description: '',
    department_id: '',
    category: '',
    priority: 'normal' as TicketPriority,
    auto_route: false,
    channel: 'web' as TicketChannel,
  });

  useEffect(() => {
    const controller = new AbortController();
    departmentsApi
      .list(controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        setDepartments(result.items ?? []);
      })
      .catch((error) => {
        if (controller.signal.aborted) return;
        setDepartmentError(getApiErrorMessage(error, 'Unable to load departments.'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingDepartments(false);
      });
    return () => controller.abort();
  }, []);

  function setField<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitError('');
    setSubmitting(true);
    try {
      const ticket = await ticketsApi.create({
        subject: form.subject.trim(),
        description: form.description.trim(),
        department_id: form.department_id ? Number(form.department_id) : null,
        category: form.category.trim() || null,
        priority: form.priority,
        auto_route: form.auto_route,
        channel: form.channel,
      });
      toast.success(`${ticket.public_reference} submitted successfully.`);
      setForm({ subject: '', description: '', department_id: '', category: '', priority: 'normal', auto_route: false, channel: 'web' });
      onCreated(ticket);
    } catch (error) {
      setSubmitError(getApiErrorMessage(error, 'Unable to submit your query.'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="overflow-hidden">
      <div className="flex items-start justify-between gap-4 border-b border-slate-100 p-5 sm:p-6">
        <div>
          <p className="eyebrow text-teal-700">New request</p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-navy-900">Submit a new query</h2>
          <p className="mt-1 text-sm text-slate-500">Tell us what you need and choose the closest department.</p>
        </div>
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Submission help">
              <CircleHelp className="h-5 w-5" aria-hidden="true" />
            </Button>
          </PopoverTrigger>
          <PopoverContent>
            <p className="font-semibold text-navy-900">How routing works</p>
            <p className="mt-1 leading-relaxed">
              Your query is created with a public reference. Staff and HOD users can then assign it to the right person.
            </p>
          </PopoverContent>
        </Popover>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5 p-5 sm:p-6">
        {departmentError ? (
          <ErrorState compact title="Could not load departments" message={departmentError} />
        ) : null}

        <div>
          <label htmlFor="ticket-subject" className="field-label">Subject</label>
          <input
            id="ticket-subject"
            value={form.subject}
            onChange={(event) => setField('subject', event.target.value)}
            minLength={5}
            maxLength={255}
            required
            placeholder="A short, clear summary"
            className="field-input"
          />
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="ticket-department" className="field-label">Department</label>
            <span className="relative block">
              <select
                id="ticket-department"
                value={form.department_id}
                onChange={(event) => setField('department_id', event.target.value)}
                required={!form.auto_route}
                className="field-input appearance-none pr-9"
              >
                <option value="">{loadingDepartments ? 'Loading departments…' : form.auto_route ? 'Let the router choose' : 'Select a department'}</option>
                {departments.map((department) => (
                  <option key={department.id} value={String(department.id)}>{department.name}</option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            </span>
          </div>

          <div>
            <label htmlFor="ticket-priority" className="field-label">Priority</label>
            <span className="relative block">
              <select
                id="ticket-priority"
                value={form.priority}
                onChange={(event) => setField('priority', event.target.value as TicketPriority)}
                className="field-input appearance-none pr-9"
              >
                {TICKET_PRIORITIES.map((priority) => (
                  <option key={priority} value={priority}>{prettyLabel(priority)}</option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            </span>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2.5 text-sm text-navy-900 transition-colors hover:border-teal-300 hover:bg-teal-50/50">
            <input
              id="ticket-auto-route"
              type="checkbox"
              checked={form.auto_route}
              onChange={(event) => setField('auto_route', event.target.checked)}
              className="h-4 w-4 shrink-0 rounded border-slate-300 text-teal-700 focus:ring-teal-500"
              aria-describedby="ticket-auto-route-help"
            />
            <span>
              <span className="block font-semibold">Auto-route this query</span>
              <span id="ticket-auto-route-help" className="block text-xs font-normal text-slate-500">
                Let the routing engine choose a department when none is selected.
              </span>
            </span>
          </label>

          <div>
            <label htmlFor="ticket-channel" className="field-label">Channel</label>
            <span className="relative block">
              <select
                id="ticket-channel"
                value={form.channel}
                onChange={(event) => setField('channel', event.target.value as TicketChannel)}
                className="field-input appearance-none pr-9"
              >
                {TICKET_CHANNELS.map((channel) => (
                  <option key={channel} value={channel}>{prettyLabel(channel)}</option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            </span>
            <p className="mt-1 text-xs text-slate-500">Indicates how this request reached the workspace.</p>
          </div>
        </div>

        <div>
          <label htmlFor="ticket-category" className="field-label">Category <span className="font-normal text-slate-500">(optional)</span></label>
          <input
            id="ticket-category"
            value={form.category}
            onChange={(event) => setField('category', event.target.value)}
            maxLength={80}
            placeholder="e.g. Account access"
            className="field-input"
          />
        </div>

        <div>
          <label htmlFor="ticket-description" className="field-label">Description</label>
          <Textarea
            id="ticket-description"
            value={form.description}
            onChange={(event) => setField('description', event.target.value)}
            minLength={10}
            maxLength={10000}
            required
            rows={5}
            placeholder="Describe your query in as much detail as possible…"
          />
          <p className="mt-1.5 text-xs text-slate-500">Include any relevant dates, references or context.</p>
        </div>

        {submitError ? (
          <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{submitError}</p>
        ) : null}

        <div className="flex flex-col gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-slate-500">
            {departments.length === 0 && !loadingDepartments && !form.auto_route
              ? 'No active departments are configured yet. Contact an administrator.'
              : form.auto_route
                ? 'The routing engine will select a department and record the decision.'
                : 'Your query goes to the selected department queue.'}
          </p>
          <Button type="submit" variant="teal" disabled={submitting || (!form.auto_route && departments.length === 0)} className="shrink-0">
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Plus className="h-4 w-4" aria-hidden="true" />}
            {submitting ? 'Submitting…' : 'Submit query'}
          </Button>
        </div>
      </form>
    </Card>
  );
}
