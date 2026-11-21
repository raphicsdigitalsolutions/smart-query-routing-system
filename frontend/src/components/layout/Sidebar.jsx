import { NavLink } from 'react-router-dom';
import {
  GraduationCap,
  LayoutDashboard,
  ShieldCheck,
  UsersRound,
  X,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { useAuth } from '../../context/AuthContext';
import logo from '../../assets/logo.svg';

const NAV_GROUPS = [
  {
    label: 'Workspace',
    items: [{ to: '/dashboard', label: 'Overview', icon: LayoutDashboard, roles: null }],
  },
  {
    label: 'Role views',
    items: [
      { to: '/student', label: 'Student', icon: GraduationCap, roles: ['student'] },
      { to: '/staff', label: 'Staff', icon: UsersRound, roles: ['staff', 'hod'] },
      { to: '/admin', label: 'Admin', icon: ShieldCheck, roles: ['admin'] },
    ],
  },
];

export default function Sidebar() {
  const { appName, isSidebarOpen, closeSidebar } = useApp();
  const { hasRole } = useAuth();
  const groups = NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => !item.roles || hasRole(...item.roles)),
  })).filter((group) => group.items.length > 0);

  return (
    <>
      {isSidebarOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={closeSidebar}
          className="fixed inset-0 z-30 bg-navy-950/50 lg:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-navy-900 text-white transition-transform duration-200 lg:translate-x-0 ${
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-16 items-center gap-3 border-b border-navy-800 px-5">
          <img src={logo} alt="" className="h-9 w-9" />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">Communication Hub</p>
            <p className="truncate text-xs text-navy-200">University Portal</p>
          </div>
          <button
            type="button"
            onClick={closeSidebar}
            aria-label="Close navigation"
            className="ml-auto rounded-md p-1 text-navy-200 hover:bg-navy-800 hover:text-white lg:hidden"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-6" aria-label="Main navigation">
          {groups.map((group) => (
            <div key={group.label}>
              <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-wider text-navy-200">
                {group.label}
              </p>
              <div className="space-y-1">
                {group.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={closeSidebar}
                    className={({ isActive }) =>
                      `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-teal-600 text-white'
                          : 'text-navy-100 hover:bg-navy-800 hover:text-white'
                      }`
                    }
                  >
                    <item.icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                    {item.label}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-navy-800 px-5 py-4">
          <p className="text-xs text-navy-200">{appName}</p>
          <p className="mt-1 text-xs font-medium text-teal-100">Phase 4 · Secure core</p>
        </div>
      </aside>
    </>
  );
}
