'use client';

import { useTranslations } from 'next-intl';
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
import { useAdminUsers } from '@/hooks/use-admin-users';

export default function AdminUsersPage() {
  const t = useTranslations('users');
  const tCommon = useTranslations('common');

  const {
    users,
    roles,
    isLoading,
    error,
    setError,
    search,
    setSearch,
    currentUser,
    authLoading,
    canCreate,
    canUpdate,
    canDelete,
    createDialogOpen,
    setCreateDialogOpen,
    editDialogOpen,
    setEditDialogOpen,
    deleteDialogOpen,
    setDeleteDialogOpen,
    selectedUser,
    formData,
    setFormData,
    formErrors,
    isSubmitting,
    loadData,
    handleSearch,
    openCreateDialog,
    openEditDialog,
    openDeleteDialog,
    handleCreateUser,
    handleUpdateUser,
    handleDeleteUser,
    toggleRole,
  } = useAdminUsers({ t, tCommon });

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
