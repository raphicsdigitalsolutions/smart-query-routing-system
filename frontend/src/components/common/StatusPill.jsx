const STYLES = {
  healthy: 'bg-teal-50 text-teal-700 ring-teal-100',
  online: 'bg-teal-50 text-teal-700 ring-teal-100',
  checking: 'bg-amber-50 text-amber-700 ring-amber-100',
  offline: 'bg-rose-50 text-rose-700 ring-rose-100',
  planned: 'bg-slate-100 text-slate-600 ring-slate-200',
  new: 'bg-sky-50 text-sky-700 ring-sky-100',
  assigned: 'bg-indigo-50 text-indigo-700 ring-indigo-100',
  in_progress: 'bg-teal-50 text-teal-700 ring-teal-100',
  waiting_for_student: 'bg-amber-50 text-amber-700 ring-amber-100',
  resolved: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
  closed: 'bg-slate-100 text-slate-600 ring-slate-200',
  urgent: 'bg-rose-50 text-rose-700 ring-rose-100',
  high: 'bg-amber-50 text-amber-700 ring-amber-100',
  normal: 'bg-teal-50 text-teal-700 ring-teal-100',
  low: 'bg-slate-100 text-slate-600 ring-slate-200',
};

const LABELS = {
  healthy: 'Healthy',
  online: 'Online',
  checking: 'Checking',
  offline: 'Offline',
  planned: 'Planned',
  new: 'New',
  assigned: 'Assigned',
  in_progress: 'In progress',
  waiting_for_student: 'Waiting for student',
  resolved: 'Resolved',
  closed: 'Closed',
};

export default function StatusPill({ status = 'planned', label }) {
  const key = STYLES[status] ? status : 'planned';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${STYLES[key]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      {label || LABELS[key] || status}
    </span>
  );
}
