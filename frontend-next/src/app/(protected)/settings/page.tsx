'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Bot,
  CheckCircle2,
  KeyRound,
  Loader2,
  Mail,
  MessageSquare,
  PlugZap,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Webhook,
} from 'lucide-react';
import { toast } from 'sonner';
import { PasswordInput } from '@/components/auth/PasswordInput';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { PageHeader } from '@/components/common/PageHeader';
import { Skeleton } from '@/components/common/Skeleton';
import { StatusPill } from '@/components/common/StatusPill';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { apiKeysApi, integrationsApi } from '@/lib/api/endpoints';
import { getApiErrorMessage } from '@/lib/api/errors';
import { ROLE_HOME, type ApiKeyStatus, type IntegrationStatus } from '@/lib/api/types';
import { useSession } from '@/hooks/useSession';
import { formatDateTime } from '@/lib/utils';

function StatusRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5 border-b border-slate-100 py-2.5 last:border-0 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
      <dt className="text-xs font-medium text-slate-500">{label}</dt>
      <dd className="min-w-0 break-words text-sm font-medium text-navy-900">{value}</dd>
    </div>
  );
}

export default function SettingsPage() {
  const { user } = useSession();
  const [keys, setKeys] = useState<ApiKeyStatus[]>([]);
  const [keyValue, setKeyValue] = useState('');
  const [loadingKeys, setLoadingKeys] = useState(true);
  const [keysError, setKeysError] = useState('');
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [formError, setFormError] = useState('');
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [integrations, setIntegrations] = useState<IntegrationStatus | null>(null);
  const [loadingIntegrations, setLoadingIntegrations] = useState(true);
  const [integrationsError, setIntegrationsError] = useState('');

  const loadKeys = useCallback(async () => {
    setLoadingKeys(true);
    setKeysError('');
    try {
      setKeys(await apiKeysApi.list());
    } catch (cause) {
      setKeysError(getApiErrorMessage(cause, 'Unable to load your API key status.'));
    } finally {
      setLoadingKeys(false);
    }
  }, []);

  const loadIntegrations = useCallback(async () => {
    setLoadingIntegrations(true);
    setIntegrationsError('');
    try {
      setIntegrations(await integrationsApi.status());
    } catch (cause) {
      setIntegrationsError(getApiErrorMessage(cause, 'Unable to load integration status.'));
    } finally {
      setLoadingIntegrations(false);
    }
  }, []);

  useEffect(() => {
    void loadKeys();
    void loadIntegrations();
  }, [loadKeys, loadIntegrations]);

  async function handleSave() {
    if (!keyValue.trim()) {
      setFormError('Enter an API key before saving.');
      return;
    }
    setSaving(true);
    setFormError('');
    try {
      await apiKeysApi.save(keyValue.trim());
      setKeyValue('');
      toast.success('Personal API key saved securely.');
      await loadKeys();
    } catch (cause) {
      setFormError(getApiErrorMessage(cause, 'Unable to save the API key.'));
    } finally {
      setSaving(false);
    }
  }

  async function handleValidate() {
    setValidating(true);
    setFormError('');
    try {
      const result = await apiKeysApi.validate();
      setKeys((current) => current.map((item) => (item.provider === result.provider ? result : item)));
      toast.success(result.is_valid ? 'Your API key is valid.' : 'Your API key could not be validated.');
    } catch (cause) {
      setFormError(getApiErrorMessage(cause, 'Unable to validate the API key.'));
    } finally {
      setValidating(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    setFormError('');
    try {
      await apiKeysApi.remove();
      setConfirmOpen(false);
      setKeyValue('');
      toast.success('Personal API key removed.');
      await loadKeys();
    } catch (cause) {
      setFormError(getApiErrorMessage(cause, 'Unable to remove the API key.'));
    } finally {
      setDeleting(false);
    }
  }

  const configured = keys.filter((item) => item.configured);
  const primary = configured[0] ?? keys[0] ?? null;

  const integrationCards = [
    { key: 'smtp' as const, label: 'Email (SMTP)', icon: <Mail className="h-5 w-5" aria-hidden="true" /> },
    { key: 'whatsapp' as const, label: 'WhatsApp', icon: <MessageSquare className="h-5 w-5" aria-hidden="true" /> },
    { key: 'google_oauth' as const, label: 'Google sign-in', icon: <ShieldCheck className="h-5 w-5" aria-hidden="true" /> },
    { key: 'intake_webhook' as const, label: 'Inbound webhook', icon: <Webhook className="h-5 w-5" aria-hidden="true" /> },
  ];

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Preferences"
        title="Settings"
        description="Manage your personal AI key and review which integrations are enabled."
        icon={<KeyRound className="h-6 w-6" aria-hidden="true" />}
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card className="overflow-hidden">
          <div className="border-b border-slate-100 p-5 sm:p-6">
            <p className="eyebrow text-teal-700">Bring your own key</p>
            <h2 className="mt-1 text-lg font-semibold tracking-tight text-navy-900">Personal AI key</h2>
            <p className="mt-1 text-sm leading-relaxed text-slate-500">
              AI assistance uses a key you provide. The secret is sent directly to the backend and is never stored in this browser.
            </p>
          </div>

          <div className="space-y-5 p-5 sm:p-6">
            {keysError ? <ErrorState compact title="Status unavailable" message={keysError} onRetry={() => void loadKeys()} /> : null}

            {loadingKeys ? (
              <div className="space-y-3" role="status" aria-label="Loading API key status">
                <Skeleton className="h-3 w-32" />
                <Skeleton className="h-11 w-full" />
                <Skeleton className="h-3 w-48" />
              </div>
            ) : null}

            {!loadingKeys && !keysError && !primary ? (
              <EmptyState
                title="No key configured"
                message="Add your own key to enable grounded AI assistance. Validation results and usage metadata will appear here afterwards."
                icon={<Bot className="h-5 w-5" aria-hidden="true" />}
              />
            ) : null}

            {!loadingKeys && primary ? (
              <dl className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-2">
                <StatusRow label="Provider" value={primary.provider} />
                <StatusRow
                  label="Status"
                  value={<StatusPill status={primary.configured ? (primary.is_valid ? 'completed' : 'planned') : 'closed'} label={primary.configured ? (primary.is_valid === null ? 'Configured' : primary.is_valid ? 'Validated' : 'Invalid') : 'Not configured'} />}
                />
                <StatusRow label="Key hint" value={primary.key_hint ?? 'Hidden'} />
                <StatusRow label="Validated at" value={formatDateTime(primary.validated_at)} />
                <StatusRow label="Last used" value={formatDateTime(primary.last_used_at)} />
                <StatusRow label="Updated" value={formatDateTime(primary.updated_at)} />
              </dl>
            ) : null}

            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs leading-relaxed text-amber-900">
              <p className="font-semibold">Why is a personal key required?</p>
              <p className="mt-1">
                No shared key is used by default. If AI assistance reports that a key is missing, add or validate one here.
              </p>
              {user ? (
                <Link href={ROLE_HOME[user.role]} className="mt-2 inline-flex items-center gap-1.5 font-semibold text-teal-800 underline underline-offset-2 hover:text-teal-900">
                  <Bot className="h-3.5 w-3.5" aria-hidden="true" /> Go to your AI-enabled workspace
                </Link>
              ) : null}
            </div>

            <div className="space-y-4 border-t border-slate-100 pt-5">
              <div>
                <label htmlFor="api-key" className="field-label">API key</label>
                <PasswordInput
                  id="api-key"
                  value={keyValue}
                  onChange={(event) => {
                    setKeyValue(event.target.value);
                    setFormError('');
                  }}
                  autoComplete="off"
                  spellCheck={false}
                  placeholder={primary?.configured ? 'Replace with a new key' : 'Paste your key'}
                  aria-describedby="api-key-help"
                />
                <p id="api-key-help" className="mt-1.5 text-xs text-slate-500">
                  The full key is never displayed again. Only a masked hint is shown above.
                </p>
              </div>

              {formError ? <ErrorState compact title="Request failed" message={formError} /> : null}

              <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                <Button variant="teal" onClick={() => void handleSave()} disabled={saving || !keyValue.trim()}>
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <KeyRound className="h-4 w-4" aria-hidden="true" />}
                  {primary?.configured ? 'Replace key' : 'Add key'}
                </Button>
                <Button variant="outline" onClick={() => void handleValidate()} disabled={validating || !primary?.configured}>
                  {validating ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <RefreshCw className="h-4 w-4" aria-hidden="true" />}
                  Validate key
                </Button>
                <Button variant="ghost" className="text-rose-600 hover:bg-rose-50 hover:text-rose-700" onClick={() => setConfirmOpen(true)} disabled={!primary?.configured}>
                  <Trash2 className="h-4 w-4" aria-hidden="true" /> Remove
                </Button>
              </div>
            </div>
          </div>
        </Card>

        <div className="space-y-6">
          <Card className="overflow-hidden">
            <div className="border-b border-slate-100 p-5 sm:p-6">
              <p className="eyebrow text-teal-700">Connectivity</p>
              <h2 className="mt-1 text-lg font-semibold tracking-tight text-navy-900">Integration status</h2>
              <p className="mt-1 text-sm leading-relaxed text-slate-500">
                Configuration flags only. Secrets and addresses are never included.
              </p>
            </div>
            <div className="p-5 sm:p-6">
              {integrationsError ? <ErrorState compact title="Status unavailable" message={integrationsError} onRetry={() => void loadIntegrations()} /> : null}
              {loadingIntegrations ? (
                <div className="grid gap-3 sm:grid-cols-2" role="status" aria-label="Loading integration status">
                  {Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-20" />)}
                </div>
              ) : null}
              {!loadingIntegrations && !integrationsError ? (
                <ul className="grid gap-3 sm:grid-cols-2">
                  {integrationCards.map((item) => {
                    const enabled = Boolean(integrations?.[item.key]);
                    return (
                      <li key={item.key} className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
                        <div className="flex items-start justify-between gap-2">
                          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-50 text-teal-700 ring-1 ring-teal-100">
                            {item.icon}
                          </span>
                          <StatusPill status={enabled ? 'healthy' : 'closed'} label={enabled ? 'Enabled' : 'Not configured'} />
                        </div>
                        <p className="mt-3 text-sm font-semibold text-navy-900">{item.label}</p>
                      </li>
                    );
                  })}
                </ul>
              ) : null}
            </div>
          </Card>

          <Card className="border-teal-200 bg-teal-50/50 p-5 sm:p-6">
            <div className="flex items-start gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-teal-700 shadow-sm ring-1 ring-teal-200">
                <PlugZap className="h-5 w-5" aria-hidden="true" />
              </span>
              <div>
                <h3 className="text-sm font-semibold text-navy-900">Secure by design</h3>
                <p className="mt-1 text-xs leading-relaxed text-slate-600">
                  Your key is encrypted at rest by the backend and isolated to your account. Deleting it removes it from future AI runs.
                </p>
                <p className="mt-2 flex items-center gap-1.5 text-[11px] font-medium text-teal-800">
                  <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> No key material is written to browser storage.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove your personal key?</DialogTitle>
            <DialogDescription>
              AI assistance will stop working for your account until you add a new key. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button variant="outline" onClick={() => setConfirmOpen(false)} disabled={deleting}>Cancel</Button>
            <Button variant="danger" onClick={() => void handleDelete()} disabled={deleting}>
              {deleting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Trash2 className="h-4 w-4" aria-hidden="true" />}
              Remove key
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
