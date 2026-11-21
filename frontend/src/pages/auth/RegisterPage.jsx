import { useState } from 'react';
import { LockKeyhole, Mail, UserRound } from 'lucide-react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getApiErrorMessage } from '../../services/api';
import logo from '../../assets/logo.svg';

export default function RegisterPage() {
  const { register, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) return <Navigate to="/student" replace />;

  const update = (field) => (event) => setForm((prev) => ({ ...prev, [field]: event.target.value }));

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    if (form.password.length < 12) {
      setError('Password must be at least 12 characters long.');
      return;
    }
    setSubmitting(true);
    try {
      await register(form);
      navigate('/student', { replace: true });
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to create the account.'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center justify-center gap-3">
          <img src={logo} alt="" className="h-10 w-10" />
          <div>
            <p className="text-base font-semibold text-navy-900">Communication Hub</p>
            <p className="text-xs text-slate-500">Student registration</p>
          </div>
        </div>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <h1 className="text-xl font-semibold tracking-tight text-navy-900">Create student account</h1>
          <p className="mt-1 text-sm text-slate-500">
            Public registration always creates a student account. Staff and administrator roles are
            assigned by an administrator.
          </p>

          {error && (
            <div role="alert" className="mt-5 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          )}

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-navy-800">Full name</label>
              <div className="relative mt-1.5">
                <UserRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                <input
                  id="full_name"
                  type="text"
                  required
                  minLength={2}
                  autoComplete="name"
                  value={form.full_name}
                  onChange={update('full_name')}
                  className="w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-600"
                />
              </div>
            </div>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-navy-800">University email</label>
              <div className="relative mt-1.5">
                <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                <input
                  id="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={form.email}
                  onChange={update('email')}
                  className="w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-600"
                />
              </div>
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-navy-800">Password</label>
              <div className="relative mt-1.5">
                <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                <input
                  id="password"
                  type="password"
                  required
                  minLength={12}
                  autoComplete="new-password"
                  value={form.password}
                  onChange={update('password')}
                  className="w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-3 text-sm outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-600"
                />
              </div>
              <p className="mt-1 text-xs text-slate-500">At least 12 characters. Stored as an Argon2 hash.</p>
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-600 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <p className="mt-6 text-sm text-slate-500">
            Already registered?{' '}
            <Link to="/login" className="font-semibold text-navy-700 hover:text-teal-700">Sign in</Link>
          </p>
        </section>
      </div>
    </div>
  );
}
