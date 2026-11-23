'use client';

import { useEffect, useRef } from 'react';
import { ticketsApi } from '@/lib/api/endpoints';
import type { TicketStatusSnapshot } from '@/lib/api/types';

interface PollingOptions {
  enabled?: boolean;
  intervalMs?: number;
}

/**
 * FR-06: poll the lightweight status snapshot and notify only on real changes.
 * Transient failures are ignored so a provider blip does not break the ticket UI;
 * the next interval retries automatically.
 */
export function useTicketStatusPolling(
  ticketId: string,
  onUpdate: (snapshot: TicketStatusSnapshot) => void,
  { enabled = true, intervalMs = 15_000 }: PollingOptions = {},
): void {
  const callbackRef = useRef(onUpdate);
  useEffect(() => {
    callbackRef.current = onUpdate;
  }, [onUpdate]);

  useEffect(() => {
    if (!enabled) return;

    const controller = new AbortController();
    let active = true;
    let lastKey = '';
    let inFlight = false;

    const poll = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const snapshot = await ticketsApi.statusSnapshot(ticketId, controller.signal);
        const key = JSON.stringify(snapshot);
        if (!active || key === lastKey) return;
        lastKey = key;
        callbackRef.current(snapshot);
      } catch {
        // Polling is best-effort; in-page actions still refresh explicitly.
      } finally {
        inFlight = false;
      }
    };

    void poll();
    const timer = window.setInterval(() => void poll(), intervalMs);

    return () => {
      active = false;
      window.clearInterval(timer);
      controller.abort();
    };
  }, [ticketId, enabled, intervalMs]);
}
