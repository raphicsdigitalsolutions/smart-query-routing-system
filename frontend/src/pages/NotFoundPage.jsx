import { Compass } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-6 py-16 text-center shadow-sm">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-navy-50 text-navy-800">
        <Compass className="h-6 w-6" aria-hidden="true" />
      </div>
      <p className="mt-5 text-3xl font-semibold text-navy-900">404</p>
      <h1 className="mt-1 text-lg font-semibold text-navy-900">Page not found</h1>
      <p className="mt-2 text-sm text-slate-500">
        The page you requested does not exist in this application.
      </p>
      <Link
        to="/dashboard"
        className="mt-6 inline-flex rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800"
      >
        Go to overview
      </Link>
    </div>
  );
}
