'use client';

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { api, CurrentUserInfo } from '@/lib/api';

export interface TotpRequiredResult {
  totpRequired: true;
}

export interface LoginSuccessResult {
  totpRequired: false;
}

export type LoginResult = TotpRequiredResult | LoginSuccessResult;

interface AuthContextType {
  user: CurrentUserInfo | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string, totpCode?: string) => Promise<LoginResult>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
  hasAnyPermission: (...permissions: string[]) => boolean;
  hasAllPermissions: (...permissions: string[]) => boolean;
  hasRole: (role: string) => boolean;
  isSuperAdmin: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const refreshUser = useCallback(async () => {
    try {
      // With httpOnly cookies, we verify auth by calling the /me endpoint
      // The server will read the token from the httpOnly cookie
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

  const login = useCallback(async (email: string, password: string, totpCode?: string): Promise<LoginResult> => {
    // Clear any existing session state before logging in (only on first attempt, not TOTP verification)
    // This ensures old tokens/state don't persist across logins
    if (!totpCode) {
      api.clearAuth();
    }

    // Get CSRF token first for the login request
    await api.refreshCsrfToken();
    const response = await api.login(email, password, totpCode);

    // Check if TOTP verification is required
    if (response.totp_required) {
      return { totpRequired: true };
    }

    // Login successful - fetch user info to verify authentication worked
    // Note: Cookies are set by the server response, should be available immediately
    try {
      const userInfo = await api.getCurrentUser();
      setUser(userInfo);
      // Refresh CSRF token after login (new session)
      await api.refreshCsrfToken();
    } catch (error) {
      // If we can't fetch user info after successful login, something is wrong
      // Clear any partial state and report the error
      setUser(null);
      api.clearAuth();
      throw new Error('Login succeeded but failed to establish session. Please try again.');
    }

    router.push('/dashboard');
    return { totpRequired: false };
  }, [router]);

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

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshUser,
        hasPermission,
        hasAnyPermission,
        hasAllPermissions,
        hasRole,
        isSuperAdmin,
        isAdmin,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Permission constants matching the backend - use dot notation
export const Permissions = {
  // Dashboard
  DASHBOARD_VIEW: 'dashboard.view',

  // Users (Admin user management)
  ADMIN_USERS_VIEW: 'users.view',
  ADMIN_USERS_CREATE: 'users.create',
  ADMIN_USERS_UPDATE: 'users.edit',
  ADMIN_USERS_DELETE: 'users.delete',
  ADMIN_USERS_RESET_PASSWORD: 'users.manage_roles',

  // Roles
  ROLES_VIEW: 'roles.view',
  ROLES_CREATE: 'roles.create',
  ROLES_UPDATE: 'roles.edit',
  ROLES_DELETE: 'roles.delete',

  // Providers
  PROVIDERS_VIEW: 'providers.view',
  PROVIDERS_CREATE: 'providers.create',
  PROVIDERS_UPDATE: 'providers.edit',
  PROVIDERS_DELETE: 'providers.delete',
  PROVIDERS_SYNC: 'providers.sync',

  // Licenses
  LICENSES_VIEW: 'licenses.view',
  LICENSES_CREATE: 'licenses.create',
  LICENSES_UPDATE: 'licenses.edit',
  LICENSES_DELETE: 'licenses.delete',
  LICENSES_ASSIGN: 'licenses.assign',
  LICENSES_BULK: 'licenses.bulk_actions',

  // Employees (from HiBob)
  USERS_VIEW: 'employees.view',
  USERS_EDIT: 'employees.edit',

  // Reports
  REPORTS_VIEW: 'reports.view',
  REPORTS_EXPORT: 'reports.export',

  // Settings
  SETTINGS_VIEW: 'settings.view',
  SETTINGS_UPDATE: 'settings.edit',

  // Payment Methods
  PAYMENT_METHODS_VIEW: 'payment_methods.view',
  PAYMENT_METHODS_CREATE: 'payment_methods.create',
  PAYMENT_METHODS_UPDATE: 'payment_methods.edit',
  PAYMENT_METHODS_DELETE: 'payment_methods.delete',

  // Audit
  AUDIT_VIEW: 'audit.view',
  AUDIT_EXPORT: 'audit.export',

  // System
  SYSTEM_ADMIN: 'system.admin',
} as const;
