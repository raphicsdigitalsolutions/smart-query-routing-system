import { Link, Navigate, useLocation } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import LoadingScreen from '../common/LoadingScreen';

export default function ProtectedRoute({ children, roles }) {
  const { status, isAuthenticated, hasRole } = useAuth();
  const location = useLocation();

  if (status === 'loading') return <LoadingScreen />;
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (roles && !hasRole(...roles)) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center px-4">
        <div className="w-full max-w-md rounded-xl border border-rose-200 bg-white p-8 text-center shadow-sm">
          <ShieldAlert className="mx-auto h-10 w-10 text-rose-500" aria-hidden="true" />
          <h1 className="mt-4 text-lg font-semibold text-navy-900">Access restricted</h1>
          <p className="mt-2 text-sm text-slate-500">
            Your role does not have permission to view this page. Backend authorization also
            enforces this rule.
          </p>
          <Link
            to="/dashboard"
            className="mt-6 inline-block rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800"
          >
            Back to overview
          </Link>
        </div>
      </div>
    );
  }
  return children;
}
