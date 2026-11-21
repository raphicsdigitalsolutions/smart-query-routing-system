import { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { AuthProvider } from './context/AuthContext';
import AppLayout from './components/layout/AppLayout';
import ProtectedRoute from './components/auth/ProtectedRoute';
import ErrorBoundary from './components/common/ErrorBoundary';
import LoadingScreen from './components/common/LoadingScreen';

const DashboardPage = lazy(() => import('./pages/dashboard/DashboardPage'));
const StudentDashboardPage = lazy(() => import('./pages/student/StudentDashboardPage'));
const StaffDashboardPage = lazy(() => import('./pages/staff/StaffDashboardPage'));
const AdminDashboardPage = lazy(() => import('./pages/admin/AdminDashboardPage'));
const TicketDetailPage = lazy(() => import('./pages/tickets/TicketDetailPage'));
const LoginPage = lazy(() => import('./pages/auth/LoginPage'));
const RegisterPage = lazy(() => import('./pages/auth/RegisterPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));

export default function App() {
  return (
    <ErrorBoundary>
      <AppProvider>
        <BrowserRouter>
          <AuthProvider>
            <Suspense fallback={<LoadingScreen />}>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
                  <Route index element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/tickets/:ticketId" element={<TicketDetailPage />} />
                  <Route path="/student" element={<ProtectedRoute roles={['student']}><StudentDashboardPage /></ProtectedRoute>} />
                  <Route path="/staff" element={<ProtectedRoute roles={['staff', 'hod']}><StaffDashboardPage /></ProtectedRoute>} />
                  <Route path="/admin" element={<ProtectedRoute roles={['admin']}><AdminDashboardPage /></ProtectedRoute>} />
                  <Route path="*" element={<NotFoundPage />} />
                </Route>
              </Routes>
            </Suspense>
          </AuthProvider>
        </BrowserRouter>
      </AppProvider>
    </ErrorBoundary>
  );
}
