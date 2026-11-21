import { Link } from 'react-router-dom';
import {
  ArrowUpRight,
  GraduationCap,
  Inbox,
  ShieldCheck,
  UsersRound,
} from 'lucide-react';
import StatCard from '../../components/dashboard/StatCard';
import BackendStatusCard from '../../components/dashboard/BackendStatusCard';
import EmptyState from '../../components/common/EmptyState';
import { useAuth } from '../../context/AuthContext';
import useTickets from '../../hooks/useTickets';

const QUICK_LINKS = [
  {
    to: '/student',
    roles: ['student'],
    title: 'Student workspace',
    description: 'Submit queries and track replies.',
    icon: GraduationCap,
  },
  {
    to: '/staff',
    roles: ['staff', 'hod', 'admin'],
    title: 'Staff workspace',
    description: 'Triage and respond to assigned queries.',
    icon: UsersRound,
  },
  {
    to: '/admin',
    roles: ['admin'],
    title: 'Admin overview',
    description: 'Review all tickets across departments.',
    icon: ShieldCheck,
  },
];

export default function DashboardPage() {
  const { user, hasRole } = useAuth();
  const { total, loading, error, refresh } = useTickets({ limit: 1 });
  const links = QUICK_LINKS.filter((link) => hasRole(...link.roles));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-navy-900 sm:text-3xl">
          Welcome{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          University Intelligent Communication Hub — authenticated query routing and staff
          collaboration.
        </p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2" aria-label="Ticket metrics">
        <StatCard
          icon={Inbox}
          label="Tickets in your view"
          value={loading ? '—' : error ? '—' : total}
          hint="Live count from the database, scoped to your role"
        />
        <StatCard
          icon={ShieldCheck}
          label="Your role"
          value={user?.role?.toUpperCase() || '—'}
          hint="Permissions are enforced by the backend"
        />
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <BackendStatusCard />
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-navy-900">Getting started</h3>
          {error ? (
            <p className="mt-4 text-sm text-rose-600">Ticket data unavailable: {error}</p>
          ) : links.length > 0 ? (
            <div className="mt-4 space-y-3">
              {links.map((link) => (
                <Link
                  key={link.to}
                  to={link.to}
                  className="flex items-start gap-3 rounded-lg border border-slate-100 bg-slate-50 p-3 transition-colors hover:border-teal-500"
                >
                  <link.icon className="mt-0.5 h-5 w-5 shrink-0 text-teal-700" aria-hidden="true" />
                  <span>
                    <span className="block text-sm font-semibold text-navy-900">{link.title}</span>
                    <span className="mt-0.5 block text-xs text-slate-500">{link.description}</span>
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <div className="mt-4">
              <EmptyState
                title="No workspace for this role"
                message="Contact an administrator if you expected access to a workspace."
              />
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
