'use client';

import { useCallback, useEffect, useState } from 'react';
import { ticketsApi, type TicketQuery } from '@/lib/api/endpoints';
import { getApiErrorMessage } from '@/lib/api/errors';
import type { TicketResponse } from '@/lib/api/types';

export function useTickets(params: TicketQuery = {}) {
  const [items, setItems] = useState<TicketResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const key = JSON.stringify(params);

  const refresh = useCallback(() => setRefreshKey((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');

    ticketsApi.list(JSON.parse(key) as TicketQuery, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        setItems(result.items ?? []);
        setTotal(result.total ?? 0);
      })
      .catch((cause) => {
        if (controller.signal.aborted) return;
        setError(getApiErrorMessage(cause, 'Unable to load tickets.'));
        setItems([]);
        setTotal(0);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [key, refreshKey]);

  return { items, total, loading, error, refresh };
}
