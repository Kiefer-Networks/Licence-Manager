'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth, Permissions } from '@/components/auth-provider';
import { Permission } from '@/lib/api';
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
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
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
import { MoreHorizontal } from 'lucide-react';
import { useAdminRoles } from '@/hooks/use-admin-roles';

export default function AdminRolesPage() {
  const t = useTranslations('roles');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { hasPermission, isLoading: authLoading } = useAuth();

  const {
    roles,
    permissionsByCategory,
    isLoading,
    error,
    setError,
    createDialogOpen,
    setCreateDialogOpen,
    editDialogOpen,
    setEditDialogOpen,
    deleteDialogOpen,
    setDeleteDialogOpen,
    viewDialogOpen,
    setViewDialogOpen,
    selectedRole,
    formData,
    setFormData,
    formErrors,
    isSubmitting,
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
  } = useAdminRoles(t, tCommon);

  const canCreate = hasPermission(Permissions.ROLES_CREATE);
  const canUpdate = hasPermission(Permissions.ROLES_UPDATE);
  const canDelete = hasPermission(Permissions.ROLES_DELETE);

  useEffect(() => {
    if (!authLoading && !hasPermission(Permissions.ROLES_VIEW)) {
      router.push('/unauthorized');
      return;
    }
  }, [authLoading, hasPermission, router]);

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
        <Label>{t('permissions')}</Label>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" onClick={selectAllPermissions}>
            {t('selectAll')}
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={clearAllPermissions}>
            {t('clearAll')}
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
                  <span className="text-sm font-medium">{t('selectAllCategory', { category })}</span>
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
                <CardTitle>{t('roleManagement')}</CardTitle>
              <CardDescription>{t('manageRolesDescription')}</CardDescription>
            </div>
            {canCreate && (
              <Button onClick={openCreateDialog}>{t('addRole')}</Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mb-4 bg-destructive/10 text-destructive text-sm p-3 rounded-md">
              {error}
              <button className="ml-2 underline" onClick={() => setError('')}>{tCommon('close')}</button>
            </div>
          )}

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('code')}</TableHead>
                <TableHead>{tCommon('name')}</TableHead>
                <TableHead>{tCommon('description')}</TableHead>
                <TableHead>{t('type')}</TableHead>
                <TableHead>{t('priority')}</TableHead>
                <TableHead>{t('permissions')}</TableHead>
                <TableHead className="text-right">{tCommon('actions')}</TableHead>
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
                      {role.is_system ? t('system') : t('custom')}
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
                      {t('permissionCount', { count: role.permissions.length })}
                    </Button>
                  </TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreHorizontal className="h-4 w-4" />
                          <span className="sr-only">{tCommon('actions')}</span>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => openViewDialog(role)}>
                          {t('viewPermissions')}
                        </DropdownMenuItem>
                        {canUpdate && !role.is_system && (
                          <DropdownMenuItem onClick={() => openEditDialog(role)}>
                            {tCommon('edit')}
                          </DropdownMenuItem>
                        )}
                        {canDelete && !role.is_system && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => openDeleteDialog(role)}
                            >
                              {tCommon('delete')}
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
                    {t('noRolesFound')}
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
            <DialogTitle>{t('addRole')}</DialogTitle>
            <DialogDescription>{t('addRoleDescription')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {formErrors.length > 0 && (
              <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                {formErrors.map((err, i) => <div key={i}>{err}</div>)}
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="create-code">{t('code')}</Label>
                <Input
                  id="create-code"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') })}
                  placeholder={t('codePlaceholder')}
                  required
                />
                <p className="text-xs text-muted-foreground">{t('lowercaseOnly')}</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="create-name">{tCommon('name')}</Label>
                <Input
                  id="create-name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder={t('namePlaceholder')}
                  required
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-description">{tCommon('description')}</Label>
              <Textarea
                id="create-description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder={t('descriptionPlaceholder')}
                rows={2}
              />
            </div>
            {renderPermissionSelector()}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              {tCommon('cancel')}
            </Button>
            <Button onClick={handleCreateRole} disabled={isSubmitting}>
              {isSubmitting ? t('creating') : t('addRole')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Role Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('editRole')}</DialogTitle>
            <DialogDescription>{t('editRoleDescription')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {formErrors.length > 0 && (
              <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                {formErrors.map((err, i) => <div key={i}>{err}</div>)}
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-code">{t('code')}</Label>
                <Input
                  id="edit-code"
                  value={formData.code}
                  disabled
                  className="bg-muted"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-name">{tCommon('name')}</Label>
                <Input
                  id="edit-name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-description">{t('description')}</Label>
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
              {tCommon('cancel')}
            </Button>
            <Button onClick={handleUpdateRole} disabled={isSubmitting}>
              {isSubmitting ? t('saving') : t('saveChanges')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Permissions Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{t('rolePermissions', { name: selectedRole?.name ?? '' })}</DialogTitle>
            <DialogDescription>
              {selectedRole?.description || t('permissionsAssignedTo', { name: selectedRole?.name ?? '' })}
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
              <p className="text-muted-foreground text-center py-4">{t('noPermissionsAssigned')}</p>
            )}
          </div>
          <DialogFooter>
            <Button onClick={() => setViewDialogOpen(false)}>{tCommon('close')}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Role Dialog */}
      <ConfirmationDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title={t('deleteRole')}
        description={t('deleteRoleConfirmation', { name: selectedRole?.name || '' })}
        confirmLabel={t('deleteRole')}
        loadingLabel={t('deleting')}
        onConfirm={handleDeleteRole}
        isLoading={isSubmitting}
      />
      </div>
    </AppLayout>
  );
}
