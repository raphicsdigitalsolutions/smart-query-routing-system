import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  clearAuthToken,
  getAuthToken,
  getMe,
  login as apiLogin,
  registerStudent,
} from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState('loading');

  const finishLogin = useCallback((data) => {
    setUser(data.user);
    setStatus('authenticated');
  }, []);

  const logout = useCallback(() => {
    clearAuthToken();
    setUser(null);
    setStatus('guest');
  }, []);

  useEffect(() => {
    let active = true;
    if (!getAuthToken()) {
      setStatus('guest');
      return undefined;
    }
    getMe()
      .then((profile) => {
        if (active) {
          setUser(profile);
          setStatus('authenticated');
        }
      })
      .catch(() => {
        if (active) logout();
      });
    return () => {
      active = false;
    };
  }, [logout]);

  useEffect(() => {
    window.addEventListener('auth:unauthorized', logout);
    return () => window.removeEventListener('auth:unauthorized', logout);
  }, [logout]);

  const login = useCallback(
    async (email, password) => {
      const data = await apiLogin({ email, password });
      finishLogin(data);
      return data.user;
    },
    [finishLogin],
  );

  const register = useCallback(
    async (payload) => {
      await registerStudent(payload);
      // New accounts are students; log them in with the just-created credentials.
      return login(payload.email, payload.password);
    },
    [login],
  );

  const hasRole = useCallback(
    (...roles) => Boolean(user && roles.includes(user.role)),
    [user],
  );

  const value = useMemo(
    () => ({ user, status, isAuthenticated: status === 'authenticated', login, register, logout, hasRole }),
    [user, status, login, register, logout, hasRole],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside an AuthProvider');
  return context;
}

export default AuthContext;
