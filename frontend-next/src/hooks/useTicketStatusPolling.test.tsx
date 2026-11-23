import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ticketsApi } from '@/lib/api/endpoints';
import type { TicketStatusSnapshot } from '@/lib/api/types';
import { useTicketStatusPolling } from './useTicketStatusPolling';

vi.mock('@/lib/api/endpoints', () => ({
  ticketsApi: { statusSnapshot: vi.fn() },
}));

const statusSnapshot = vi.mocked(ticketsApi.statusSnapshot);

function snapshot(status: TicketStatusSnapshot['status']): TicketStatusSnapshot {
  return {
    id: 42,
    public_reference: 'TKT-000042',
    status,
    assigned_to: null,
    is_escalated: false,
    updated_at: `2026-11-22T12:00:00.000Z`,
  };
}

describe('useTicketStatusPolling', () => {
  beforeEach(() => {
    statusSnapshot.mockReset();
  });

  it('reports only changed snapshots', async () => {
    statusSnapshot
      .mockResolvedValueOnce(snapshot('new'))
      .mockResolvedValueOnce(snapshot('new'))
      .mockResolvedValue(snapshot('in_progress'));
    const onUpdate = vi.fn();

    renderHook(() => useTicketStatusPolling('42', onUpdate, { intervalMs: 25 }));

    await waitFor(() => expect(statusSnapshot).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(onUpdate).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(statusSnapshot.mock.calls.length).toBeGreaterThanOrEqual(3), {
      timeout: 1500,
    });
    await waitFor(() => expect(onUpdate).toHaveBeenCalledTimes(2));
    expect(onUpdate.mock.calls[1]?.[0].status).toBe('in_progress');
  });

  it('does not poll when disabled', async () => {
    renderHook(() =>
      useTicketStatusPolling('42', vi.fn(), { enabled: false, intervalMs: 25 }),
    );
    await new Promise((resolve) => setTimeout(resolve, 60));
    expect(statusSnapshot).not.toHaveBeenCalled();
  });

  it('retries after a transient polling error', async () => {
    statusSnapshot
      .mockRejectedValueOnce(new Error('network offline'))
      .mockResolvedValue(snapshot('assigned'));
    const onUpdate = vi.fn();

    renderHook(() => useTicketStatusPolling('42', onUpdate, { intervalMs: 25 }));

    await waitFor(() => expect(onUpdate).toHaveBeenCalledTimes(1), { timeout: 1500 });
    expect(onUpdate.mock.calls[0]?.[0].status).toBe('assigned');
  });
});
