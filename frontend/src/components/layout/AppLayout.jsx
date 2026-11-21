import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

const PAGE_META = {
  '/dashboard': ['Overview', 'University communication at a glance'],
  '/student': ['Student Dashboard', 'Your queries and staff replies'],
  '/staff': ['Staff Dashboard', 'Assigned queries and team workload'],
  '/admin': ['Admin Dashboard', 'Ticket overview across all departments'],
};

export default function AppLayout() {
  const { pathname } = useLocation();
  const [title, subtitle] = pathname.startsWith('/tickets/')
    ? ['Ticket detail', 'Conversation, workflow and recorded history']
    : PAGE_META[pathname] || PAGE_META['/dashboard'];

  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar />
      <div className="lg:pl-64">
        <Topbar title={title} subtitle={subtitle} />
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
