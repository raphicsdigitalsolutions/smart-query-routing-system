import type { ReactNode } from 'react';
import { Route, ShieldCheck, Sparkles, Workflow } from 'lucide-react';
import { BrandMark } from '@/components/common/BrandMark';

interface AuthShellProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}

const HIGHLIGHTS = [
  {
    icon: Route,
    title: 'Purposeful routing',
    description: 'Every query reaches the correct department and staff queue.',
  },
  {
    icon: ShieldCheck,
    title: 'Role-based access',
    description: 'Students, staff, HODs and admins see only what they should.',
  },
  {
    icon: Sparkles,
    title: 'Grounded AI assistance',
    description: 'Staff-only recommendations that stay unpublished until approved.',
  },
  {
    icon: Workflow,
    title: 'Auditable workflow',
    description: 'Every assignment and status change is recorded and reviewable.',
  },
];

export function AuthShell({ title, subtitle, children, footer }: AuthShellProps) {
  return (
    <main className="min-h-screen bg-canvas">
      <div className="mx-auto grid min-h-screen w-full max-w-[1440px] lg:grid-cols-[minmax(0,1fr)_minmax(0,520px)]">
        <section className="auth-backdrop relative hidden flex-col justify-between p-10 text-white lg:flex xl:p-14">
          <div className="relative z-10">
            <BrandMark inverted size={44} showWordmark />
          </div>

          <div className="relative z-10 max-w-xl">
            <p className="eyebrow text-teal-200">University communication hub</p>
            <h2 className="mt-4 text-3xl font-semibold leading-[1.15] tracking-tight xl:text-[2.6rem]">
              Every student query, routed with clarity.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-slate-300">
              One secure workspace to submit requests, collaborate across departments and resolve
              student issues with a complete audit trail.
            </p>
            <ul className="mt-9 grid gap-5 sm:grid-cols-2">
              {HIGHLIGHTS.map(({ icon: Icon, title: heading, description }) => (
                <li key={heading} className="flex gap-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/15 bg-white/10 text-teal-200">
                    <Icon className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <span>
                    <span className="block text-sm font-semibold text-white">{heading}</span>
                    <span className="mt-0.5 block text-xs leading-relaxed text-slate-300">{description}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="relative z-10 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
            <span>© {new Date().getFullYear()} University Communication Hub</span>
            <span>Secure · Auditable · Role-scoped</span>
          </div>
        </section>

        <section className="flex items-center justify-center px-4 py-8 sm:px-8 sm:py-12 lg:px-10">
          <div className="w-full max-w-md">
            <div className="mb-7 lg:hidden">
              <BrandMark size={40} showWordmark />
            </div>

            <div className="surface-card p-6 sm:p-8">
              <p className="eyebrow text-teal-700">University portal</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-navy-900 sm:text-[1.7rem]">{title}</h1>
              <p className="mt-2 text-sm leading-relaxed text-slate-500">{subtitle}</p>
              <div className="mt-7">{children}</div>
            </div>

            <div className="mt-6 text-center text-sm text-slate-600">{footer}</div>
            <p className="mt-4 text-center text-xs text-slate-500">
              Protected by HttpOnly cookies and CSRF validation.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
