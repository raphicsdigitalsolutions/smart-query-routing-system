'use client';

import { useCallback, useEffect, useState } from 'react';
import { getHealth } from '@/lib/api/endpoints';
import { getApiErrorMessage } from '@/lib/api/errors';
import type { HealthResponse } from '@/lib/api/types';

export function useBackendStatus() {
  const [status, setStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => setRefreshKey((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setStatus('checking');
    setError('');

    getHealth(controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        setData(result);
        setStatus('online');
      })
      .catch((cause) => {
        if (controller.signal.aborted) return;
        setError(getApiErrorMessage(cause, 'Unable to reach the backend.'));
        setStatus('offline');
      });

    return () => controller.abort();
  }, [refreshKey]);

  return { status, data, error, refresh };
}
