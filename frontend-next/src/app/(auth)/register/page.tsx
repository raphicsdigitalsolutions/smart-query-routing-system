'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AlertCircle, Check, Loader2, Mail, UserRound } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AuthShell } from '@/components/auth/AuthShell';
import { PasswordInput } from '@/components/auth/PasswordInput';
import { useSession } from '@/hooks/useSession';
import { getApiErrorMessage } from '@/lib/api/errors';
import { cn } from '@/lib/utils';

interface FieldErrors {
  full_name?: string;
  email?: string;
  password?: string;
}

export default function RegisterPage() {
  const router = useRouter();
  const { status, user, register } = useSession();
  const [form, setForm] = useState({ full_name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (status === 'authenticated' && user) router.replace('/student');
  }, [status, user, router]);

  function updateField(key: keyof FieldErrors | keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
    setFieldErrors((current) => ({ ...current, [key]: undefined }));
  }

  function validate(): boolean {
    const next: FieldErrors = {};
    if (form.full_name.trim().length < 2) next.full_name = 'Enter your full name.';
    if (!form.email.trim()) next.email = 'Email address is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      next.email = 'Enter a valid email address.';
    }
    if (form.password.length < 12) next.password = 'Password must be at least 12 characters long.';
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError('');
    if (!validate()) return;
    setSubmitting(true);
    try {
      await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
      });
      router.replace('/student');
    } catch (cause) {
      setError(getApiErrorMessage(cause, 'Unable to create your account.'));
    } finally {
      setSubmitting(false);
    }
  }

  const passwordReady = form.password.length >= 12;

  return (
    <AuthShell
      title="Create your account"
      subtitle="Public registration creates a student account. Staff and administrator accounts are provisioned separately."
      footer={
        <span>
          Already registered?{' '}
          <Link href="/login" className="font-semibold text-teal-700 hover:text-teal-800 hover:underline">
            Sign in
          </Link>
        </span>
      }
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        <div>
          <label htmlFor="register-name" className="field-label">Full name</label>
          <div className="relative">
            <UserRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              id="register-name"
              value={form.full_name}
              onChange={(event) => updateField('full_name', event.target.value)}
              autoComplete="name"
              maxLength={120}
              placeholder="e.g. Ada Lovelace"
              aria-invalid={Boolean(fieldErrors.full_name)}
              aria-describedby={fieldErrors.full_name ? 'register-name-error' : undefined}
              className={cn(
                'field-input field-input-with-icon',
                fieldErrors.full_name && 'border-rose-400 focus:border-rose-500 focus:ring-rose-500/15',
              )}
            />
          </div>
          {fieldErrors.full_name ? (
            <p id="register-name-error" className="mt-1.5 flex items-center gap-1.5 text-xs text-rose-600">
              <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" /> {fieldErrors.full_name}
            </p>
          ) : null}
        </div>

        <div>
          <label htmlFor="register-email" className="field-label">Email address</label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              id="register-email"
              type="email"
              value={form.email}
              onChange={(event) => updateField('email', event.target.value)}
              autoComplete="email"
              maxLength={255}
              placeholder="you@university.edu"
              aria-invalid={Boolean(fieldErrors.email)}
              aria-describedby={fieldErrors.email ? 'register-email-error' : undefined}
              className={cn(
                'field-input field-input-with-icon',
                fieldErrors.email && 'border-rose-400 focus:border-rose-500 focus:ring-rose-500/15',
              )}
            />
          </div>
          {fieldErrors.email ? (
            <p id="register-email-error" className="mt-1.5 flex items-center gap-1.5 text-xs text-rose-600">
              <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" /> {fieldErrors.email}
            </p>
          ) : null}
        </div>

        <div>
          <label htmlFor="register-password" className="field-label">Password</label>
          <PasswordInput
            id="register-password"
            value={form.password}
            onChange={(event) => updateField('password', event.target.value)}
            autoComplete="new-password"
            maxLength={128}
            placeholder="Create a strong password"
            aria-invalid={Boolean(fieldErrors.password)}
            aria-describedby="register-password-hint"
            className={cn(
              fieldErrors.password && 'border-rose-400 focus:border-rose-500 focus:ring-rose-500/15',
            )}
          />
          <p
            id="register-password-hint"
            className={cn('mt-1.5 flex items-center gap-1.5 text-xs', passwordReady ? 'text-teal-700' : 'text-slate-500')}
          >
            {passwordReady ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" />}
            At least 12 characters · stored as an Argon2 hash
          </p>
          {fieldErrors.password ? (
            <p role="alert" className="mt-1 flex items-center gap-1.5 text-xs text-rose-600">
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

        <Button type="submit" variant="teal" size="lg" className="w-full" disabled={submitting}>
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
          {submitting ? 'Creating account…' : 'Create account'}
        </Button>
      </form>
    </AuthShell>
  );
}
