'use client';

import Link from 'next/link';
import { ArrowUpRight, GraduationCap, Layers3, ShieldCheck, TicketCheck, UsersRound } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { StatCard } from '@/components/common/StatCard';
import { BackendStatusCard } from '@/components/common/BackendStatusCard';
import { StatusPill } from '@/components/common/StatusPill';
import { Skeleton } from '@/components/common/Skeleton';
import { useSession } from '@/hooks/useSession';
import { useTickets } from '@/hooks/useTickets';
import type { Role } from '@/lib/api/types';
import { formatDate, prettyLabel } from '@/lib/utils';

const QUICK_LINKS: Array<{ label: string; description: string; href: string; roles: Role[]; icon: React.ReactNode }> = [
  {
    label: 'Submit a query',
    description: 'Create a new student ticket.',
    href: '/student',
    roles: ['student'],
    icon: <GraduationCap className="h-5 w-5" aria-hidden="true" />,
  },
  {
    label: 'Assigned queue',
    description: 'Work tickets assigned to you.',
    href: '/staff',
    roles: ['staff', 'hod'],
    icon: <UsersRound className="h-5 w-5" aria-hidden="true" />,
  },
  {
    label: 'Department overview',
    description: 'Review escalations and assignments.',
    href: '/hod',
    roles: ['hod'],
    icon: <Layers3 className="h-5 w-5" aria-hidden="true" />,
  },
  {
    label: 'Administration',
    description: 'Tickets, departments and assignment control.',
    href: '/admin',
    roles: ['admin'],
    icon: <ShieldCheck className="h-5 w-5" aria-hidden="true" />,
  },
];

export default function DashboardPage() {
  const { user } = useSession();
  const { items, total, loading, error, refresh } = useTickets({ limit: 5 });
  const links = QUICK_LINKS.filter((link) => user && link.roles.includes(user.role));

  return (
    <div className="space-y-7">
      <div className="relative overflow-hidden rounded-2xl border border-navy-800 bg-navy-900 px-6 py-7 text-white shadow-sm sm:px-8 sm:py-9">
        <div className="pointer-events-none absolute -right-16 -top-24 h-64 w-64 rounded-full bg-teal-500/10 blur-2xl" aria-hidden="true" />
        <div className="relative z-10 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="eyebrow text-teal-200">University communication hub</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
              Welcome{user?.full_name ? `, ${user.full_name.split(/\s+/)[0]}` : ''}
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-300">
              A single place to submit, route and resolve university queries — with role-based access and a complete audit trail.
            </p>
          </div>
          {links[0] ? (
            <Link
              href={links[0].href}
              className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-lg bg-teal-600 px-4 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-teal-500"
            >
              {links[0].label} <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          ) : null}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard
          label="Tickets in your view"
          value={error ? '—' : loading ? <Skeleton className="h-8 w-12" /> : total}
          hint="Scoped by the backend to your role and department"
          icon={<TicketCheck className="h-5 w-5" aria-hidden="true" />}
          tone="navy"
        />
        <StatCard
          label="Your role"
          value={user ? prettyLabel(user.role) : '—'}
          hint="Permissions enforced by FastAPI"
          icon={<ShieldCheck className="h-5 w-5" aria-hidden="true" />}
        />
      </div>

      {error ? <ErrorState compact title="Ticket data unavailable" message={error} onRetry={refresh} /> : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5 sm:p-6">
          <h3 className="text-sm font-semibold text-navy-900">Getting started</h3>
          <p className="mt-1 text-xs text-slate-500">Shortcuts available for your role.</p>
          <div className="mt-4 space-y-2.5">
            {links.length === 0 ? (
              <EmptyState title="No workspace for this role" message="Contact an administrator if you need access." />
            ) : (
              links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="group flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3.5 transition-all hover:border-teal-200 hover:bg-teal-50/50 hover:shadow-sm"
                >
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-teal-50 text-teal-700 ring-1 ring-teal-100">
                    {link.icon}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold text-navy-900">{link.label}</span>
                    <span className="block truncate text-xs text-slate-500">{link.description}</span>
                  </span>
                  <ArrowUpRight className="h-4 w-4 shrink-0 text-slate-300 transition-colors group-hover:text-teal-600" aria-hidden="true" />
                </Link>
              ))
            )}
          </div>
        </Card>

        <div className="space-y-6">
          <BackendStatusCard />

          <Card className="p-5 sm:p-6">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-navy-900">Recent tickets</h3>
                <p className="mt-1 text-xs text-slate-500">The latest records visible to you.</p>
              </div>
              <Link href={links[0]?.href ?? '/dashboard'} className="text-xs font-semibold text-teal-700 hover:underline">
                View all
              </Link>
            </div>
            <div className="mt-4">
              {loading ? (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, index) => (
                    <div key={index} className="flex items-center gap-3 rounded-lg border border-slate-100 p-3">
                      <Skeleton className="h-4 w-20" />
                      <Skeleton className="h-4 flex-1" />
                      <Skeleton className="h-5 w-16" />
                    </div>
                  ))}
                </div>
              ) : items.length === 0 ? (
                <EmptyState
                  title="No tickets yet"
                  message="Tickets will appear here once a query is submitted in a view you can access."
                  className="border-0 bg-transparent px-2 py-8"
                />
              ) : (
                <ul className="divide-y divide-slate-100">
                  {items.map((ticket) => (
                    <li key={ticket.id}>
                      <Link
                        href={`/tickets/${ticket.id}`}
                        className="group flex items-center gap-3 rounded-lg px-2 py-3 transition-colors hover:bg-slate-50"
                      >
                        <span className="w-24 shrink-0 font-mono text-[11px] text-slate-500">{ticket.public_reference}</span>
                        <span className="min-w-0 flex-1 truncate text-sm font-medium text-navy-800 group-hover:text-teal-700">{ticket.subject}</span>
                        <StatusPill status={ticket.status} />
                        <span className="hidden w-20 shrink-0 text-right text-[11px] text-slate-500 sm:block">{formatDate(ticket.created_at)}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
