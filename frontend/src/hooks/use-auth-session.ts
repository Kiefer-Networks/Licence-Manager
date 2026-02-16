'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { api, CurrentUserInfo } from '@/lib/api';

export interface UseAuthSessionReturn {
  user: CurrentUserInfo | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
  hasAnyPermission: (...permissions: string[]) => boolean;
  hasAllPermissions: (...permissions: string[]) => boolean;
  hasRole: (role: string) => boolean;
  isSuperAdmin: boolean;
  isAdmin: boolean;
}

/**
 * Custom hook that encapsulates all auth session API calls and business logic.
 * Used internally by AuthProvider to manage authentication state.
 */
export function useAuthSession(): UseAuthSessionReturn {
  const [user, setUser] = useState<CurrentUserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const refreshUser = useCallback(async () => {
    try {
      // With httpOnly cookies, we verify auth by calling the /me endpoint
      const userInfo = await api.getCurrentUser();
      setUser(userInfo);
      // Ensure we have a CSRF token for subsequent requests
      await api.refreshCsrfToken();
    } catch {
      // Not authenticated or session expired
      setUser(null);
      api.clearAuth();
    }
  }, []);

  useEffect(() => {
    const initAuth = async () => {
      setIsLoading(true);
      await refreshUser();
      setIsLoading(false);
    };

    initAuth();
  }, [refreshUser]);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // Ignore errors during logout
    } finally {
      setUser(null);
      api.clearAuth();
      router.push('/auth/signin?logout=true');
    }
  }, [router]);

  const hasPermission = useCallback((permission: string): boolean => {
    if (!user) return false;
    if (user.is_superadmin) return true;
    return user.permissions.includes(permission);
  }, [user]);

  const hasAnyPermission = useCallback((...permissions: string[]): boolean => {
    if (!user) return false;
    if (user.is_superadmin) return true;
    return permissions.some(p => user.permissions.includes(p));
  }, [user]);

  const hasAllPermissions = useCallback((...permissions: string[]): boolean => {
    if (!user) return false;
    if (user.is_superadmin) return true;
    return permissions.every(p => user.permissions.includes(p));
  }, [user]);

  const hasRole = useCallback((role: string): boolean => {
    if (!user) return false;
    return user.roles.includes(role);
  }, [user]);

  const isSuperAdmin = user?.is_superadmin ?? false;
  const isAdmin = hasRole('admin') || isSuperAdmin;

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
    logout,
    refreshUser,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    hasRole,
    isSuperAdmin,
    isAdmin,
  };
}
