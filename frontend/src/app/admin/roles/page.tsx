'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth, Permissions } from '@/components/auth-provider';
import { api, Role, Permission, PermissionsByCategory, PermissionCategory } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import { AppLayout } from '@/components/layout/app-layout';

export default function AdminRolesPage() {
  const t = useTranslations('roles');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { hasPermission, isLoading: authLoading } = useAuth();

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
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: '',
    permission_ids: [] as string[],
  });
  const [formErrors, setFormErrors] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canCreate = hasPermission(Permissions.ROLES_CREATE);
  const canUpdate = hasPermission(Permissions.ROLES_UPDATE);
  const canDelete = hasPermission(Permissions.ROLES_DELETE);

  useEffect(() => {
    if (!authLoading && !hasPermission(Permissions.ROLES_VIEW)) {
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
      const [rolesResponse, permissionsResponse] = await Promise.all([
        api.getRoles(),
        api.getPermissionsByCategory(),
      ]);
      setRoles(rolesResponse.items);
      setPermissionsByCategory(permissionsResponse);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load data';
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
    // Role.permissions is an array of permission codes (strings)
    // We need to convert them to permission IDs for the form
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
      const errorMessage = err instanceof Error ? err.message : 'Failed to create role';
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
      const errorMessage = err instanceof Error ? err.message : 'Failed to update role';
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
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete role';
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

  if (authLoading || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const renderPermissionSelector = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <Label>Permissions</Label>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" onClick={selectAllPermissions}>
            Select All
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={clearAllPermissions}>
            Clear All
          </Button>
        </div>
      </div>
      <Tabs defaultValue={Object.keys(permissionsByCategory)[0]} className="w-full">
        <TabsList className="flex flex-wrap h-auto gap-1">
          {Object.keys(permissionsByCategory).map(category => {
            const categoryPerms = permissionsByCategory[category] || [];
            const selectedCount = categoryPerms.filter(p => formData.permission_ids.includes(p.id)).length;
            return (
              <TabsTrigger key={category} value={category} className="text-xs">
                {category} ({selectedCount}/{categoryPerms.length})
              </TabsTrigger>
            );
          })}
        </TabsList>
        {Object.entries(permissionsByCategory).map(([category, permissions]) => {
          const allSelected = permissions.every(p => formData.permission_ids.includes(p.id));
          return (
            <TabsContent key={category} value={category} className="mt-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2 pb-2 border-b">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={() => toggleCategoryPermissions(category)}
                    className="rounded"
                  />
                  <span className="text-sm font-medium">Select all {category}</span>
                </div>
                <div className="grid grid-cols-1 gap-2 max-h-48 overflow-y-auto">
                  {permissions.map(permission => (
                    <label
                      key={permission.id}
                      className="flex items-start gap-2 p-2 rounded hover:bg-muted cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={formData.permission_ids.includes(permission.id)}
                        onChange={() => togglePermission(permission.id)}
                        className="mt-1 rounded"
                      />
                      <div>
                        <div className="text-sm font-medium">{permission.name}</div>
                        {permission.description && (
                          <div className="text-xs text-muted-foreground">{permission.description}</div>
                        )}
                        <code className="text-xs text-muted-foreground">{permission.code}</code>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </TabsContent>
          );
        })}
      </Tabs>
    </div>
  );

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Role Management</CardTitle>
              <CardDescription>Manage roles and their permissions</CardDescription>
            </div>
            {canCreate && (
              <Button onClick={openCreateDialog}>Create Role</Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mb-4 bg-destructive/10 text-destructive text-sm p-3 rounded-md">
              {error}
              <button className="ml-2 underline" onClick={() => setError('')}>Dismiss</button>
            </div>
          )}

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Permissions</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {roles.map((role) => (
                <TableRow key={role.id}>
                  <TableCell className="font-mono text-sm">{role.code}</TableCell>
                  <TableCell className="font-medium">{role.name}</TableCell>
                  <TableCell className="max-w-xs truncate">{role.description || '-'}</TableCell>
                  <TableCell>
                    <Badge variant={role.is_system ? 'default' : 'secondary'}>
                      {role.is_system ? 'System' : 'Custom'}
                    </Badge>
                  </TableCell>
                  <TableCell>{role.priority}</TableCell>
                  <TableCell>
                    <Button
                      variant="link"
                      size="sm"
                      className="p-0 h-auto"
                      onClick={() => openViewDialog(role)}
                    >
                      {role.permissions.length} permissions
                    </Button>
                  </TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          Actions
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => openViewDialog(role)}>
                          View Permissions
                        </DropdownMenuItem>
                        {canUpdate && !role.is_system && (
                          <DropdownMenuItem onClick={() => openEditDialog(role)}>
                            Edit
                          </DropdownMenuItem>
                        )}
                        {canDelete && !role.is_system && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => openDeleteDialog(role)}
                            >
                              Delete
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
              {roles.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                    No roles found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Create Role Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Role</DialogTitle>
            <DialogDescription>Create a new custom role with specific permissions.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {formErrors.length > 0 && (
              <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                {formErrors.map((err, i) => <div key={i}>{err}</div>)}
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="create-code">Code</Label>
                <Input
                  id="create-code"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') })}
                  placeholder="e.g., license_manager"
                  required
                />
                <p className="text-xs text-muted-foreground">Lowercase letters, numbers, and underscores only.</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="create-name">Name</Label>
                <Input
                  id="create-name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., License Manager"
                  required
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-description">Description</Label>
              <Textarea
                id="create-description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Describe what this role is for..."
                rows={2}
              />
            </div>
            {renderPermissionSelector()}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateRole} disabled={isSubmitting}>
              {isSubmitting ? 'Creating...' : 'Create Role'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Role Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Role</DialogTitle>
            <DialogDescription>Update role settings and permissions.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {formErrors.length > 0 && (
              <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                {formErrors.map((err, i) => <div key={i}>{err}</div>)}
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-code">Code</Label>
                <Input
                  id="edit-code"
                  value={formData.code}
                  disabled
                  className="bg-muted"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-name">Name</Label>
                <Input
                  id="edit-name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={2}
              />
            </div>
            {renderPermissionSelector()}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateRole} disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Permissions Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{selectedRole?.name} - Permissions</DialogTitle>
            <DialogDescription>
              {selectedRole?.description || `Permissions assigned to the ${selectedRole?.name} role.`}
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-96 overflow-y-auto">
            {(() => {
              // Role.permissions is array of permission codes, group by category
              const allPermissions = Object.values(permissionsByCategory).flat();
              const rolePermissions = (selectedRole?.permissions || [])
                .map(code => allPermissions.find(p => p.code === code))
                .filter((p): p is Permission => !!p);

              const grouped = rolePermissions.reduce((acc, perm) => {
                if (!acc[perm.category]) acc[perm.category] = [];
                acc[perm.category].push(perm);
                return acc;
              }, {} as Record<string, Permission[]>);

              return Object.entries(grouped).map(([category, permissions]) => (
                <div key={category} className="mb-4">
                  <h4 className="font-medium text-sm mb-2 capitalize">{category}</h4>
                  <div className="flex flex-wrap gap-1">
                    {permissions.map(perm => (
                      <Badge key={perm.id} variant="secondary" className="text-xs">
                        {perm.name}
                      </Badge>
                    ))}
                  </div>
                </div>
              ));
            })()}
            {(selectedRole?.permissions || []).length === 0 && (
              <p className="text-muted-foreground text-center py-4">No permissions assigned.</p>
            )}
          </div>
          <DialogFooter>
            <Button onClick={() => setViewDialogOpen(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Role Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Role</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the role &quot;{selectedRole?.name}&quot;? Users with this role will lose these permissions. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteRole} disabled={isSubmitting}>
              {isSubmitting ? 'Deleting...' : 'Delete Role'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      </div>
    </AppLayout>
  );
}
