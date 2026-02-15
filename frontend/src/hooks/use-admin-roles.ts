'use client';

import { useState, useEffect } from 'react';
import { api, Role, PermissionsByCategory, Permission } from '@/lib/api';

/**
 * Form data for creating/editing a role.
 */
export interface RoleFormData {
  code: string;
  name: string;
  description: string;
  permission_ids: string[];
}

/**
 * Return type for the useAdminRoles hook.
 */
export interface UseAdminRolesReturn {
  // Data
  roles: Role[];
  permissionsByCategory: PermissionsByCategory;

  // Loading & error
  isLoading: boolean;
  error: string;
  setError: (error: string) => void;

  // Dialog states
  createDialogOpen: boolean;
  setCreateDialogOpen: (open: boolean) => void;
  editDialogOpen: boolean;
  setEditDialogOpen: (open: boolean) => void;
  deleteDialogOpen: boolean;
  setDeleteDialogOpen: (open: boolean) => void;
  viewDialogOpen: boolean;
  setViewDialogOpen: (open: boolean) => void;
  selectedRole: Role | null;

  // Form
  formData: RoleFormData;
  setFormData: React.Dispatch<React.SetStateAction<RoleFormData>>;
  formErrors: string[];
  isSubmitting: boolean;

  // Actions
  openCreateDialog: () => void;
  openEditDialog: (role: Role) => void;
  openViewDialog: (role: Role) => void;
  openDeleteDialog: (role: Role) => void;
  handleCreateRole: () => Promise<void>;
  handleUpdateRole: () => Promise<void>;
  handleDeleteRole: () => Promise<void>;
  togglePermission: (permissionId: string) => void;
  toggleCategoryPermissions: (category: string) => void;
  selectAllPermissions: () => void;
  clearAllPermissions: () => void;
}

/**
 * Custom hook that encapsulates all business logic for the Admin Roles page.
 * Manages roles CRUD, permission selection, and dialog states.
 */
export function useAdminRoles(
  t: (key: string, params?: Record<string, string | number>) => string,
  tCommon: (key: string) => string,
): UseAdminRolesReturn {
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissionsByCategory, setPermissionsByCategory] = useState<PermissionsByCategory>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);

  // Form states
  const [formData, setFormData] = useState<RoleFormData>({
    code: '',
    name: '',
    description: '',
    permission_ids: [],
  });
  const [formErrors, setFormErrors] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [rolesResponse, permissionsResponse] = await Promise.all([
        api.getRoles(),
        api.getPermissionsByCategory(),
      ]);
      setRoles(rolesResponse.items);
      setPermissionsByCategory(permissionsResponse);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : tCommon('operationFailed');
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const getAllPermissionIds = (): string[] => {
    return Object.values(permissionsByCategory).flatMap(perms => perms.map(p => p.id));
  };

  const openCreateDialog = () => {
    setFormData({ code: '', name: '', description: '', permission_ids: [] });
    setFormErrors([]);
    setCreateDialogOpen(true);
  };

  const openEditDialog = (role: Role) => {
    setSelectedRole(role);
    const allPermissions = Object.values(permissionsByCategory).flat();
    const permissionIds = role.permissions
      .map(code => allPermissions.find(p => p.code === code)?.id)
      .filter((id): id is string => !!id);

    setFormData({
      code: role.code,
      name: role.name,
      description: role.description || '',
      permission_ids: permissionIds,
    });
    setFormErrors([]);
    setEditDialogOpen(true);
  };

  const openViewDialog = (role: Role) => {
    setSelectedRole(role);
    setViewDialogOpen(true);
  };

  const openDeleteDialog = (role: Role) => {
    setSelectedRole(role);
    setDeleteDialogOpen(true);
  };

  const handleCreateRole = async () => {
    setFormErrors([]);
    setIsSubmitting(true);

    try {
      await api.createRole({
        code: formData.code,
        name: formData.name,
        description: formData.description || undefined,
        permission_ids: formData.permission_ids,
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

  const handleUpdateRole = async () => {
    if (!selectedRole) return;
    setFormErrors([]);
    setIsSubmitting(true);

    try {
      await api.updateRole(selectedRole.id, {
        name: formData.name,
        description: formData.description || undefined,
        permission_ids: formData.permission_ids,
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

  const handleDeleteRole = async () => {
    if (!selectedRole) return;
    setIsSubmitting(true);

    try {
      await api.deleteRole(selectedRole.id);
      setDeleteDialogOpen(false);
      await loadData();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('failedToDelete');
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const togglePermission = (permissionId: string) => {
    setFormData(prev => ({
      ...prev,
      permission_ids: prev.permission_ids.includes(permissionId)
        ? prev.permission_ids.filter(id => id !== permissionId)
        : [...prev.permission_ids, permissionId],
    }));
  };

  const toggleCategoryPermissions = (category: string) => {
    const categoryPermissionIds = permissionsByCategory[category]?.map(p => p.id) || [];
    const allSelected = categoryPermissionIds.every(id => formData.permission_ids.includes(id));

    setFormData(prev => ({
      ...prev,
      permission_ids: allSelected
        ? prev.permission_ids.filter(id => !categoryPermissionIds.includes(id))
        : Array.from(new Set([...prev.permission_ids, ...categoryPermissionIds])),
    }));
  };

  const selectAllPermissions = () => {
    setFormData(prev => ({
      ...prev,
      permission_ids: getAllPermissionIds(),
    }));
  };

  const clearAllPermissions = () => {
    setFormData(prev => ({
      ...prev,
      permission_ids: [],
    }));
  };

  return {
    // Data
    roles,
    permissionsByCategory,

    // Loading & error
    isLoading,
    error,
    setError,

    // Dialog states
    createDialogOpen,
    setCreateDialogOpen,
    editDialogOpen,
    setEditDialogOpen,
    deleteDialogOpen,
    setDeleteDialogOpen,
    viewDialogOpen,
    setViewDialogOpen,
    selectedRole,

    // Form
    formData,
    setFormData,
    formErrors,
    isSubmitting,

    // Actions
    openCreateDialog,
    openEditDialog,
    openViewDialog,
    openDeleteDialog,
    handleCreateRole,
    handleUpdateRole,
    handleDeleteRole,
    togglePermission,
    toggleCategoryPermissions,
    selectAllPermissions,
    clearAllPermissions,
  };
}
