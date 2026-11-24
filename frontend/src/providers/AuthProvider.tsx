import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api } from '@/lib/api';
import type { AuthUser, LoginData, Role } from '@/lib/types';
import { AuthContext, type AuthContextValue } from './auth-context';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => api.isAuthenticated() ? api.getUser<AuthUser>() : null);
  const [loading, setLoading] = useState(true);

  const clear = useCallback(() => {
    api.clearAuth();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!api.isAuthenticated()) return;
    try {
      const envelope = await api.get<AuthUser>('/auth/me');
      api.setUser(envelope.data);
      setUser(envelope.data);
    } catch {
      clear();
    }
  }, [clear]);

  useEffect(() => {
    const unauthorized = () => setUser(null);
    window.addEventListener('auth:unauthorized', unauthorized);
    const bootstrap = async () => {
      if (api.isAuthenticated()) await refreshUser();
      setLoading(false);
    };
    void bootstrap();
    return () => window.removeEventListener('auth:unauthorized', unauthorized);
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    const envelope = await api.post<LoginData>('/auth/login', { email, password });
    api.setToken(envelope.data.access_token);
    api.setUser(envelope.data.user);
    setUser(envelope.data.user);
    return envelope.data.user;
  }, []);

  const changePassword = useCallback(async (currentPassword: string, newPassword: string, confirmPassword: string) => {
    await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    });
    await refreshUser();
  }, [refreshUser]);

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout');
    } finally {
      clear();
    }
  }, [clear]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login,
      changePassword,
      logout,
      refreshUser,
      hasRole: (...roles: Role[]) => Boolean(user && roles.includes(user.role)),
    }),
    [user, loading, login, changePassword, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
