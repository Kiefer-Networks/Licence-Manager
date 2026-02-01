'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  api,
  AdminAccountPattern,
  License,
  Provider,
  Employee,
} from '@/lib/api';
import {
  Search,
  Plus,
  Trash2,
  Loader2,
  ShieldCheck,
  Play,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  User,
  Building2,
  Globe,
  Check,
  AlertTriangle,
  Users,
  AlertCircle,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

// Type for grouped admin accounts
interface GroupedAdminAccount {
  email: string;
  name: string | null;
  owner_id: string | null;
  owner_name: string | null;
  owner_status: string | null;
  licenses: License[];
  providers: { id: string; name: string; status: string }[];
  hasGlobalPattern: boolean;
  hasSuspended: boolean;
  activeCount: number;
  suspendedCount: number;
}

interface AdminAccountsTabProps {
  providers: Provider[];
  showToast: (type: 'success' | 'error' | 'info', text: string) => void;
}

export function AdminAccountsTab({ providers, showToast }: AdminAccountsTabProps) {
  const t = useTranslations('adminAccounts');
  const tCommon = useTranslations('common');
  const tLicenses = useTranslations('licenses');

  // Patterns state
  const [patterns, setPatterns] = useState<AdminAccountPattern[]>([]);
  const [loadingPatterns, setLoadingPatterns] = useState(true);
  const [showAddPattern, setShowAddPattern] = useState(false);
  const [newPattern, setNewPattern] = useState({
    email_pattern: '',
    name: '',
    notes: '',
  });
  const [creatingPattern, setCreatingPattern] = useState(false);
  const [deletingPatternId, setDeletingPatternId] = useState<string | null>(null);
  const [applyingPatterns, setApplyingPatterns] = useState(false);
  const [makeGlobalLicense, setMakeGlobalLicense] = useState<License | null>(null);
  const [makingGlobal, setMakingGlobal] = useState(false);

  // Pattern matches dialog state
  const [matchesDialog, setMatchesDialog] = useState<AdminAccountPattern | null>(null);
  const [matchesLicenses, setMatchesLicenses] = useState<License[]>([]);
  const [loadingMatches, setLoadingMatches] = useState(false);

  // Edit owner dialog state
  const [editOwnerAccount, setEditOwnerAccount] = useState<GroupedAdminAccount | null>(null);
  const [selectedOwnerId, setSelectedOwnerId] = useState<string>('');
  const [savingOwner, setSavingOwner] = useState(false);

  // Admin Account Licenses state
  const [licenses, setLicenses] = useState<License[]>([]);
  const [loadingLicenses, setLoadingLicenses] = useState(true);
  const [licensesTotal, setLicensesTotal] = useState(0);
  const [licensesPage, setLicensesPage] = useState(1);
  const [licensesSearch, setLicensesSearch] = useState('');
  const [licensesProviderId, setLicensesProviderId] = useState<string>('all');
  const [licensesSortColumn, setLicensesSortColumn] = useState<string>('external_user_id');
  const [licensesSortDir, setLicensesSortDir] = useState<'asc' | 'desc'>('asc');

  // Employees for owner selection
  const [employees, setEmployees] = useState<Employee[]>([]);

  // Load patterns
  useEffect(() => {
    loadPatterns();
    loadEmployees();
  }, []);

  // Load admin account licenses
  useEffect(() => {
    loadLicenses();
  }, [licensesPage, licensesSearch, licensesProviderId, licensesSortColumn, licensesSortDir]);

  const loadPatterns = async () => {
    setLoadingPatterns(true);
    try {
      const response = await api.getAdminAccountPatterns();
      setPatterns(response.items);
    } catch (error) {
      showToast('error', t('failedToLoadPatterns'));
    } finally {
      setLoadingPatterns(false);
    }
  };

  const loadLicenses = async () => {
    setLoadingLicenses(true);
    try {
      const response = await api.getAdminAccountLicenses({
        page: licensesPage,
        page_size: 50,
        search: licensesSearch || undefined,
        provider_id: licensesProviderId !== 'all' ? licensesProviderId : undefined,
        sort_by: licensesSortColumn,
        sort_dir: licensesSortDir,
      });
      setLicenses(response.items);
      setLicensesTotal(response.total);
    } catch (error) {
      showToast('error', t('failedToLoadLicenses'));
    } finally {
      setLoadingLicenses(false);
    }
  };

  const loadEmployees = async () => {
    try {
      const response = await api.getEmployees({ page_size: 200, status: 'active' });
      setEmployees(response.items);
    } catch (error) {
      // Silent fail for employee loading
    }
  };

  const handleShowMatches = async (pattern: AdminAccountPattern) => {
    setMatchesDialog(pattern);
    setLoadingMatches(true);
    setMatchesLicenses([]);
    try {
      // Use the pattern as search query to find matching licenses
      const response = await api.getAdminAccountLicenses({
        search: pattern.email_pattern.replace('*', ''),  // Remove wildcard for search
        page_size: 200,
      });
      // Filter client-side to get exact matches for this pattern
      const patternRegex = new RegExp(
        '^' + pattern.email_pattern.replace(/\*/g, '.*').replace(/\?/g, '.') + '$',
        'i'
      );
      const filtered = response.items.filter(license =>
        patternRegex.test(license.external_user_id)
      );
      setMatchesLicenses(filtered);
    } catch (error) {
      showToast('error', t('failedToLoadMatching'));
    } finally {
      setLoadingMatches(false);
    }
  };

  const handleCreatePattern = async () => {
    if (!newPattern.email_pattern.trim()) {
      showToast('error', t('emailPatternRequired'));
      return;
    }

    setCreatingPattern(true);
    try {
      await api.createAdminAccountPattern({
        email_pattern: newPattern.email_pattern.trim(),
        name: newPattern.name.trim() || undefined,
        notes: newPattern.notes.trim() || undefined,
      });
      showToast('success', t('patternCreated'));
      setShowAddPattern(false);
      setNewPattern({ email_pattern: '', name: '', notes: '' });
      loadPatterns();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToCreatePattern'));
    } finally {
      setCreatingPattern(false);
    }
  };

  const handleDeletePattern = async (patternId: string) => {
    setDeletingPatternId(patternId);
    try {
      await api.deleteAdminAccountPattern(patternId);
      showToast('success', t('patternDeleted'));
      loadPatterns();
    } catch (error) {
      showToast('error', t('failedToDeletePattern'));
    } finally {
      setDeletingPatternId(null);
    }
  };

  const handleApplyPatterns = async () => {
    setApplyingPatterns(true);
    try {
      const result = await api.applyAdminAccountPatterns();
      if (result.updated_count > 0) {
        showToast('success', t('patternsApplied', { count: result.updated_count }));
        loadLicenses();
        loadPatterns();
      } else {
        showToast('info', t('noNewMatches'));
      }
    } catch (error) {
      showToast('error', t('failedToApply'));
    } finally {
      setApplyingPatterns(false);
    }
  };

  const handleLicenseSort = (column: string) => {
    if (licensesSortColumn === column) {
      setLicensesSortDir(licensesSortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setLicensesSortColumn(column);
      setLicensesSortDir('asc');
    }
  };

  // Check if email already has a global pattern
  const isEmailGlobal = (email: string): boolean => {
    return patterns.some((p) => {
      if (p.email_pattern === email) return true;
      // Check wildcard pattern match
      if (p.email_pattern.includes('*')) {
        const regex = new RegExp('^' + p.email_pattern.replace(/\*/g, '.*') + '$', 'i');
        return regex.test(email);
      }
      return false;
    });
  };

  const handleMakeGlobal = async () => {
    if (!makeGlobalLicense) return;

    setMakingGlobal(true);
    try {
      await api.createAdminAccountPattern({
        email_pattern: makeGlobalLicense.external_user_id,
        name: makeGlobalLicense.admin_account_name || undefined,
      });
      showToast('success', t('patternCreated'));
      setMakeGlobalLicense(null);
      loadPatterns();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToCreatePattern'));
    } finally {
      setMakingGlobal(false);
    }
  };

  const handleOpenEditOwner = (account: GroupedAdminAccount) => {
    setEditOwnerAccount(account);
    setSelectedOwnerId(account.owner_id || '');
  };

  const handleSaveOwner = async () => {
    if (!editOwnerAccount) return;

    setSavingOwner(true);
    try {
      // Update all licenses for this admin account
      for (const license of editOwnerAccount.licenses) {
        await api.updateLicenseAdminAccount(license.id, {
          is_admin_account: true,
          admin_account_name: editOwnerAccount.name || undefined,
          admin_account_owner_id: selectedOwnerId || undefined,
        });
      }
      showToast('success', t('ownerUpdated'));
      setEditOwnerAccount(null);
      loadLicenses();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToUpdateOwner'));
    } finally {
      setSavingOwner(false);
    }
  };

  const SortIcon = ({ column }: { column: string }) => {
    if (licensesSortColumn !== column) return <ChevronsUpDown className="h-3.5 w-3.5 text-zinc-400" />;
    return licensesSortDir === 'asc' ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />;
  };

  const licensesPageSize = 50;
  const licensesTotalPages = Math.ceil(licensesTotal / licensesPageSize);

  // Group licenses by email
  const groupedAccounts: GroupedAdminAccount[] = (() => {
    const grouped = new Map<string, GroupedAdminAccount>();

    for (const license of licenses) {
      const email = license.external_user_id;
      const existing = grouped.get(email);

      if (existing) {
        existing.licenses.push(license);
        existing.providers.push({
          id: license.provider_id,
          name: license.provider_name,
          status: license.status,
        });
        if (license.status === 'suspended' || license.status === 'inactive') {
          existing.hasSuspended = true;
          existing.suspendedCount++;
        } else if (license.status === 'active') {
          existing.activeCount++;
        }
      } else {
        grouped.set(email, {
          email,
          name: license.admin_account_name || null,
          owner_id: license.admin_account_owner_id || null,
          owner_name: license.admin_account_owner_name || null,
          owner_status: license.admin_account_owner_status || null,
          licenses: [license],
          providers: [{
            id: license.provider_id,
            name: license.provider_name,
            status: license.status,
          }],
          hasGlobalPattern: isEmailGlobal(email),
          hasSuspended: license.status === 'suspended' || license.status === 'inactive',
          activeCount: license.status === 'active' ? 1 : 0,
          suspendedCount: (license.status === 'suspended' || license.status === 'inactive') ? 1 : 0,
        });
      }
    }

    return Array.from(grouped.values());
  })();

  // Calculate summary statistics
  const summaryStats = {
    uniqueAdmins: groupedAccounts.length,
    totalLicenses: licenses.length,
    uniqueProviders: new Set(licenses.map(l => l.provider_id)).size,
    suspendedLicenses: licenses.filter(l => l.status === 'suspended' || l.status === 'inactive').length,
    adminsWithSuspended: groupedAccounts.filter(a => a.hasSuspended).length,
  };

  return (
    <div className="space-y-8">
      {/* Global Patterns Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-medium">{t('patterns')}</h2>
            <p className="text-sm text-muted-foreground">
              {t('emailPattern')}
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleApplyPatterns}
              disabled={applyingPatterns || patterns.length === 0}
            >
              {applyingPatterns ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              {t('applyToAll')}
            </Button>
            <Button size="sm" onClick={() => setShowAddPattern(true)}>
              <Plus className="h-4 w-4 mr-2" />
              {t('addPattern')}
            </Button>
          </div>
        </div>

        {/* Patterns Table */}
        <div className="border rounded-lg bg-white overflow-hidden">
          {loadingPatterns ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
            </div>
          ) : patterns.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
              <ShieldCheck className="h-8 w-8 mb-2 opacity-30" />
              <p className="text-sm">{tCommon('noData')}</p>
              <p className="text-xs">{t('emailPattern')}</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-zinc-50/50">
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('emailPattern')}</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tCommon('name')}</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('matchingLicenses')}</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">{tCommon('actions')}</th>
                </tr>
              </thead>
              <tbody>
                {patterns.map((pattern) => (
                  <tr key={pattern.id} className="border-b last:border-0 hover:bg-zinc-50/50">
                    <td className="px-4 py-3">
                      <code className="text-sm bg-zinc-100 px-2 py-0.5 rounded">
                        {pattern.email_pattern}
                      </code>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {pattern.name || '-'}
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant="outline"
                        className={`tabular-nums ${pattern.match_count > 0 ? 'cursor-pointer hover:bg-zinc-100' : ''}`}
                        onClick={() => pattern.match_count > 0 && handleShowMatches(pattern)}
                      >
                        {pattern.match_count}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeletePattern(pattern.id)}
                        disabled={deletingPatternId === pattern.id}
                        className="text-destructive hover:text-destructive"
                      >
                        {deletingPatternId === pattern.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Admin Account Licenses Section */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-medium">{t('title')}</h2>
          <p className="text-sm text-muted-foreground">
            {t('matchingLicenses')}
          </p>
        </div>

        {/* Summary Cards */}
        {!loadingLicenses && licenses.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Card className="bg-gradient-to-br from-purple-50 to-white border-purple-100">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <Users className="h-4 w-4 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-semibold text-purple-700">{summaryStats.uniqueAdmins}</p>
                    <p className="text-xs text-purple-600">{t('title')}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-blue-50 to-white border-blue-100">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <ShieldCheck className="h-4 w-4 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-semibold text-blue-700">{summaryStats.totalLicenses}</p>
                    <p className="text-xs text-blue-600">{tLicenses('title')}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-emerald-50 to-white border-emerald-100">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-emerald-100 rounded-lg">
                    <Building2 className="h-4 w-4 text-emerald-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-semibold text-emerald-700">{summaryStats.uniqueProviders}</p>
                    <p className="text-xs text-emerald-600">{tLicenses('provider')}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {summaryStats.suspendedLicenses > 0 ? (
              <Card className="bg-gradient-to-br from-amber-50 to-white border-amber-100">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-amber-100 rounded-lg">
                      <AlertCircle className="h-4 w-4 text-amber-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-semibold text-amber-700">{summaryStats.suspendedLicenses}</p>
                      <p className="text-xs text-amber-600">{tCommon('inactive')}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="bg-gradient-to-br from-zinc-50 to-white border-zinc-100">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-zinc-100 rounded-lg">
                      <Check className="h-4 w-4 text-zinc-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-semibold text-zinc-700">0</p>
                      <p className="text-xs text-zinc-600">{tCommon('inactive')}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
            <Input
              placeholder={tLicenses('searchPlaceholder')}
              value={licensesSearch}
              onChange={(e) => {
                setLicensesSearch(e.target.value);
                setLicensesPage(1);
              }}
              className="pl-9 h-9 bg-zinc-50 border-zinc-200"
            />
          </div>

          <Select value={licensesProviderId} onValueChange={(v) => {
            setLicensesProviderId(v);
            setLicensesPage(1);
          }}>
            <SelectTrigger className="w-44 h-9 bg-zinc-50 border-zinc-200">
              <SelectValue placeholder={tLicenses('provider')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{tLicenses('allProviders')}</SelectItem>
              {providers.map((provider) => (
                <SelectItem key={provider.id} value={provider.id}>
                  {provider.display_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <span className="text-sm text-muted-foreground ml-auto">
            {tLicenses('licenseCount', { count: licensesTotal })}
          </span>
        </div>

        {/* Grouped Licenses Table */}
        <div className="border rounded-lg bg-white overflow-hidden">
          {loadingLicenses ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
            </div>
          ) : groupedAccounts.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <ShieldCheck className="h-8 w-8 mb-2 opacity-30" />
              <p className="text-sm">{tCommon('noData')}</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-zinc-50/50">
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <button onClick={() => handleLicenseSort('external_user_id')} className="flex items-center gap-1.5 hover:text-foreground">
                      {tCommon('email')} <SortIcon column="external_user_id" />
                    </button>
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tLicenses('provider')}</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tCommon('name')}</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('owner')}</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tCommon('status')}</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">{t('patterns')}</th>
                </tr>
              </thead>
              <tbody>
                {groupedAccounts.map((account) => (
                  <tr key={account.email} className={`border-b last:border-0 hover:bg-zinc-50/50 ${account.hasSuspended ? 'bg-amber-50/30' : ''}`}>
                    <td className="px-4 py-3">
                      <code className="text-sm bg-zinc-100 px-2 py-0.5 rounded">
                        {account.email}
                      </code>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1.5">
                        {account.providers.map((provider, idx) => (
                          <Badge
                            key={`${provider.id}-${idx}`}
                            variant="outline"
                            className={`text-xs ${
                              provider.status === 'active'
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : 'bg-zinc-100 text-zinc-500 border-zinc-200'
                            }`}
                          >
                            {provider.name}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {account.name || '-'}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleOpenEditOwner(account)}
                        className="flex items-center gap-1.5 hover:bg-zinc-100 rounded px-2 py-1 -mx-2 -my-1 transition-colors"
                        title={t('clickToEditOwner')}
                      >
                        {account.owner_name ? (
                          <>
                            <User className="h-3.5 w-3.5 text-muted-foreground" />
                            <span className={account.owner_status === 'offboarded' ? 'text-red-600' : 'text-muted-foreground'}>
                              {account.owner_name}
                            </span>
                            {account.owner_status === 'offboarded' && (
                              <span title={t('ownerOffboarded')}><AlertTriangle className="h-3.5 w-3.5 text-red-500" /></span>
                            )}
                          </>
                        ) : (
                          <span className="text-muted-foreground text-xs">{t('clickToAssign')}</span>
                        )}
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        {account.activeCount > 0 && (
                          <Badge variant="secondary" className="bg-emerald-50 text-emerald-700 border-0 text-xs">
                            {account.activeCount} {tCommon('active').toLowerCase()}
                          </Badge>
                        )}
                        {account.suspendedCount > 0 && (
                          <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 text-xs">
                            {account.suspendedCount} {tCommon('inactive').toLowerCase()}
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {account.hasGlobalPattern ? (
                        <div
                          className="inline-flex items-center gap-1 text-emerald-600"
                          title={t('emailMatchesGlobalPattern')}
                        >
                          <Check className="h-4 w-4" />
                          <Globe className="h-4 w-4" />
                        </div>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setMakeGlobalLicense(account.licenses[0])}
                          className="text-muted-foreground hover:text-foreground"
                          title={t('makeGlobalPattern')}
                        >
                          <Globe className="h-4 w-4" />
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {licensesTotalPages > 1 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {tLicenses('pageOf', { page: licensesPage, total: licensesTotalPages })}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setLicensesPage(licensesPage - 1)}
                disabled={licensesPage === 1}
              >
                {tLicenses('previous')}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setLicensesPage(licensesPage + 1)}
                disabled={licensesPage === licensesTotalPages}
              >
                {tCommon('next')}
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Pattern Matches Dialog */}
      <Dialog open={!!matchesDialog} onOpenChange={(open) => !open && setMatchesDialog(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-purple-500" />
              {t('matchingLicenses')}
            </DialogTitle>
            <DialogDescription>
              {t('emailPattern')}: <code className="bg-zinc-100 px-2 py-0.5 rounded">{matchesDialog?.email_pattern}</code>
              {matchesDialog?.name && <span> ({matchesDialog.name})</span>}
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-auto">
            {loadingMatches ? (
              <div className="flex items-center justify-center h-48">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : matchesLicenses.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                <ShieldCheck className="h-8 w-8 mb-2 opacity-30" />
                <p className="text-sm">{t('noNewMatches')}</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-white">
                  <tr className="border-b bg-zinc-50/50">
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tCommon('email')}</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tLicenses('provider')}</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tLicenses('licenseType')}</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('owner')}</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tCommon('status')}</th>
                  </tr>
                </thead>
                <tbody>
                  {matchesLicenses.map((license) => (
                    <tr key={license.id} className="border-b last:border-0 hover:bg-zinc-50/50">
                      <td className="px-4 py-3">
                        <code className="text-sm bg-zinc-100 px-2 py-0.5 rounded">
                          {license.external_user_id}
                        </code>
                      </td>
                      <td className="px-4 py-3">
                        <a
                          href={`/providers/${license.provider_id}`}
                          className="text-sm text-blue-600 hover:underline flex items-center gap-1"
                        >
                          <Building2 className="h-3.5 w-3.5" />
                          {license.provider_name}
                        </a>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {license.license_type_display_name || license.license_type || '-'}
                      </td>
                      <td className="px-4 py-3">
                        {license.admin_account_owner_name ? (
                          <div className="flex items-center gap-1.5">
                            <User className="h-3.5 w-3.5 text-muted-foreground" />
                            <span className={license.admin_account_owner_status === 'offboarded' ? 'text-red-600 line-through' : 'text-muted-foreground'}>
                              {license.admin_account_owner_name}
                            </span>
                            {license.admin_account_owner_status === 'offboarded' && (
                              <span title={t('ownerOffboarded')}><AlertTriangle className="h-3.5 w-3.5 text-red-500" /></span>
                            )}
                          </div>
                        ) : (
                          <span className="text-muted-foreground text-xs">{tLicenses('unassigned')}</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={license.status === 'active' ? 'secondary' : 'outline'} className={license.status === 'active' ? 'bg-emerald-50 text-emerald-700' : ''}>
                          {license.status === 'active' ? tLicenses('active') : tLicenses('inactive')}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setMatchesDialog(null)}>{tCommon('close')}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Make Global Dialog */}
      <Dialog open={!!makeGlobalLicense} onOpenChange={(open) => !open && setMakeGlobalLicense(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('addPattern')}</DialogTitle>
            <DialogDescription>
              {t('emailPattern')}
            </DialogDescription>
          </DialogHeader>
          {makeGlobalLicense && (
            <div className="space-y-4 py-4">
              <div className="p-3 bg-zinc-50 rounded-lg space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">{tCommon('email')}:</span>
                  <code className="text-sm bg-white px-2 py-0.5 rounded border">
                    {makeGlobalLicense.external_user_id}
                  </code>
                </div>
                {makeGlobalLicense.admin_account_name && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">{tCommon('name')}:</span>
                    <span className="text-sm">{makeGlobalLicense.admin_account_name}</span>
                  </div>
                )}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setMakeGlobalLicense(null)}>
              {tCommon('cancel')}
            </Button>
            <Button onClick={handleMakeGlobal} disabled={makingGlobal}>
              {makingGlobal ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Globe className="h-4 w-4 mr-2" />
              )}
              {t('addPattern')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Pattern Dialog */}
      <Dialog open={showAddPattern} onOpenChange={setShowAddPattern}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('addPattern')}</DialogTitle>
            <DialogDescription>
              {t('emailPattern')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="email_pattern">{t('emailPattern')} *</Label>
              <Input
                id="email_pattern"
                placeholder={t('emailPatternPlaceholder')}
                value={newPattern.email_pattern}
                onChange={(e) => setNewPattern({ ...newPattern, email_pattern: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">{tCommon('name')}</Label>
              <Input
                id="name"
                placeholder={t('adminNamePlaceholder')}
                value={newPattern.name}
                onChange={(e) => setNewPattern({ ...newPattern, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">{t('notes')}</Label>
              <Textarea
                id="notes"
                placeholder={t('notes')}
                value={newPattern.notes}
                onChange={(e) => setNewPattern({ ...newPattern, notes: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddPattern(false)}>
              {tCommon('cancel')}
            </Button>
            <Button onClick={handleCreatePattern} disabled={creatingPattern}>
              {creatingPattern ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : null}
              {t('addPattern')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Owner Dialog */}
      <Dialog open={!!editOwnerAccount} onOpenChange={(open) => !open && setEditOwnerAccount(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <User className="h-5 w-5 text-purple-500" />
              {t('assignOwner')}
            </DialogTitle>
            <DialogDescription>
              {t('assignOwnerDescription')}
            </DialogDescription>
          </DialogHeader>
          {editOwnerAccount && (
            <div className="space-y-4 py-4">
              <div className="p-3 bg-zinc-50 rounded-lg space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">{tCommon('email')}:</span>
                  <code className="text-sm bg-white px-2 py-0.5 rounded border">
                    {editOwnerAccount.email}
                  </code>
                </div>
                {editOwnerAccount.name && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">{tCommon('name')}:</span>
                    <span className="text-sm">{editOwnerAccount.name}</span>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">{tLicenses('title')}:</span>
                  <span className="text-sm">{editOwnerAccount.licenses.length}</span>
                </div>
              </div>

              <div className="space-y-2">
                <Label>{t('owner')}</Label>
                <Select value={selectedOwnerId || '__none__'} onValueChange={(v) => setSelectedOwnerId(v === '__none__' ? '' : v)}>
                  <SelectTrigger>
                    <SelectValue placeholder={tCommon('selectOption')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">{tCommon('none')}</SelectItem>
                    {employees.map((emp) => (
                      <SelectItem key={emp.id} value={emp.id}>
                        {emp.full_name} ({emp.department || '-'})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOwnerAccount(null)}>
              {tCommon('cancel')}
            </Button>
            <Button onClick={handleSaveOwner} disabled={savingOwner}>
              {savingOwner ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Check className="h-4 w-4 mr-2" />
              )}
              {tCommon('save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
