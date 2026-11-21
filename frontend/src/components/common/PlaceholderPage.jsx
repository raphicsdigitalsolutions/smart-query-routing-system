import { Check, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import StatusPill from './StatusPill';

export default function PlaceholderPage({
  title,
  description,
  phase,
  features = [],
  icon: Icon,
}) {
  return (
    <div className="space-y-6">
      <Link
        to="/dashboard"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-navy-700 hover:text-teal-700"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to overview
      </Link>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
              {Icon && <Icon className="h-6 w-6" aria-hidden="true" />}
            </div>
            <div>
              <h1 className="text-2xl font-semibold tracking-tight text-navy-900">{title}</h1>
              <p className="mt-1 max-w-2xl text-sm text-slate-600">{description}</p>
            </div>
          </div>
          <StatusPill status="planned" label={phase} />
        </div>

        <div className="mt-8 border-t border-slate-100 pt-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Planned capabilities
          </h2>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {features.map((feature) => (
              <li
                key={feature}
                className="flex items-start gap-2.5 rounded-lg border border-slate-100 bg-slate-50 px-4 py-3 text-sm text-navy-800"
              >
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-teal-600" aria-hidden="true" />
                {feature}
              </li>
            ))}
          </ul>
        </div>

        <p className="mt-6 text-sm text-slate-500">
          This is an initial shell. Functionality will be added in the corresponding roadmap phase.
        </p>
      </section>
    </div>
  );
}
