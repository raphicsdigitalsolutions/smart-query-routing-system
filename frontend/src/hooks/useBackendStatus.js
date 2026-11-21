import { useCallback, useEffect, useState } from 'react';
import { getHealth } from '../services/api';

/** Polls the backend once on mount and exposes a manual retry. */
export function useBackendStatus() {
  const [state, setState] = useState({
    status: 'checking',
    data: null,
    error: null,
  });

  const refresh = useCallback(async () => {
    setState({ status: 'checking', data: null, error: null });
    try {
      const data = await getHealth();
      setState({ status: 'online', data, error: null });
    } catch (error) {
      setState({
        status: 'offline',
        data: null,
        error: error?.message || 'Unable to reach the backend.',
      });
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { ...state, refresh };
}

export default useBackendStatus;
