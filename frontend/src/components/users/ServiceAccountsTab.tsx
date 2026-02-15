'use client';

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
import { EmployeeAutocomplete } from '@/components/ui/employee-autocomplete';
import { Provider } from '@/lib/api';
import {
  Search,
  Plus,
  Trash2,
  Loader2,
  Bot,
  Play,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  User,
  Building2,
  Globe,
  Check,
  Tag,
} from 'lucide-react';
import { useServiceAccounts } from '@/hooks/use-service-accounts';

interface ServiceAccountsTabProps {
  providers: Provider[];
  showToast: (type: 'success' | 'error' | 'info', text: string) => void;
}

export function ServiceAccountsTab({ providers, showToast }: ServiceAccountsTabProps) {
  const t = useTranslations('serviceAccounts');
  const tCommon = useTranslations('common');
  const tLicenses = useTranslations('licenses');

  const {
    patterns,
    loadingPatterns,
    showAddPattern,
    setShowAddPattern,
    newPattern,
    setNewPattern,
    creatingPattern,
    deletingPatternId,
    applyingPatterns,
    handleCreatePattern,
    handleDeletePattern,
    handleApplyPatterns,
    makeGlobalLicense,
    setMakeGlobalLicense,
    makingGlobal,
    handleMakeGlobal,
    matchesDialog,
    setMatchesDialog,
    matchesLicenses,
    loadingMatches,
    handleShowMatches,
    licenses,
    loadingLicenses,
    licensesTotal,
    licensesPage,
    setLicensesPage,
    licensesSearch,
    setLicensesSearch,
    licensesProviderId,
    setLicensesProviderId,
    licensesSortColumn,
    licensesSortDir,
    handleLicenseSort,
    employees,
    licenseTypes,
    loadingLicenseTypes,
    showAddLicenseType,
    setShowAddLicenseType,
    newLicenseType,
    setNewLicenseType,
    creatingLicenseType,
    deletingLicenseTypeId,
    applyingLicenseTypes,
    handleCreateLicenseType,
    handleDeleteLicenseType,
    handleApplyLicenseTypes,
    licensesTotalPages,
    isEmailGlobal,
  } = useServiceAccounts(providers, showToast, t, tCommon, tLicenses);

  const SortIcon = ({ column }: { column: string }) => {
    if (licensesSortColumn !== column) return <ChevronsUpDown className="h-3.5 w-3.5 text-zinc-400" />;
    return licensesSortDir === 'asc' ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />;
  };

  return (
    <div className="space-y-8">
      {/* Global Patterns Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-medium">{t('patterns')}</h2>
            <p className="text-sm text-muted-foreground">
              {t('patternHelp')}
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
              <Bot className="h-8 w-8 mb-2 opacity-30" />
              <p className="text-sm">{tCommon('noData')}</p>
              <p className="text-xs">{t('patternHelp')}</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-zinc-50/50">
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('emailPattern')}</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tCommon('name')}</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('owner')}</th>
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
                      {pattern.owner_name ? (
                        <div className="flex items-center gap-1.5">
                          <User className="h-3.5 w-3.5 text-muted-foreground" />
                          <span className="text-muted-foreground">{pattern.owner_name}</span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
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

      {/* License Type Rules Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-medium">{t('licenseTypes')}</h2>
            <p className="text-sm text-muted-foreground">
              {t('licenseTypesHelp')}
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleApplyLicenseTypes}
              disabled={applyingLicenseTypes || licenseTypes.length === 0}
            >
              {applyingLicenseTypes ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              {t('applyLicenseTypes')}
            </Button>
            <Button size="sm" onClick={() => setShowAddLicenseType(true)}>
              <Plus className="h-4 w-4 mr-2" />
              {t('addLicenseType')}
            </Button>
          </div>
        </div>

        {/* License Types Table */}
        <div className="border rounded-lg bg-white overflow-hidden">
          {loadingLicenseTypes ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
            </div>
          ) : licenseTypes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
              <Tag className="h-8 w-8 mb-2 opacity-30" />
              <p className="text-sm">{tCommon('noData')}</p>
              <p className="text-xs">{t('licenseTypesHelp')}</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-zinc-50/50">
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('licenseType')}</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tCommon('name')}</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('owner')}</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('matchingLicenses')}</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">{tCommon('actions')}</th>
                </tr>
              </thead>
              <tbody>
                {licenseTypes.map((entry) => (
                  <tr key={entry.id} className="border-b last:border-0 hover:bg-zinc-50/50">
                    <td className="px-4 py-3">
                      <code className="text-sm bg-zinc-100 px-2 py-0.5 rounded">
                        {entry.license_type}
                      </code>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {entry.name || '-'}
                    </td>
                    <td className="px-4 py-3">
                      {entry.owner_name ? (
                        <div className="flex items-center gap-1.5">
                          <User className="h-3.5 w-3.5 text-muted-foreground" />
                          <span className="text-muted-foreground">{entry.owner_name}</span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="outline" className="tabular-nums">
                        {entry.match_count}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteLicenseType(entry.id)}
                        disabled={deletingLicenseTypeId === entry.id}
                        className="text-destructive hover:text-destructive"
                      >
                        {deletingLicenseTypeId === entry.id ? (
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

      {/* Service Account Licenses Section */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-medium">{t('title')}</h2>
          <p className="text-sm text-muted-foreground">
            {t('matchingLicenses')}
          </p>
        </div>

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

        {/* Licenses Table */}
        <div className="border rounded-lg bg-white overflow-hidden">
          {loadingLicenses ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
            </div>
          ) : licenses.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <Bot className="h-8 w-8 mb-2 opacity-30" />
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
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tLicenses('licenseType')}</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tCommon('status')}</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">{t('patterns')}</th>
                </tr>
              </thead>
              <tbody>
                {licenses.map((license) => (
                  <tr key={license.id} className="border-b last:border-0 hover:bg-zinc-50/50">
                    <td className="px-4 py-3">
                      <code className="text-sm bg-zinc-100 px-2 py-0.5 rounded">
                        {license.external_user_id}
                      </code>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <Building2 className="h-3.5 w-3.5 text-muted-foreground" />
                        <span>{license.provider_name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {license.service_account_name || '-'}
                    </td>
                    <td className="px-4 py-3">
                      {license.service_account_owner_name ? (
                        <div className="flex items-center gap-1.5">
                          <User className="h-3.5 w-3.5 text-muted-foreground" />
                          <span className="text-muted-foreground">{license.service_account_owner_name}</span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {license.license_type_display_name || license.license_type || '-'}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={license.status === 'active' ? 'secondary' : 'outline'}
                             className={license.status === 'active' ? 'bg-emerald-50 text-emerald-700 border-0' : ''}>
                        {license.status === 'active' ? tLicenses('active') : tLicenses('inactive')}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {isEmailGlobal(license.external_user_id) ? (
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
                          onClick={() => setMakeGlobalLicense(license)}
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
              <Bot className="h-5 w-5 text-blue-500" />
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
                <Bot className="h-8 w-8 mb-2 opacity-30" />
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
                        {license.service_account_owner_name ? (
                          <div className="flex items-center gap-1.5">
                            <User className="h-3.5 w-3.5 text-muted-foreground" />
                            <span className="text-muted-foreground">{license.service_account_owner_name}</span>
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
              {t('patternHelp')}
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
                {makeGlobalLicense.service_account_name && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">{tCommon('name')}:</span>
                    <span className="text-sm">{makeGlobalLicense.service_account_name}</span>
                  </div>
                )}
                {makeGlobalLicense.service_account_owner_name && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">{t('owner')}:</span>
                    <span className="text-sm">{makeGlobalLicense.service_account_owner_name}</span>
                  </div>
                )}
              </div>
              <p className="text-sm text-muted-foreground">
                {t('patternHelp')}
              </p>
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
              {t('patternHelp')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="email_pattern">{t('emailPattern')} *</Label>
              <Input
                id="email_pattern"
                placeholder="svc-*@company.com"
                value={newPattern.email_pattern}
                onChange={(e) => setNewPattern({ ...newPattern, email_pattern: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                {t('patternHelp')}
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">{tCommon('name')}</Label>
              <Input
                id="name"
                placeholder={t('serviceNamePlaceholder')}
                value={newPattern.name}
                onChange={(e) => setNewPattern({ ...newPattern, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="owner">{t('owner')} ({tCommon('optional')})</Label>
              <EmployeeAutocomplete
                employees={employees}
                value={newPattern.owner_id}
                onChange={(v) => setNewPattern({ ...newPattern, owner_id: v })}
                placeholder={tCommon('selectOption')}
                noOwnerLabel={tCommon('none')}
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

      {/* Add License Type Dialog */}
      <Dialog open={showAddLicenseType} onOpenChange={setShowAddLicenseType}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('addLicenseType')}</DialogTitle>
            <DialogDescription>
              {t('licenseTypesHelp')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="license_type">{t('licenseType')} *</Label>
              <Input
                id="license_type"
                placeholder={t('licenseTypePlaceholder')}
                value={newLicenseType.license_type}
                onChange={(e) => setNewLicenseType({ ...newLicenseType, license_type: e.target.value })}
                maxLength={500}
              />
              <p className="text-xs text-muted-foreground">
                {t('licenseTypeDescription')}
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="license_type_name">{tCommon('name')}</Label>
              <Input
                id="license_type_name"
                placeholder={t('serviceNamePlaceholder')}
                value={newLicenseType.name}
                onChange={(e) => setNewLicenseType({ ...newLicenseType, name: e.target.value })}
                maxLength={255}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="license_type_owner">{t('owner')} ({tCommon('optional')})</Label>
              <EmployeeAutocomplete
                employees={employees}
                value={newLicenseType.owner_id}
                onChange={(v) => setNewLicenseType({ ...newLicenseType, owner_id: v })}
                placeholder={tCommon('selectOption')}
                noOwnerLabel={tCommon('none')}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="license_type_notes">{t('notes')}</Label>
              <Textarea
                id="license_type_notes"
                placeholder={t('notes')}
                value={newLicenseType.notes}
                onChange={(e) => setNewLicenseType({ ...newLicenseType, notes: e.target.value })}
                maxLength={2000}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddLicenseType(false)}>
              {tCommon('cancel')}
            </Button>
            <Button onClick={handleCreateLicenseType} disabled={creatingLicenseType}>
              {creatingLicenseType ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : null}
              {t('addLicenseType')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
