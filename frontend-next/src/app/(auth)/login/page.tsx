'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AlertCircle, Loader2, LockKeyhole, Mail } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AuthShell } from '@/components/auth/AuthShell';
import { GoogleSignInButton } from '@/components/auth/GoogleSignInButton';
import { PasswordInput } from '@/components/auth/PasswordInput';
import { useSession } from '@/hooks/useSession';
import { getApiErrorMessage } from '@/lib/api/errors';
import { ROLE_HOME } from '@/lib/api/types';
import { cn } from '@/lib/utils';

interface FieldErrors {
  email?: string;
  password?: string;
}

export default function LoginPage() {
  const router = useRouter();
  const { status, user, login, loginGoogle } = useSession();
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? '';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [googleSubmitting, setGoogleSubmitting] = useState(false);

  useEffect(() => {
    if (status === 'authenticated' && user) router.replace(ROLE_HOME[user.role]);
  }, [status, user, router]);

  function validate(): boolean {
    const next: FieldErrors = {};
    if (!email.trim()) next.email = 'Email address is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      next.email = 'Enter a valid email address.';
    }
    if (!password) next.password = 'Password is required.';
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError('');
    if (!validate()) return;
    setSubmitting(true);
    try {
      const signedIn = await login(email.trim(), password);
      router.replace(ROLE_HOME[signedIn.role]);
    } catch (cause) {
      setError(getApiErrorMessage(cause, 'Unable to sign in.'));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGoogleCredential(credential: string) {
    setError('');
    setGoogleSubmitting(true);
    try {
      const signedIn = await loginGoogle(credential);
      router.replace(ROLE_HOME[signedIn.role]);
    } catch (cause) {
      setError(getApiErrorMessage(cause, 'Google sign-in failed.'));
    } finally {
      setGoogleSubmitting(false);
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to access your university workspace."
      footer={
        <span>
          New here?{' '}
          <Link href="/register" className="font-semibold text-teal-700 hover:text-teal-800 hover:underline">
            Create an account
          </Link>
        </span>
      }
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        <div>
          <label htmlFor="login-email" className="field-label">Email address</label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setFieldErrors((current) => ({ ...current, email: undefined }));
              }}
              autoComplete="email"
              placeholder="you@university.edu"
              aria-invalid={Boolean(fieldErrors.email)}
              aria-describedby={fieldErrors.email ? 'login-email-error' : undefined}
              className={cn(
                'field-input field-input-with-icon',
                fieldErrors.email && 'border-rose-400 focus:border-rose-500 focus:ring-rose-500/15',
              )}
            />
          </div>
          {fieldErrors.email ? (
            <p id="login-email-error" className="mt-1.5 flex items-center gap-1.5 text-xs text-rose-600">
              <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" /> {fieldErrors.email}
            </p>
          ) : null}
        </div>

        <div>
          <label htmlFor="login-password" className="field-label">Password</label>
          <PasswordInput
            id="login-password"
            value={password}
            onChange={(event) => {
              setPassword(event.target.value);
              setFieldErrors((current) => ({ ...current, password: undefined }));
            }}
            autoComplete="current-password"
            placeholder="Enter your password"
            aria-invalid={Boolean(fieldErrors.password)}
            aria-describedby={fieldErrors.password ? 'login-password-error' : undefined}
            className={cn(
              fieldErrors.password && 'border-rose-400 focus:border-rose-500 focus:ring-rose-500/15',
            )}
          />
          {fieldErrors.password ? (
            <p id="login-password-error" className="mt-1.5 flex items-center gap-1.5 text-xs text-rose-600">
              <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" /> {fieldErrors.password}
            </p>
          ) : null}
        </div>

        {error ? (
          <p role="alert" className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </p>
        ) : null}

        <Button type="submit" size="lg" className="w-full" disabled={submitting || googleSubmitting}>
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <LockKeyhole className="h-4 w-4" aria-hidden="true" />}
          {submitting ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>

      {googleSubmitting ? (
        <p role="status" className="mt-4 flex items-center justify-center gap-2 text-sm text-teal-700">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Completing Google sign-in…
        </p>
      ) : null}

      {googleClientId ? (
        <div className="mt-6">
          <GoogleSignInButton clientId={googleClientId} onCredential={handleGoogleCredential} />
        </div>
      ) : null}
    </AuthShell>
  );
}
