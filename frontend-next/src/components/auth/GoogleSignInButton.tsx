'use client';

import { useEffect, useRef, useState } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import { ErrorState } from '@/components/common/ErrorState';

interface GoogleCredentialResponse {
  credential: string;
}

interface GoogleIdApi {
  initialize: (options: {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void;
    ux_mode?: 'popup' | 'redirect';
  }) => void;
  renderButton: (
    parent: HTMLElement,
    options: { theme?: 'outline' | 'filled_blue' | 'filled_black'; size?: 'small' | 'medium' | 'large'; width?: number },
  ) => void;
}

declare global {
  interface Window {
    google?: { accounts: { id: GoogleIdApi } };
  }
}

function loadGoogleIdentityScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();

  const existing = document.getElementById('google-identity-services');
  if (existing instanceof HTMLScriptElement) {
    return new Promise((resolve, reject) => {
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error('Google sign-in script failed to load.')), { once: true });
    });
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.id = 'google-identity-services';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Google sign-in script failed to load.'));
    document.head.appendChild(script);
  });
}

interface GoogleSignInButtonProps {
  clientId: string;
  onCredential: (credential: string) => Promise<void>;
}

/** Official Google Identity Services button; rendered only when a client ID is configured. */
export function GoogleSignInButton({ clientId, onCredential }: GoogleSignInButtonProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const callbackRef = useRef(onCredential);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState('');

  useEffect(() => {
    callbackRef.current = onCredential;
  }, [onCredential]);

  useEffect(() => {
    if (!clientId) return;
    let cancelled = false;
    let observer: ResizeObserver | null = null;
    let lastWidth = 0;

    const render = () => {
      const container = containerRef.current;
      if (!container || !window.google?.accounts?.id) return;
      const width = Math.max(220, Math.min(320, container.clientWidth || 280));
      if (width === lastWidth && container.childElementCount > 0) return;
      lastWidth = width;
      container.replaceChildren();
      window.google.accounts.id.initialize({
        client_id: clientId,
        ux_mode: 'popup',
        callback: (response) => {
          if (response?.credential) void callbackRef.current(response.credential);
        },
      });
      window.google.accounts.id.renderButton(container, {
        theme: 'outline',
        size: 'large',
        width,
      });
      setStatus('ready');
    };

    loadGoogleIdentityScript()
      .then(() => {
        if (cancelled) return;
        render();
        if (typeof ResizeObserver !== 'undefined' && containerRef.current) {
          observer = new ResizeObserver(render);
          observer.observe(containerRef.current);
        }
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        setError(cause instanceof Error ? cause.message : 'Google sign-in is unavailable.');
        setStatus('error');
      });

    return () => {
      cancelled = true;
      observer?.disconnect();
    };
  }, [clientId]);

  if (!clientId) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3" aria-hidden="true">
        <span className="h-px flex-1 bg-slate-200" />
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">or</span>
        <span className="h-px flex-1 bg-slate-200" />
      </div>
      {status === 'loading' ? (
        <p className="flex h-11 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Preparing Google sign-in…
        </p>
      ) : null}
      {status === 'error' ? (
        <ErrorState
          compact
          title="Google sign-in unavailable"
          message={error || 'The Google Identity Services script could not be loaded.'}
        />
      ) : null}
      <div ref={containerRef} className="flex min-h-11 w-full max-w-full justify-center overflow-hidden" aria-label="Sign in with Google" />
      <p className="flex items-start gap-1.5 text-[11px] leading-relaxed text-slate-500">
        <AlertCircle className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        Google sign-in is available only when your institution has configured it.
      </p>
    </div>
  );
}
