import { LogOut, Menu } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { useAuth } from '../../context/AuthContext';

function initials(fullName = '') {
  return fullName
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');
}

export default function Topbar({ title, subtitle }) {
  const { openSidebar } = useApp();
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
        <button
          type="button"
          onClick={openSidebar}
          aria-label="Open navigation"
          className="rounded-md p-2 text-navy-800 hover:bg-slate-100 lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="min-w-0 flex-1">
          <h2 className="truncate text-base font-semibold text-navy-900 sm:text-lg">{title}</h2>
          <p className="hidden truncate text-xs text-slate-500 sm:block">{subtitle}</p>
        </div>

        <div className="flex items-center gap-2.5 border-l border-slate-200 pl-4">
          <div
            className="flex h-9 w-9 items-center justify-center rounded-full bg-navy-900 text-xs font-semibold text-white"
            aria-hidden="true"
          >
            {initials(user?.full_name) || '?'}
          </div>
          <div className="hidden sm:block">
            <p className="text-sm font-medium text-navy-900">{user?.full_name || 'Account'}</p>
            <p className="text-xs capitalize text-slate-500">{user?.role || 'Guest'}</p>
          </div>
          <button
            type="button"
            onClick={logout}
            title="Sign out"
            aria-label="Sign out"
            className="ml-1 rounded-lg p-2 text-slate-500 hover:bg-rose-50 hover:text-rose-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>
    </header>
  );
}
