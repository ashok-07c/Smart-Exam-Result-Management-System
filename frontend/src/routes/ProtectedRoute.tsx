import type { ReactNode } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { LoadingState } from '@/components/ui';
import { useAuth } from '@/providers/auth-context';
import { homeForRole } from '@/lib/roles';
import type { Role } from '@/lib/types';

function SessionLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <LoadingState label="Preparing your workspace…" />
    </div>
  );
}

export function ProtectedRoute({ roles, children }: { roles?: Role[]; children?: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <SessionLoading />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (user.must_change_password) return <Navigate to="/change-password" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/unauthorized" replace />;
  return <AppShell>{children ?? <Outlet />}</AppShell>;
}

/** Standalone route for the mandatory first-login password change. */
export function PasswordChangeRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <SessionLoading />;
  if (!user) return <Navigate to="/login" replace />;
  if (!user.must_change_password) return <Navigate to={homeForRole(user.role)} replace />;
  return <>{children}</>;
}

export function GuestRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingState label="Checking session…" />;
  if (user) {
    return <Navigate to={user.must_change_password ? '/change-password' : homeForRole(user.role)} replace />;
  }
  return <>{children}</>;
}
