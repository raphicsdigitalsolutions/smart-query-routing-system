'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  Bell,
  ChevronDown,
  ChevronRight,
  Compass,
  LayoutDashboard,
  LogOut,
  Menu,
  PlusCircle,
  UserRound,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { notificationsApi } from '@/lib/api/endpoints';
import { getApiErrorMessage } from '@/lib/api/errors';
import { ROLE_HOME, type NotificationItem, type UserResponse } from '@/lib/api/types';
import { useSession } from '@/hooks/useSession';
import { formatDateTime, initials, prettyLabel } from '@/lib/utils';
import { Skeleton } from '@/components/common/Skeleton';

interface TopbarProps {
  user: UserResponse;
  onMenuClick: () => void;
}

function pageMeta(pathname: string): [string, string] {
  if (pathname.startsWith('/student')) return ['My queries', 'Submit and track your requests'];
  if (pathname.startsWith('/staff')) return ['Staff workspace', 'Assigned queue and ticket collaboration'];
  if (pathname.startsWith('/hod')) return ['Department overview', 'Queue, assignment and escalation review'];
  if (pathname.startsWith('/admin')) return ['Administration', 'Tickets, departments and assignment control'];
  if (pathname.startsWith('/tickets/')) return ['Ticket detail', 'Conversation, workflow and recorded history'];
  if (pathname.startsWith('/settings')) return ['Settings', 'Personal keys and integration status'];
  if (pathname.startsWith('/knowledge')) return ['Knowledge', 'Approved sources for grounded answers'];
  if (pathname.startsWith('/analytics')) return ['Analytics', 'Role-scoped ticket insights and reports'];
  if (pathname.startsWith('/announcements')) return ['Announcements', 'University broadcasts'];
  if (pathname.startsWith('/leave')) return ['Leave windows', 'Availability and auto-replies'];
  if (pathname.startsWith('/audit')) return ['Audit log', 'Recorded sensitive actions'];
  if (pathname.startsWith('/notifications')) return ['Notifications', 'Your in-app notification centre'];
  return ['Overview', 'University communication at a glance'];
}

export function Topbar({ user, onMenuClick }: TopbarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { logout } = useSession();
  const [title, subtitle] = pageMeta(pathname);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loadingNotifications, setLoadingNotifications] = useState(true);
  const [notificationError, setNotificationError] = useState('');

  const loadNotifications = useCallback(async () => {
    setLoadingNotifications(true);
    setNotificationError('');
    try {
      const result = await notificationsApi.list({ limit: 8 });
      setNotifications(result.items);
    } catch (cause) {
      setNotificationError(getApiErrorMessage(cause, 'Unable to load notifications.'));
    } finally {
      setLoadingNotifications(false);
    }
  }, []);

  useEffect(() => {
    void loadNotifications();
  }, [loadNotifications, pathname]);

  const unreadCount = notifications.filter((item) => !item.read_at).length;

  async function markNotificationRead(notification: NotificationItem) {
    if (notification.read_at) return;
    try {
      await notificationsApi.markRead(notification.id);
      setNotifications((current) =>
        current.map((item) =>
          item.id === notification.id ? { ...item, read_at: new Date().toISOString() } : item,
        ),
      );
    } catch (cause) {
      toast.error(getApiErrorMessage(cause, 'Unable to mark this notification as read.'));
    }
  }

  async function handleSignOut() {
    await logout();
    toast.success('Signed out');
    router.replace('/login');
  }

  return (
    <header className="sticky top-0 z-20 flex h-[68px] shrink-0 items-center justify-between gap-4 border-b border-slate-200/80 bg-white/95 px-4 backdrop-blur sm:px-6 lg:px-8">
      <div className="flex min-w-0 items-center gap-3">
        <Button variant="ghost" size="icon" className="lg:hidden" onClick={onMenuClick} aria-label="Open navigation">
          <Menu className="h-5 w-5" aria-hidden="true" />
        </Button>
        <div className="min-w-0">
          <div className="hidden items-center gap-1.5 text-[11px] font-medium text-slate-500 sm:flex">
            <span>Workspace</span>
            <ChevronRight className="h-3 w-3" aria-hidden="true" />
            <span className="text-slate-500">{title}</span>
          </div>
          <h1 className="truncate text-lg font-semibold tracking-tight text-navy-900 sm:text-xl">{title}</h1>
          <p className="hidden truncate text-xs text-slate-500 sm:block">{subtitle}</p>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="hidden md:inline-flex" aria-label="Quick links">
              <Compass className="h-4 w-4 text-slate-500" aria-hidden="true" />
              Quick links
              <ChevronDown className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52">
            <DropdownMenuLabel>Go to</DropdownMenuLabel>
            <DropdownMenuItem onSelect={() => router.push('/dashboard')}>
              <LayoutDashboard className="h-4 w-4" aria-hidden="true" /> Overview
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => router.push(ROLE_HOME[user.role])}>
              <UserRound className="h-4 w-4" aria-hidden="true" /> My role view
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => router.push('/student')}>
              <PlusCircle className="h-4 w-4" aria-hidden="true" /> Submit a query
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu onOpenChange={(open) => { if (open) void loadNotifications(); }}>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="relative"
              aria-label={unreadCount > 0 ? `Notifications, ${unreadCount} unread` : 'Notifications'}
            >
              <Bell className="h-[18px] w-[18px] text-slate-500" aria-hidden="true" />
              {unreadCount > 0 ? (
                <span className="absolute right-1 top-1 flex min-w-4 items-center justify-center rounded-full bg-teal-600 px-1 text-[10px] font-bold leading-4 text-white">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              ) : null}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-[min(20rem,calc(100vw-2rem))] p-0">
            <div className="border-b border-slate-100 px-4 py-3">
              <p className="text-sm font-semibold text-navy-900">Notifications</p>
              <p className="text-xs text-slate-500">
                {unreadCount > 0 ? `${unreadCount} unread update${unreadCount === 1 ? '' : 's'}` : 'Updates from your workspace'}
              </p>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {notificationError ? (
                <p role="alert" className="px-4 py-3 text-xs text-rose-700">{notificationError}</p>
              ) : null}
              {loadingNotifications ? (
                <div className="space-y-3 px-4 py-4">
                  <Skeleton className="h-3 w-3/4" />
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-2/3" />
                </div>
              ) : null}
              {!loadingNotifications && !notificationError && notifications.length === 0 ? (
                <div className="px-5 py-8 text-center">
                  <span className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                    <Bell className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <p className="mt-3 text-sm font-medium text-navy-800">No notifications yet</p>
                  <p className="mt-1 text-xs leading-relaxed text-slate-500">
                    Ticket updates will appear here once they are generated.
                  </p>
                </div>
              ) : null}
              {!loadingNotifications
                ? notifications.map((notification) => (
                    <DropdownMenuItem
                      key={notification.id}
                      className="flex flex-col items-start gap-1 whitespace-normal px-4 py-3 focus:bg-slate-50"
                      onSelect={(event) => {
                        event.preventDefault();
                        void markNotificationRead(notification);
                      }}
                    >
                      <span className="flex w-full items-center justify-between gap-2">
                        <span className="truncate text-xs font-semibold text-navy-900">
                          {notification.subject ?? prettyLabel(notification.event_type)}
                        </span>
                        {!notification.read_at ? (
                          <span className="h-2 w-2 shrink-0 rounded-full bg-teal-500" aria-label="Unread" />
                        ) : null}
                      </span>
                      <span className="line-clamp-2 text-xs leading-relaxed text-slate-600">{notification.body}</span>
                      <span className="text-[10px] text-slate-400">{formatDateTime(notification.created_at)}</span>
                    </DropdownMenuItem>
                  ))
                : null}
            </div>
            <div className="border-t border-slate-100 px-4 py-2.5">
              <Link href="/notifications" className="text-xs font-semibold text-teal-700 hover:underline">
                View all notifications
              </Link>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        <span className="mx-1 hidden h-7 w-px bg-slate-200 sm:block" aria-hidden="true" />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white py-1.5 pl-1.5 pr-2 text-left shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600/40"
            >
              <span className="sr-only">Account menu</span>
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-50 text-xs font-semibold text-teal-700" aria-hidden="true">
                {initials(user.full_name)}
              </span>
              <span className="hidden sm:block">
                <span className="block max-w-32 truncate text-xs font-semibold text-navy-900">{user.full_name}</span>
                <span className="block text-[11px] text-slate-500">{prettyLabel(user.role)}</span>
              </span>
              <ChevronDown className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-60">
            <DropdownMenuLabel className="normal-case tracking-normal">
              <span className="block truncate text-sm font-semibold text-navy-900">{user.full_name}</span>
              <span className="block truncate text-xs font-normal text-slate-500">{user.email}</span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href={ROLE_HOME[user.role]}>
                <UserRound className="h-4 w-4" aria-hidden="true" /> My workspace
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => void handleSignOut()} className="text-rose-600 focus:bg-rose-50 focus:text-rose-700">
              <LogOut className="h-4 w-4" aria-hidden="true" /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
