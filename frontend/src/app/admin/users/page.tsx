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
import { MoreVertical, Shield } from 'lucide-react';
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
  const [resetPasswordDialogOpen, setResetPasswordDialogOpen] = useState(false);
  const [disable2FADialogOpen, setDisable2FADialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [temporaryPassword, setTemporaryPassword] = useState<string | null>(null);
  const [passwordSentViaEmail, setPasswordSentViaEmail] = useState(false);
  const [emailConfigured, setEmailConfigured] = useState(false);
  const [createResult, setCreateResult] = useState<AdminUserCreateResponse | null>(null);

  // Form states
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    password: '',
    language: 'en',  // Default to English
    role_codes: [] as string[],
  });
  const [formErrors, setFormErrors] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Note: These client-side permission checks are for UX only (hiding buttons/UI).
  // Server-side enforcement via require_permission() is the authoritative check.
  // All API endpoints validate permissions independently.
  const canCreate = hasPermission(Permissions.ADMIN_USERS_CREATE);
  const canUpdate = hasPermission(Permissions.ADMIN_USERS_UPDATE);
  const canDelete = hasPermission(Permissions.ADMIN_USERS_DELETE);
  const canResetPassword = hasPermission(Permissions.ADMIN_USERS_RESET_PASSWORD);
  const isSuperadmin = currentUser?.is_superadmin ?? false;

  useEffect(() => {
    if (!authLoading && !hasPermission(Permissions.ADMIN_USERS_VIEW)) {
      router.push('/unauthorized');
      return;
    }
  }, [authLoading, hasPermission, router]);

  useEffect(() => {
    loadData();
    checkEmailConfig();
  }, []);

  const checkEmailConfig = async () => {
    try {
      const configured = await api.isEmailConfigured();
      setEmailConfigured(configured);
    } catch {
      setEmailConfigured(false);
    }
  };

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
    setFormData({ email: '', name: '', password: '', language: 'en', role_codes: [] });
    setFormErrors([]);
    setCreateResult(null);
    setTemporaryPassword(null);
    setPasswordSentViaEmail(false);
    setCreateDialogOpen(true);
  };

  const openEditDialog = (user: AdminUser) => {
    setSelectedUser(user);
    setFormData({
      email: user.email,
      name: user.name || '',
      password: '',
      language: user.language || 'en',
      role_codes: user.roles, // Backend returns role codes directly
    });
    setFormErrors([]);
    setEditDialogOpen(true);
  };

  const openDeleteDialog = (user: AdminUser) => {
    setSelectedUser(user);
    setDeleteDialogOpen(true);
  };

  const openResetPasswordDialog = (user: AdminUser) => {
    setSelectedUser(user);
    setTemporaryPassword(null);
    setPasswordSentViaEmail(false);
    setResetPasswordDialogOpen(true);
  };

  const openDisable2FADialog = (user: AdminUser) => {
    setSelectedUser(user);
    setDisable2FADialogOpen(true);
  };

  const handleDisable2FA = async () => {
    if (!selectedUser) return;
    setIsSubmitting(true);

    try {
      await api.disableUserTotp(selectedUser.id);
      setDisable2FADialogOpen(false);
      await loadData();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('failedToDisable2FA');
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateUser = async () => {
    setFormErrors([]);
    setIsSubmitting(true);

    try {
      // Convert role codes to role IDs for the API
      const roleIds = formData.role_codes
        .map(code => roles.find(r => r.code === code)?.id)
        .filter((id): id is string => !!id);

      const result = await api.createAdminUser({
        email: formData.email,
        name: formData.name || undefined,
        password: formData.password || undefined,
        language: formData.language,
        role_ids: roleIds,
      });

      setCreateResult(result);
      setPasswordSentViaEmail(result.password_sent_via_email);
      setTemporaryPassword(result.temporary_password || null);

      // Only close dialog if password was sent via email
      if (result.password_sent_via_email) {
        setCreateDialogOpen(false);
        await loadData();
      }
      // If temporary_password is returned, keep dialog open to show it
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

  const handleResetPassword = async () => {
    if (!selectedUser) return;
    setIsSubmitting(true);

    try {
      const result = await api.resetAdminUserPassword(selectedUser.id);
      setPasswordSentViaEmail(result.password_sent_via_email);
      setTemporaryPassword(result.temporary_password || null);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('failedToResetPassword');
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
                      ) : user.require_password_change ? (
                        <Badge variant="outline" className="text-amber-600 border-amber-200 bg-amber-50">{t('passwordChangeRequired')}</Badge>
                      ) : (
                        <Badge variant="default" className="bg-green-600">{tCommon('active')}</Badge>
                      )}
                      {user.totp_enabled && (
                        <span title={t('twoFactorEnabled')} className="text-green-600">
                          <Shield className="h-4 w-4" />
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
                        {canResetPassword && (
                          <DropdownMenuItem onClick={() => openResetPasswordDialog(user)}>
                            {t('resetPassword')}
                          </DropdownMenuItem>
                        )}
                        {isSuperadmin && user.totp_enabled && user.id !== currentUser?.id && (
                          <DropdownMenuItem onClick={() => openDisable2FADialog(user)}>
                            {t('disable2FA')}
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
      <Dialog open={createDialogOpen} onOpenChange={(open) => {
        if (!open && createResult) {
          loadData();
        }
        setCreateDialogOpen(open);
        if (!open) {
          setCreateResult(null);
          setTemporaryPassword(null);
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('addUser')}</DialogTitle>
            <DialogDescription>{createResult ? t('userCreated') : t('addUserDescription')}</DialogDescription>
          </DialogHeader>
          {createResult && createResult.temporary_password ? (
            <div className="space-y-4">
              <div className="p-4 bg-muted rounded-md">
                <Label className="text-sm text-muted-foreground">{t('temporaryPassword')}</Label>
                <div className="font-mono text-lg mt-1 select-all">{createResult.temporary_password}</div>
              </div>
              <p className="text-sm text-muted-foreground">
                {t('sharePasswordSecurely')}
              </p>
            </div>
          ) : (
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
              {!emailConfigured && (
                <div className="space-y-2">
                  <Label htmlFor="create-password">{tCommon('password')}</Label>
                  <Input
                    id="create-password"
                    type="password"
                    autoComplete="new-password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    minLength={12}
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    {t('passwordRequirementsText')}
                  </p>
                </div>
              )}
              {emailConfigured && (
                <div className="p-3 bg-blue-50 text-blue-700 text-sm rounded-md">
                  {t('passwordWillBeSentViaEmail')}
                </div>
              )}
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
          )}
          <DialogFooter>
            {createResult ? (
              <Button onClick={() => {
                setCreateDialogOpen(false);
                setCreateResult(null);
                setTemporaryPassword(null);
                loadData();
              }}>{t('done')}</Button>
            ) : (
              <>
                <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                  {tCommon('cancel')}
                </Button>
                <Button onClick={handleCreateUser} disabled={isSubmitting}>
                  {isSubmitting ? t('creating') : t('addUser')}
                </Button>
              </>
            )}
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
              />
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

      {/* Reset Password Dialog */}
      <Dialog open={resetPasswordDialogOpen} onOpenChange={setResetPasswordDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('resetPassword')}</DialogTitle>
            <DialogDescription>
              {passwordSentViaEmail
                ? t('passwordSentViaEmail')
                : temporaryPassword
                ? t('temporaryPasswordGenerated')
                : t('resetPasswordFor', { email: selectedUser?.email || '' })}
            </DialogDescription>
          </DialogHeader>
          {passwordSentViaEmail ? (
            <div className="space-y-4">
              <div className="p-4 bg-green-50 text-green-700 rounded-md">
                {t('passwordEmailSentTo', { email: selectedUser?.email || '' })}
              </div>
            </div>
          ) : temporaryPassword ? (
            <div className="space-y-4">
              <div className="p-4 bg-muted rounded-md">
                <Label className="text-sm text-muted-foreground">{t('temporaryPassword')}</Label>
                <div className="font-mono text-lg mt-1 select-all">{temporaryPassword}</div>
              </div>
              <p className="text-sm text-muted-foreground">
                {t('sharePasswordSecurely')}
              </p>
            </div>
          ) : null}
          <DialogFooter>
            {temporaryPassword || passwordSentViaEmail ? (
              <Button onClick={() => setResetPasswordDialogOpen(false)}>{t('done')}</Button>
            ) : (
              <>
                <Button variant="outline" onClick={() => setResetPasswordDialogOpen(false)}>
                  {tCommon('cancel')}
                </Button>
                <Button onClick={handleResetPassword} disabled={isSubmitting}>
                  {isSubmitting ? t('resetting') : t('resetPassword')}
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Disable 2FA Dialog */}
      <ConfirmationDialog
        open={disable2FADialogOpen}
        onOpenChange={setDisable2FADialogOpen}
        title={t('disable2FA')}
        description={t('disable2FAConfirmation', { email: selectedUser?.email || '' })}
        confirmLabel={t('disable2FA')}
        loadingLabel={t('disabling')}
        onConfirm={handleDisable2FA}
        isLoading={isSubmitting}
      />
      </div>
    </AppLayout>
  );
}
