'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { api, License, Employee, EmployeeSuggestion } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';
import {
  Loader2,
  Bot,
  ShieldCheck,
  Link2,
  Search,
  X,
  User,
  Check,
  UserPlus,
} from 'lucide-react';

// ==================== Bulk Action Dialogs ====================

interface BulkRemoveDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  removableCount: number;
  totalSelected: number;
  loading: boolean;
  onConfirm: () => void;
}

export function BulkRemoveDialog({
  open,
  onOpenChange,
  removableCount,
  totalSelected,
  loading,
  onConfirm,
}: BulkRemoveDialogProps) {
  const t = useTranslations('licenses');
  const tCommon = useTranslations('common');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('removeFromProvider')}</DialogTitle>
          <DialogDescription>
            {t('removeFromProviderDescription', { count: removableCount })}
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <p className="text-sm text-zinc-600 mb-3">{t('actionsPerformed')}</p>
          <ul className="text-sm space-y-2">
            <li className="flex items-start gap-2">
              <span className="text-emerald-600">-</span>
              <span>{t('usersRemovedFromProvider')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-600">-</span>
              <span>{t('licensesDeletedFromDB')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-600">-</span>
              <span>{t('onlyCursorSupports', { count: removableCount, total: totalSelected })}</span>
            </li>
          </ul>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            {tCommon('cancel')}
          </Button>
          <Button onClick={onConfirm} disabled={loading}>
            {loading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
            {t('removeLicenses', { count: removableCount })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface BulkDeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedCount: number;
  loading: boolean;
  onConfirm: () => void;
}

export function BulkDeleteDialog({
  open,
  onOpenChange,
  selectedCount,
  loading,
  onConfirm,
}: BulkDeleteDialogProps) {
  const t = useTranslations('licenses');
  const tCommon = useTranslations('common');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('bulkDelete')}</DialogTitle>
          <DialogDescription>
            {t('bulkDeleteDescription', { count: selectedCount })}
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <p className="text-sm text-zinc-600 mb-3">{t('important')}</p>
          <ul className="text-sm space-y-2">
            <li className="flex items-start gap-2">
              <span className="text-red-600">-</span>
              <span>{t('doesNotRemoveFromProvider')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-600">-</span>
              <span>{t('mayReappear')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-zinc-600">-</span>
              <span>{t('useRemoveInstead')}</span>
            </li>
          </ul>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            {tCommon('cancel')}
          </Button>
          <Button variant="destructive" onClick={onConfirm} disabled={loading}>
            {loading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
            {t('deleteCount', { count: selectedCount })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface BulkUnassignDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assignedCount: number;
  loading: boolean;
  onConfirm: () => void;
}

export function BulkUnassignDialog({
  open,
  onOpenChange,
  assignedCount,
  loading,
  onConfirm,
}: BulkUnassignDialogProps) {
  const t = useTranslations('licenses');
  const tCommon = useTranslations('common');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('bulkUnassign')}</DialogTitle>
          <DialogDescription>
            {t('bulkUnassignDescription', { count: assignedCount })}
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <p className="text-sm text-zinc-600 mb-3">{t('thisActionWill')}</p>
          <ul className="text-sm space-y-2">
            <li className="flex items-start gap-2">
              <span className="text-amber-600">-</span>
              <span>{t('removeEmployeeAssociation')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-zinc-600">-</span>
              <span>{t('markAsUnassignedInSystem')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-zinc-600">-</span>
              <span>{t('licensesRemainInDB')}</span>
            </li>
          </ul>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            {tCommon('cancel')}
          </Button>
          <Button onClick={onConfirm} disabled={loading}>
            {loading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
            {t('unassignCount', { count: assignedCount })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==================== Mark As Account Dialog ====================

interface MarkAsAccountDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  license: License | null;
  type: 'service' | 'admin';
  onSuccess: () => void;
  onToast: (message: string, type: 'success' | 'error') => void;
}

export function MarkAsAccountDialog({
  open,
  onOpenChange,
  license,
  type,
  onSuccess,
  onToast,
}: MarkAsAccountDialogProps) {
  const t = useTranslations('licenses');
  const tCommon = useTranslations('common');
  const tServiceAccounts = useTranslations('serviceAccounts');
  const tAdminAccounts = useTranslations('adminAccounts');

  const [name, setName] = useState('');
  const [ownerId, setOwnerId] = useState('');
  const [ownerQuery, setOwnerQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [showOwnerResults, setShowOwnerResults] = useState(false);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loadingEmployees, setLoadingEmployees] = useState(false);

  const loadEmployees = useCallback(async (search?: string) => {
    setLoadingEmployees(true);
    try {
      const response = await api.getEmployees({
        page_size: 50,
        status: 'active',
        search: search || undefined,
      });
      setEmployees(response.items);
    } catch (error) {
      handleSilentError('loadEmployees', error);
    } finally {
      setLoadingEmployees(false);
    }
  }, []);

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      setName('');
      setOwnerId('');
      setOwnerQuery('');
      setShowOwnerResults(false);
      loadEmployees();
    }
  }, [open, loadEmployees]);

  // Debounce employee search
  useEffect(() => {
    if (!open) return;

    const timer = setTimeout(() => {
      loadEmployees(ownerQuery.trim() || undefined);
    }, 300);

    return () => clearTimeout(timer);
  }, [ownerQuery, open, loadEmployees]);

  const handleSelectOwner = (emp: Employee) => {
    setOwnerId(emp.id);
    setOwnerQuery(emp.full_name);
    setShowOwnerResults(false);
  };

  const handleClearOwner = () => {
    setOwnerId('');
    setOwnerQuery('');
    setShowOwnerResults(false);
  };

  const handleSubmit = async () => {
    if (!license) return;

    setLoading(true);
    try {
      if (type === 'service') {
        await api.updateLicenseServiceAccount(license.id, {
          is_service_account: true,
          service_account_name: name || undefined,
          service_account_owner_id: ownerId || undefined,
        });
        onToast(tServiceAccounts('markedAsServiceAccount'), 'success');
      } else {
        await api.updateLicenseAdminAccount(license.id, {
          is_admin_account: true,
          admin_account_name: name || undefined,
          admin_account_owner_id: ownerId || undefined,
        });
        onToast(tAdminAccounts('markedAsAdminAccount'), 'success');
      }
      onOpenChange(false);
      onSuccess();
    } catch {
      onToast(t('failedToUpdate'), 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {type === 'service' ? (
              <>
                <Bot className="h-5 w-5 text-blue-500" />
                {tServiceAccounts('markAsServiceAccount')}
              </>
            ) : (
              <>
                <ShieldCheck className="h-5 w-5 text-purple-500" />
                {tAdminAccounts('markAsAdminAccount')}
              </>
            )}
          </DialogTitle>
          <DialogDescription>
            {type === 'service'
              ? tServiceAccounts('markAsServiceAccountDescription')
              : tAdminAccounts('markAsAdminAccountDescription')}
          </DialogDescription>
        </DialogHeader>
        {license && (
          <div className="space-y-4 py-4">
            <div className="p-3 bg-zinc-50 rounded-lg">
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">{t('user')}:</span>
                <code className="text-sm bg-white px-2 py-0.5 rounded border">
                  {license.external_user_id}
                </code>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="markAsName">{tCommon('name')}</Label>
              <Input
                id="markAsName"
                placeholder={type === 'service' ? tServiceAccounts('serviceNamePlaceholder') : tAdminAccounts('adminNamePlaceholder')}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>{type === 'service' ? tServiceAccounts('owner') : tAdminAccounts('owner')}</Label>
              <div className="relative">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                  <Input
                    placeholder={tServiceAccounts('searchEmployee')}
                    value={ownerQuery}
                    onChange={(e) => {
                      setOwnerQuery(e.target.value);
                      setShowOwnerResults(true);
                      if (!e.target.value) {
                        setOwnerId('');
                      }
                    }}
                    onFocus={() => setShowOwnerResults(true)}
                    className="pl-9 pr-9"
                  />
                  {ownerQuery && (
                    <button
                      type="button"
                      onClick={handleClearOwner}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
                {showOwnerResults && (
                  <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 overflow-auto">
                    <button
                      type="button"
                      onClick={handleClearOwner}
                      className={`w-full px-3 py-2 text-left text-sm hover:bg-zinc-50 flex items-center gap-2 ${
                        !ownerId ? 'bg-zinc-50' : ''
                      }`}
                    >
                      <span className="text-muted-foreground">{tCommon('none')}</span>
                    </button>
                    {loadingEmployees ? (
                      <div className="px-3 py-4 text-sm text-muted-foreground text-center flex items-center justify-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        {tCommon('loading')}
                      </div>
                    ) : employees.length === 0 ? (
                      <div className="px-3 py-4 text-sm text-muted-foreground text-center">
                        {tServiceAccounts('noEmployeesFound')}
                      </div>
                    ) : (
                      employees.map((emp) => (
                        <button
                          key={emp.id}
                          type="button"
                          onClick={() => handleSelectOwner(emp)}
                          className={`w-full px-3 py-2 text-left text-sm hover:bg-zinc-50 flex items-center gap-2 ${
                            ownerId === emp.id ? 'bg-blue-50' : ''
                          }`}
                        >
                          <User className="h-4 w-4 text-zinc-400 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate">{emp.full_name}</div>
                            <div className="text-xs text-muted-foreground truncate">
                              {emp.department || '-'} · {emp.email}
                            </div>
                          </div>
                          {ownerId === emp.id && (
                            <Check className="h-4 w-4 text-blue-600 flex-shrink-0" />
                          )}
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            {tCommon('cancel')}
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
            {type === 'service' ? tServiceAccounts('markAsServiceAccount') : tAdminAccounts('markAsAdminAccount')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==================== Link to Employee Dialog ====================

interface LinkToEmployeeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  license: License | null;
  onSuccess: () => void;
  onToast: (message: string, type: 'success' | 'error') => void;
}

export function LinkToEmployeeDialog({
  open,
  onOpenChange,
  license,
  onSuccess,
  onToast,
}: LinkToEmployeeDialogProps) {
  const t = useTranslations('licenses');
  const tCommon = useTranslations('common');

  const [suggestions, setSuggestions] = useState<EmployeeSuggestion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [linkLoading, setLinkLoading] = useState(false);

  // Fetch suggestions when dialog opens
  useEffect(() => {
    if (!open || !license) return;

    const fetchSuggestions = async () => {
      setSuggestions([]);
      setLoadingSuggestions(true);

      try {
        const metadata = license.metadata as Record<string, unknown> | undefined;
        const username = (metadata?.username as string) || (metadata?.hf_username as string) || license.external_user_id;
        const displayName = (metadata?.fullname as string) || (metadata?.display_name as string);
        const providerName = license.provider_name;

        const response = await api.getEmployeeSuggestions(providerName, username, displayName);
        setSuggestions(response.suggestions);
      } catch (error) {
        handleSilentError('getEmployeeSuggestions', error);
      } finally {
        setLoadingSuggestions(false);
      }
    };

    fetchSuggestions();
  }, [open, license]);

  const handleLinkToEmployee = async (employeeId: string) => {
    if (!license) return;

    setLinkLoading(true);
    try {
      const metadata = license.metadata as Record<string, unknown> | undefined;
      const username = (metadata?.username as string) || (metadata?.hf_username as string) || license.external_user_id;
      const displayName = (metadata?.fullname as string) || (metadata?.display_name as string);

      await api.linkExternalAccount(employeeId, {
        provider_type: license.provider_name,
        external_username: username,
        display_name: displayName,
      });

      onToast(t('linkedToEmployee'), 'success');
      onOpenChange(false);
      onSuccess();
    } catch {
      onToast(t('failedToLink'), 'error');
    } finally {
      setLinkLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-blue-500" />
            {t('linkToEmployee')}
          </DialogTitle>
          <DialogDescription>
            {t('linkToEmployeeDescription')}
          </DialogDescription>
        </DialogHeader>
        {license && (
          <div className="space-y-4 py-4">
            <div className="p-3 bg-zinc-50 rounded-lg">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm text-muted-foreground">{t('provider')}:</span>
                <span className="text-sm font-medium">{license.provider_name}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">{t('user')}:</span>
                <code className="text-sm bg-white px-2 py-0.5 rounded border">
                  {license.external_user_id}
                </code>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="text-sm font-medium">{t('suggestedMatches')}</h4>
              {loadingSuggestions ? (
                <div className="flex items-center justify-center py-6">
                  <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
                </div>
              ) : suggestions.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground">
                  <UserPlus className="h-8 w-8 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">{t('noSuggestionsFound')}</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {suggestions.map((suggestion) => (
                    <button
                      key={suggestion.employee_id}
                      onClick={() => handleLinkToEmployee(suggestion.employee_id)}
                      disabled={linkLoading}
                      className="w-full p-3 text-left rounded-lg border hover:bg-zinc-50 transition-colors disabled:opacity-50"
                    >
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-zinc-100 flex items-center justify-center flex-shrink-0">
                          <span className="text-sm font-medium text-zinc-600">
                            {suggestion.employee_name.charAt(0)}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium truncate">{suggestion.employee_name}</span>
                            <Badge variant="secondary" className="text-[10px] px-1.5">
                              {t('matchScore', { score: Math.round(suggestion.similarity_score * 100) })}
                            </Badge>
                          </div>
                          <div className="text-xs text-muted-foreground truncate">
                            {suggestion.employee_email}
                          </div>
                          <div className="text-xs text-muted-foreground/70 truncate mt-0.5">
                            {t('matchReason', { reason: suggestion.match_reason })}
                          </div>
                        </div>
                        {linkLoading ? (
                          <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
                        ) : (
                          <UserPlus className="h-4 w-4 text-zinc-400" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={linkLoading}>
            {tCommon('cancel')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
