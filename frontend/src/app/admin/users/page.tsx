'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth, Permissions } from '@/components/auth-provider';
import { api, AdminUser, Role, AdminUserCreateResponse } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
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
import { MoreVertical } from 'lucide-react';
import { AppLayout } from '@/components/layout/app-layout';
import { SearchInput } from '@/components/ui/search-input';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { ErrorAlert } from '@/components/ui/error-alert';

export default function AdminUsersPage() {
  const t = useTranslations('users');
  const tCommon = useTranslations('common');
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
    language: 'en',  // Default to English
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

  if (authLoading || isLoading) {
    return <LoadingSpinner fullScreen size="lg" />;
  }

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto">
        <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>{t('userManagement')}</CardTitle>
              <CardDescription>{t('manageUsersDescription')}</CardDescription>
            </div>
            {canCreate && (
              <Button onClick={openCreateDialog}>{t('addUser')}</Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <ErrorAlert message={error} onDismiss={() => setError('')} className="mb-4" />
          )}

          <SearchInput
            value={search}
            onChange={setSearch}
            onSearch={handleSearch}
            onClear={loadData}
            placeholder={t('searchByEmailOrName')}
            showButtons
            className="mb-4 max-w-lg"
          />

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{tCommon('email')}</TableHead>
                <TableHead>{tCommon('name')}</TableHead>
                <TableHead>{t('roles')}</TableHead>
                <TableHead>{tCommon('status')}</TableHead>
                <TableHead>{t('lastLogin')}</TableHead>
                <TableHead className="text-right">{tCommon('actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">{user.email}</TableCell>
                  <TableCell>{user.name || '-'}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {user.roles.map((roleCode) => {
                        const role = roles.find(r => r.code === roleCode);
                        return (
                          <Badge key={roleCode} variant={role?.is_system ? 'default' : 'secondary'}>
                            {role?.name || roleCode}
                          </Badge>
                        );
                      })}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {!user.is_active ? (
                        <Badge variant="secondary">{tCommon('inactive')}</Badge>
                      ) : (
                        <Badge variant="default" className="bg-green-600">{tCommon('active')}</Badge>
                      )}
                      {user.has_google_login && (
                        <span title={t('googleLinked')} className="text-blue-600">
                          <svg className="h-4 w-4" viewBox="0 0 24 24">
                            <path
                              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                              fill="#4285F4"
                            />
                            <path
                              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                              fill="#34A853"
                            />
                            <path
                              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                              fill="#FBBC05"
                            />
                            <path
                              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                              fill="#EA4335"
                            />
                          </svg>
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {user.last_login_at
                      ? new Date(user.last_login_at).toLocaleString()
                      : t('never')}
                  </TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreVertical className="h-4 w-4" />
                          <span className="sr-only">{tCommon('actions')}</span>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {canUpdate && (
                          <DropdownMenuItem onClick={() => openEditDialog(user)}>
                            {tCommon('edit')}
                          </DropdownMenuItem>
                        )}
                        {canDelete && user.id !== currentUser?.id && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => openDeleteDialog(user)}
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
              {users.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                    {t('noUsersFound')}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Create User Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('addUser')}</DialogTitle>
            <DialogDescription>{t('addUserDescription')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
              {formErrors.length > 0 && (
                <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                  {formErrors.map((err, i) => <div key={i}>{err}</div>)}
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="create-email">{tCommon('email')}</Label>
                <Input
                  id="create-email"
                  type="email"
                  autoComplete="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="create-name">{t('nameOptional')}</Label>
                <Input
                  id="create-name"
                  autoComplete="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="create-language">{t('emailLanguage')}</Label>
                <select
                  id="create-language"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  value={formData.language}
                  onChange={(e) => setFormData({ ...formData, language: e.target.value })}
                >
                  <option value="en">English</option>
                  <option value="de">Deutsch</option>
                </select>
                <p className="text-xs text-muted-foreground">
                  {t('emailLanguageDescription')}
                </p>
              </div>
              <div className="p-3 bg-blue-50 text-blue-700 text-sm rounded-md">
                {t('userWillLoginWithGoogle')}
              </div>
              <div className="space-y-2">
                <Label>{t('roles')}</Label>
                <div className="flex flex-wrap gap-2">
                  {roles.map((role) => (
                    <Badge
                      key={role.id}
                      variant={formData.role_codes.includes(role.code) ? 'default' : 'outline'}
                      className="cursor-pointer"
                      onClick={() => toggleRole(role.code)}
                    >
                      {role.name}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              {tCommon('cancel')}
            </Button>
            <Button onClick={handleCreateUser} disabled={isSubmitting}>
              {isSubmitting ? t('creating') : t('addUser')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit User Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('editUser')}</DialogTitle>
            <DialogDescription>{t('editUserDescription')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {formErrors.length > 0 && (
              <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                {formErrors.map((err, i) => <div key={i}>{err}</div>)}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="edit-email">{tCommon('email')}</Label>
              <Input
                id="edit-email"
                type="email"
                autoComplete="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                disabled={selectedUser?.has_google_login}
              />
              {selectedUser?.has_google_login && (
                <p className="text-xs text-muted-foreground">
                  {t('emailCannotBeChanged')}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-name">{t('nameOptional')}</Label>
              <Input
                id="edit-name"
                autoComplete="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>{t('roles')}</Label>
              <div className="flex flex-wrap gap-2">
                {roles.map((role) => (
                  <Badge
                    key={role.id}
                    variant={formData.role_codes.includes(role.code) ? 'default' : 'outline'}
                    className="cursor-pointer"
                    onClick={() => toggleRole(role.code)}
                  >
                    {role.name}
                  </Badge>
                ))}
              </div>
            </div>
            {/* Active status toggle - cannot deactivate yourself */}
            {selectedUser && selectedUser.id !== currentUser?.id && (
              <div className="flex items-center justify-between rounded-lg border p-3">
                <div className="space-y-0.5">
                  <Label htmlFor="edit-active">{t('userActive')}</Label>
                  <p className="text-xs text-muted-foreground">
                    {t('userActiveDescription')}
                  </p>
                </div>
                <Switch
                  id="edit-active"
                  checked={formData.is_active}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              {tCommon('cancel')}
            </Button>
            <Button onClick={handleUpdateUser} disabled={isSubmitting}>
              {isSubmitting ? t('saving') : t('saveChanges')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete User Dialog */}
      <ConfirmationDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title={t('deleteUser')}
        description={t('deleteUserConfirmation', { email: selectedUser?.email || '' })}
        confirmLabel={t('deleteUser')}
        loadingLabel={t('deleting')}
        onConfirm={handleDeleteUser}
        isLoading={isSubmitting}
      />

      </div>
    </AppLayout>
  );
}
