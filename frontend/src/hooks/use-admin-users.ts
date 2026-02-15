'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth, Permissions } from '@/components/auth-provider';
import { api, AdminUser, Role } from '@/lib/api';

/**
 * Translation functions required by the useAdminUsers hook.
 */
interface AdminUsersTranslations {
  t: (key: string, params?: Record<string, string | number>) => string;
  tCommon: (key: string) => string;
}

/**
 * Return type for the useAdminUsers hook.
 */
export interface UseAdminUsersReturn {
  // Data
  users: AdminUser[];
  roles: Role[];
  isLoading: boolean;
  error: string;
  setError: (v: string) => void;
  search: string;
  setSearch: (v: string) => void;

  // Auth
  currentUser: ReturnType<typeof useAuth>['user'];
  authLoading: boolean;
  canCreate: boolean;
  canUpdate: boolean;
  canDelete: boolean;

  // Dialog states
  createDialogOpen: boolean;
  setCreateDialogOpen: (v: boolean) => void;
  editDialogOpen: boolean;
  setEditDialogOpen: (v: boolean) => void;
  deleteDialogOpen: boolean;
  setDeleteDialogOpen: (v: boolean) => void;
  selectedUser: AdminUser | null;

  // Form states
  formData: {
    email: string;
    name: string;
    language: string;
    role_codes: string[];
    is_active: boolean;
  };
  setFormData: (v: {
    email: string;
    name: string;
    language: string;
    role_codes: string[];
    is_active: boolean;
  }) => void;
  formErrors: string[];
  isSubmitting: boolean;

  // Handlers
  loadData: () => Promise<void>;
  handleSearch: () => Promise<void>;
  openCreateDialog: () => void;
  openEditDialog: (user: AdminUser) => void;
  openDeleteDialog: (user: AdminUser) => void;
  handleCreateUser: () => Promise<void>;
  handleUpdateUser: () => Promise<void>;
  handleDeleteUser: () => Promise<void>;
  toggleRole: (roleCode: string) => void;
}

/**
 * Custom hook that encapsulates all business logic for the Admin Users page.
 * Manages user list, CRUD operations, search, and dialog state.
 */
export function useAdminUsers(
  { t, tCommon }: AdminUsersTranslations,
): UseAdminUsersReturn {
  const router = useRouter();
  const { hasPermission, isLoading: authLoading, user: currentUser } = useAuth();

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);

  // Form states
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    language: 'en',
    role_codes: [] as string[],
    is_active: true,
  });
  const [formErrors, setFormErrors] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Note: These client-side permission checks are for UX only (hiding buttons/UI).
  // Server-side enforcement via require_permission() is the authoritative check.
  // All API endpoints validate permissions independently.
  const canCreate = hasPermission(Permissions.ADMIN_USERS_CREATE);
  const canUpdate = hasPermission(Permissions.ADMIN_USERS_UPDATE);
  const canDelete = hasPermission(Permissions.ADMIN_USERS_DELETE);

  useEffect(() => {
    if (!authLoading && !hasPermission(Permissions.ADMIN_USERS_VIEW)) {
      router.push('/unauthorized');
      return;
    }
  }, [authLoading, hasPermission, router]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [usersResponse, rolesResponse] = await Promise.all([
        api.getAdminUsers(),
        api.getRoles(),
      ]);
      setUsers(usersResponse.items);
      setRoles(rolesResponse.items);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : tCommon('operationFailed');
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async () => {
    setIsLoading(true);
    try {
      const response = await api.getAdminUsers({ search });
      setUsers(response.items);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('searchFailed');
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const openCreateDialog = () => {
    setFormData({ email: '', name: '', language: 'en', role_codes: [], is_active: true });
    setFormErrors([]);
    setCreateDialogOpen(true);
  };

  const openEditDialog = (user: AdminUser) => {
    setSelectedUser(user);
    setFormData({
      email: user.email,
      name: user.name || '',
      language: user.language || 'en',
      role_codes: user.roles, // Backend returns role codes directly
      is_active: user.is_active,
    });
    setFormErrors([]);
    setEditDialogOpen(true);
  };

  const openDeleteDialog = (user: AdminUser) => {
    setSelectedUser(user);
    setDeleteDialogOpen(true);
  };

  const handleCreateUser = async () => {
    setFormErrors([]);
    setIsSubmitting(true);

    try {
      // Convert role codes to role IDs for the API
      const roleIds = formData.role_codes
        .map(code => roles.find(r => r.code === code)?.id)
        .filter((id): id is string => !!id);

      await api.createAdminUser({
        email: formData.email,
        name: formData.name || undefined,
        language: formData.language,
        role_ids: roleIds,
      });

      setCreateDialogOpen(false);
      await loadData();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('failedToCreate');
      setFormErrors([errorMessage]);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateUser = async () => {
    if (!selectedUser) return;
    setFormErrors([]);
    setIsSubmitting(true);

    try {
      // Convert role codes to role IDs for the API
      const roleIds = formData.role_codes
        .map(code => roles.find(r => r.code === code)?.id)
        .filter((id): id is string => !!id);

      await api.updateAdminUser(selectedUser.id, {
        email: formData.email !== selectedUser.email ? formData.email : undefined,
        name: formData.name || undefined,
        role_ids: roleIds,
        is_active: formData.is_active !== selectedUser.is_active ? formData.is_active : undefined,
      });
      setEditDialogOpen(false);
      await loadData();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('failedToUpdate');
      setFormErrors([errorMessage]);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!selectedUser) return;
    setIsSubmitting(true);

    try {
      await api.deleteAdminUser(selectedUser.id);
      setDeleteDialogOpen(false);
      await loadData();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('failedToDelete');
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleRole = (roleCode: string) => {
    setFormData(prev => ({
      ...prev,
      role_codes: prev.role_codes.includes(roleCode)
        ? prev.role_codes.filter(code => code !== roleCode)
        : [...prev.role_codes, roleCode],
    }));
  };

  return {
    // Data
    users,
    roles,
    isLoading,
    error,
    setError,
    search,
    setSearch,

    // Auth
    currentUser,
    authLoading,
    canCreate,
    canUpdate,
    canDelete,

    // Dialog states
    createDialogOpen,
    setCreateDialogOpen,
    editDialogOpen,
    setEditDialogOpen,
    deleteDialogOpen,
    setDeleteDialogOpen,
    selectedUser,

    // Form states
    formData,
    setFormData,
    formErrors,
    isSubmitting,

    // Handlers
    loadData,
    handleSearch,
    openCreateDialog,
    openEditDialog,
    openDeleteDialog,
    handleCreateUser,
    handleUpdateUser,
    handleDeleteUser,
    toggleRole,
  };
}
