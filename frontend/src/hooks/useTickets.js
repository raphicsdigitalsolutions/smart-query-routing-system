import { useCallback, useEffect, useState } from 'react';
import { getApiErrorMessage, listTickets } from '../services/api';

/** Loads the current user's visible tickets with filters and pagination. */
export function useTickets(params = {}) {
  const [state, setState] = useState({ items: [], total: 0, loading: true, error: '' });
  const [refreshKey, setRefreshKey] = useState(0);
  const key = JSON.stringify(params);

  useEffect(() => {
    let active = true;
    setState((prev) => ({ ...prev, loading: true, error: '' }));
    listTickets(JSON.parse(key))
      .then((data) => {
        if (active) setState({ items: data.items || [], total: data.total || 0, loading: false, error: '' });
      })
      .catch((err) => {
        if (active) setState({ items: [], total: 0, loading: false, error: getApiErrorMessage(err) });
      });
    return () => { active = false; };
  }, [key, refreshKey]);

  const refresh = useCallback(() => setRefreshKey((value) => value + 1), []);
  return { ...state, refresh };
}

export default useTickets;
