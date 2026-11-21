import { useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import { createTicket, getApiErrorMessage, listDepartments } from '../../services/api';
import ErrorState from '../common/ErrorState';

export default function CreateTicketForm({ onCreated }) {
  const [departments, setDepartments] = useState([]);
  const [loadError, setLoadError] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    subject: '',
    description: '',
    department_id: '',
    category: '',
    priority: 'normal',
  });

  useEffect(() => {
    let active = true;
    listDepartments()
      .then((data) => { if (active) setDepartments(data.items || []); })
      .catch((err) => { if (active) setLoadError(getApiErrorMessage(err)); });
    return () => { active = false; };
  }, []);

  const update = (field) => (event) => setForm((prev) => ({ ...prev, [field]: event.target.value }));

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const ticket = await createTicket({
        subject: form.subject.trim(),
        description: form.description.trim(),
        department_id: Number(form.department_id),
        category: form.category.trim() || null,
        priority: form.priority,
      });
      setForm({ subject: '', description: '', department_id: '', category: '', priority: 'normal' });
      onCreated?.(ticket);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (loadError) return <ErrorState title="Could not load departments" message={loadError} />;

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
          <Plus className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-navy-900">Submit a new query</h2>
          <p className="text-xs text-slate-500">Route your question to the right university department.</p>
        </div>
      </div>

      {error && <p role="alert" className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p>}

      <form className="mt-5 grid gap-4 sm:grid-cols-2" onSubmit={handleSubmit}>
        <div className="sm:col-span-2">
          <label htmlFor="ticket-subject" className="block text-sm font-medium text-navy-800">Subject</label>
          <input
            id="ticket-subject"
            required
            minLength={5}
            maxLength={255}
            value={form.subject}
            onChange={update('subject')}
            placeholder="e.g. Transcript request"
            className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-600"
          />
        </div>
        <div>
          <label htmlFor="ticket-department" className="block text-sm font-medium text-navy-800">Department</label>
          <select
            id="ticket-department"
            required
            value={form.department_id}
            onChange={update('department_id')}
            className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-600"
          >
            <option value="">Select a department</option>
            {departments.map((department) => (
              <option key={department.id} value={department.id}>{department.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="ticket-priority" className="block text-sm font-medium text-navy-800">Priority</label>
          <select
            id="ticket-priority"
            value={form.priority}
            onChange={update('priority')}
            className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-600"
          >
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="ticket-category" className="block text-sm font-medium text-navy-800">Category (optional)</label>
          <input
            id="ticket-category"
            maxLength={80}
            value={form.category}
            onChange={update('category')}
            placeholder="e.g. Records, Fees, Scholarships"
            className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-600"
          />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="ticket-description" className="block text-sm font-medium text-navy-800">Description</label>
          <textarea
            id="ticket-description"
            required
            minLength={10}
            maxLength={10000}
            rows={4}
            value={form.description}
            onChange={update('description')}
            placeholder="Describe your query and any relevant details."
            className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-600"
          />
        </div>
        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={submitting || departments.length === 0}
            className="rounded-lg bg-navy-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? 'Submitting…' : 'Submit query'}
          </button>
          {departments.length === 0 && !loadError && (
            <span className="ml-3 text-xs text-slate-500">No active departments are configured yet.</span>
          )}
        </div>
      </form>
    </section>
  );
}
