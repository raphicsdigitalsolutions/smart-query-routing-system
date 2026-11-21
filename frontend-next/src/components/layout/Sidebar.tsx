'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  Bell,
  BookOpenText,
  Building2,
  CalendarDays,
  ChevronsLeft,
  ChevronsRight,
  GraduationCap,
  KeyRound,
  LayoutDashboard,
  LifeBuoy,
  Megaphone,
  ScrollText,
  ShieldCheck,
  UsersRound,
  X,
} from 'lucide-react';
import type { Role } from '@/lib/api/types';
import { useSession } from '@/hooks/useSession';
import { BrandMark } from '@/components/common/BrandMark';
import { cn, initials, prettyLabel } from '@/lib/utils';

interface NavItem {
  label: string;
  href: string;
  roles?: Role[];
  icon: React.ReactNode;
}

const NAV_GROUPS: Array<{ title: string; items: NavItem[] }> = [
  {
    title: 'Workspace',
    items: [{ label: 'Overview', href: '/dashboard', icon: <LayoutDashboard className="h-[18px] w-[18px]" aria-hidden="true" /> }],
  },
  {
    title: 'Role views',
    items: [
      { label: 'Student', href: '/student', roles: ['student'], icon: <GraduationCap className="h-[18px] w-[18px]" aria-hidden="true" /> },
      { label: 'Staff', href: '/staff', roles: ['staff', 'hod'], icon: <UsersRound className="h-[18px] w-[18px]" aria-hidden="true" /> },
      { label: 'HOD', href: '/hod', roles: ['hod'], icon: <Building2 className="h-[18px] w-[18px]" aria-hidden="true" /> },
      { label: 'Admin', href: '/admin', roles: ['admin'], icon: <ShieldCheck className="h-[18px] w-[18px]" aria-hidden="true" /> },
    ],
  },
  {
    title: 'Workspace tools',
    items: [
      { label: 'Analytics', href: '/analytics', icon: <BarChart3 className="h-[18px] w-[18px]" aria-hidden="true" /> },
      { label: 'Notifications', href: '/notifications', icon: <Bell className="h-[18px] w-[18px]" aria-hidden="true" /> },
      { label: 'Announcements', href: '/announcements', icon: <Megaphone className="h-[18px] w-[18px]" aria-hidden="true" /> },
      { label: 'Leave windows', href: '/leave', roles: ['staff', 'hod', 'admin'], icon: <CalendarDays className="h-[18px] w-[18px]" aria-hidden="true" /> },
      { label: 'Knowledge', href: '/knowledge', roles: ['hod', 'admin'], icon: <BookOpenText className="h-[18px] w-[18px]" aria-hidden="true" /> },
      { label: 'Audit log', href: '/audit', roles: ['admin'], icon: <ScrollText className="h-[18px] w-[18px]" aria-hidden="true" /> },
    ],
  },
  {
    title: 'Preferences',
    items: [
      { label: 'Settings', href: '/settings', icon: <KeyRound className="h-[18px] w-[18px]" aria-hidden="true" /> },
    ],
  },
];

interface SidebarProps {
  open: boolean;
  collapsed: boolean;
  onClose: () => void;
  onToggleCollapsed: () => void;
}

export function Sidebar({ open, collapsed, onClose, onToggleCollapsed }: SidebarProps) {
  const pathname = usePathname();
  const { hasRole, user } = useSession();

  const groups = NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => !item.roles || item.roles.some((role) => hasRole(role))),
  })).filter((group) => group.items.length > 0);

  return (
    <>
      {open ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-navy-950/60 backdrop-blur-[2px] lg:hidden"
          aria-label="Dismiss navigation overlay"
          onClick={onClose}
        />
      ) : null}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex flex-col border-r border-white/5 bg-navy-900 text-white transition-[width,transform] duration-200 ease-out lg:translate-x-0',
          collapsed ? 'lg:w-[76px]' : 'lg:w-[268px]',
          'w-[268px]',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className={cn('flex h-[68px] shrink-0 items-center border-b border-white/10', collapsed ? 'lg:justify-center lg:px-0' : 'px-5')}>
          <Link href="/dashboard" className="flex min-w-0 items-center gap-3" onClick={onClose} aria-label="Smart Query home">
            <BrandMark inverted size={38} />
            <span className={cn('min-w-0', collapsed && 'lg:hidden')}>
              <span className="block text-sm font-semibold leading-tight">Smart Query</span>
              <span className="block text-[11px] text-teal-200">Communication Hub</span>
            </span>
          </Link>
          <button
            type="button"
            onClick={onClose}
            className="ml-auto rounded-lg p-1.5 text-slate-300 hover:bg-white/10 hover:text-white lg:hidden"
            aria-label="Close navigation"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5" aria-label="Main navigation">
          {groups.map((group) => (
            <div key={group.title}>
              <p
                className={cn(
                  'px-3 pb-2 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400',
                  collapsed && 'lg:hidden',
                )}
              >
                {group.title}
              </p>
              <div className="space-y-1">
                {group.items.map((item) => {
                  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      title={collapsed ? item.label : undefined}
                      aria-label={item.label}
                      onClick={onClose}
                      aria-current={active ? 'page' : undefined}
                      className={cn(
                        'relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                        collapsed && 'lg:justify-center lg:px-0',
                        active
                          ? 'bg-white/10 text-white'
                          : 'text-slate-300 hover:bg-white/[0.07] hover:text-white',
                      )}
                    >
                      {active ? (
                        <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-teal-400" aria-hidden="true" />
                      ) : null}
                      <span className={cn(active && 'text-teal-300')}>{item.icon}</span>
                      <span className={cn(collapsed && 'lg:hidden')}>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="shrink-0 border-t border-white/10 p-3">
          <Link
            href="/dashboard"
            className={cn(
              'mb-2 flex items-center gap-3 rounded-lg px-3 py-2 text-xs font-medium text-slate-300 transition-colors hover:bg-white/[0.07] hover:text-white',
              collapsed && 'lg:justify-center lg:px-0',
            )}
          >
            <LifeBuoy className="h-[18px] w-[18px]" aria-hidden="true" />
            <span className={cn(collapsed && 'lg:hidden')}>Help & overview</span>
          </Link>

          {user ? (
            <div
              className={cn(
                'flex items-center gap-3 rounded-xl bg-white/[0.06] p-2.5',
                collapsed && 'lg:justify-center lg:p-2',
              )}
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-teal-600/20 text-xs font-semibold text-teal-200">
                {initials(user.full_name)}
              </span>
              <span className={cn('min-w-0 flex-1', collapsed && 'lg:hidden')}>
                <span className="block truncate text-xs font-semibold text-white">{user.full_name}</span>
                <span className="block truncate text-[11px] text-slate-400">{prettyLabel(user.role)}</span>
              </span>
            </div>
          ) : null}

          <button
            type="button"
            onClick={onToggleCollapsed}
            className={cn(
              'mt-2 hidden w-full items-center gap-3 rounded-lg px-3 py-2 text-xs font-medium text-slate-400 transition-colors hover:bg-white/[0.07] hover:text-white lg:flex',
              collapsed && 'lg:justify-center lg:px-0',
            )}
            aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
          >
            {collapsed ? <ChevronsRight className="h-[18px] w-[18px]" aria-hidden="true" /> : <ChevronsLeft className="h-[18px] w-[18px]" aria-hidden="true" />}
            <span className={cn(collapsed && 'lg:hidden')}>Collapse navigation</span>
          </button>
        </div>
      </aside>
    </>
  );
}
