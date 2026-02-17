'use client';

import { useState, useMemo, memo, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { License } from '@/lib/api';
import { formatMonthlyCost } from '@/lib/format';
import { LicenseStatusBadge } from './LicenseStatusBadge';
import { Pagination } from '@/components/ui/pagination';
import { SearchInput } from '@/components/ui/search-input';
import { ChevronUp, ChevronDown, ChevronsUpDown, Key, MoreHorizontal, Bot, UserPlus, Trash2, ShieldCheck, Tags, Check, X, Lightbulb, Ban } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import Link from 'next/link';

interface LicenseTableProps {
  licenses: License[];
  showProvider?: boolean;
  showEmployee?: boolean;
  showSuggestion?: boolean;
  emptyMessage?: string;
  onSelect?: (license: License) => void;
  selectedIds?: Set<string>;
  onToggleSelect?: (id: string) => void;
  onToggleSelectAll?: () => void;
  onServiceAccountClick?: (license: License) => void;
  onAdminAccountClick?: (license: License) => void;
  onLicenseTypeClick?: (license: License) => void;
  onAssignClick?: (license: License) => void;
  onDeleteClick?: (license: License) => void;
  onCancelClick?: (license: License) => void;
  onConfirmMatch?: (license: License) => void;
  onRejectMatch?: (license: License) => void;
}

type SortColumn = 'external_user_id' | 'employee_name' | 'license_type' | 'monthly_cost' | 'provider_name';

function LicenseTableComponent({
  licenses,
  showProvider = true,
  showEmployee = true,
  showSuggestion = false,
  emptyMessage,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onServiceAccountClick,
  onAdminAccountClick,
  onLicenseTypeClick,
  onAssignClick,
  onDeleteClick,
  onCancelClick,
  onConfirmMatch,
  onRejectMatch,
}: LicenseTableProps) {
  const t = useTranslations('licenses');
  const tCommon = useTranslations('common');
  const tLifecycle = useTranslations('lifecycle');
  const displayEmptyMessage = emptyMessage || tCommon('noResults');
  const hasActions = onServiceAccountClick || onAdminAccountClick || onLicenseTypeClick || onAssignClick || onDeleteClick || onCancelClick;
  const hasMatchActions = onConfirmMatch || onRejectMatch;
  const [search, setSearch] = useState('');
  const [sortColumn, setSortColumn] = useState<SortColumn>('external_user_id');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const handleSort = useCallback((column: SortColumn) => {
    setSortColumn((prevColumn) => {
      if (prevColumn === column) {
        setSortDirection((prevDir) => prevDir === 'asc' ? 'desc' : 'asc');
        return prevColumn;
      } else {
        setSortDirection('asc');
        return column;
      }
    });
  }, []);

  const SortIcon = ({ column }: { column: SortColumn }) => {
    if (sortColumn !== column) return <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground" />;
    return sortDirection === 'asc' ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />;
  };

  // Filter and sort licenses
  const filteredLicenses = useMemo(() => {
    let result = licenses;

    // Search filter
    if (search) {
      const searchLower = search.toLowerCase();
      const metaStr = (val: unknown) => typeof val === 'string' ? val.toLowerCase() : '';
      result = result.filter(
        (l) =>
          l.external_user_id.toLowerCase().includes(searchLower) ||
          l.employee_name?.toLowerCase().includes(searchLower) ||
          l.employee_email?.toLowerCase().includes(searchLower) ||
          l.provider_name.toLowerCase().includes(searchLower) ||
          l.license_type?.toLowerCase().includes(searchLower) ||
          l.service_account_name?.toLowerCase().includes(searchLower) ||
          l.service_account_owner_name?.toLowerCase().includes(searchLower) ||
          // Search in metadata (names, usernames, emails)
          metaStr(l.metadata?.email).includes(searchLower) ||
          metaStr(l.metadata?.assignee_name).includes(searchLower) ||
          metaStr(l.metadata?.fullName).includes(searchLower) ||
          metaStr(l.metadata?.fullname).includes(searchLower) ||
          metaStr(l.metadata?.displayName).includes(searchLower) ||
          metaStr(l.metadata?.display_name).includes(searchLower) ||
          metaStr(l.metadata?.username).includes(searchLower) ||
          metaStr(l.metadata?.hf_username).includes(searchLower)
      );
    }

    // Sort
    result = [...result].sort((a, b) => {
      let aVal: string | number = '';
      let bVal: string | number = '';

      switch (sortColumn) {
        case 'external_user_id':
          // Use metadata.email if available (e.g., JetBrains), otherwise external_user_id
          aVal = (a.metadata?.email || a.external_user_id).toLowerCase();
          bVal = (b.metadata?.email || b.external_user_id).toLowerCase();
          break;
        case 'employee_name':
          aVal = (a.employee_name || '').toLowerCase();
          bVal = (b.employee_name || '').toLowerCase();
          break;
        case 'license_type':
          aVal = (a.license_type || '').toLowerCase();
          bVal = (b.license_type || '').toLowerCase();
          break;
        case 'monthly_cost':
          aVal = parseFloat(a.monthly_cost || '0');
          bVal = parseFloat(b.monthly_cost || '0');
          break;
        case 'provider_name':
          aVal = a.provider_name.toLowerCase();
          bVal = b.provider_name.toLowerCase();
          break;
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return result;
  }, [licenses, search, sortColumn, sortDirection]);

  // Pagination
  const totalPages = Math.ceil(filteredLicenses.length / pageSize);
  const paginatedLicenses = filteredLicenses.slice((page - 1) * pageSize, page * pageSize);

  const showSelection = selectedIds && onToggleSelect && onToggleSelectAll;

  return (
    <div className="space-y-4">
      {/* Search */}
      <SearchInput
        value={search}
        onChange={(value) => {
          setSearch(value);
          setPage(1);
        }}
        placeholder={t('searchPlaceholder')}
      />

      {/* Table */}
      <div className="border rounded-lg bg-card overflow-hidden">
        {paginatedLicenses.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
            <Key className="h-8 w-8 mb-2 opacity-30" />
            <p className="text-sm">{displayEmptyMessage}</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                {showSelection && (
                  <th className="w-10 px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.size === paginatedLicenses.length && paginatedLicenses.length > 0}
                      onChange={onToggleSelectAll}
                      className="h-4 w-4 rounded border-input text-primary focus:ring-ring"
                    />
                  </th>
                )}
                {showProvider && (
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <button onClick={() => handleSort('provider_name')} className="flex items-center gap-1.5 hover:text-foreground">
                      {t('provider')} <SortIcon column="provider_name" />
                    </button>
                  </th>
                )}
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                  <button onClick={() => handleSort('external_user_id')} className="flex items-center gap-1.5 hover:text-foreground">
                    {t('license')} <SortIcon column="external_user_id" />
                  </button>
                </th>
                {showEmployee && (
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <button onClick={() => handleSort('employee_name')} className="flex items-center gap-1.5 hover:text-foreground">
                      {t('employee')} <SortIcon column="employee_name" />
                    </button>
                  </th>
                )}
                {showSuggestion && (
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    {t('suggestedMatch')}
                  </th>
                )}
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                  <button onClick={() => handleSort('license_type')} className="flex items-center gap-1.5 hover:text-foreground">
                    {t('type')} <SortIcon column="license_type" />
                  </button>
                </th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">
                  <button onClick={() => handleSort('monthly_cost')} className="flex items-center gap-1.5 justify-end hover:text-foreground ml-auto">
                    {t('cost')} <SortIcon column="monthly_cost" />
                  </button>
                </th>
                {hasActions && (
                  <th className="w-10 px-4 py-3"></th>
                )}
              </tr>
            </thead>
            <tbody>
              {paginatedLicenses.map((license) => (
                <tr
                  key={license.id}
                  className={`border-b last:border-0 hover:bg-muted/50 transition-colors ${
                    selectedIds?.has(license.id) ? 'bg-muted/50' : ''
                  }`}
                >
                  {showSelection && (
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(license.id)}
                        onChange={() => onToggleSelect(license.id)}
                        className="h-4 w-4 rounded border-input text-primary focus:ring-ring"
                      />
                    </td>
                  )}
                  {showProvider && (
                    <td className="px-4 py-3">
                      <Link href={`/providers/${license.provider_id}`} className="font-medium hover:underline">
                        {license.provider_name}
                      </Link>
                    </td>
                  )}
                  <td className="px-4 py-3">
                    <div>
                      {(() => {
                        // Get display name from various metadata fields (ensure string type)
                        const str = (v: unknown) => typeof v === 'string' ? v : undefined;
                        const displayName = str(license.metadata?.fullName)
                          || str(license.metadata?.fullname)
                          || str(license.metadata?.displayName)
                          || str(license.metadata?.display_name)
                          || str(license.metadata?.assignee_name);
                        const username = str(license.metadata?.username) || str(license.metadata?.hf_username);
                        const email = str(license.metadata?.email);
                        const externalId = license.external_user_id;
                        const isEmailLike = externalId?.includes('@');

                        return (
                          <>
                            {/* Show name prominently if available */}
                            {displayName && (
                              <span className="font-medium block">
                                {displayName}
                              </span>
                            )}
                            {/* Show email or external_user_id */}
                            <span className={`text-muted-foreground ${displayName ? 'text-xs' : ''}`}>
                              {email || (isEmailLike ? externalId : null) || (username ? `@${username}` : externalId)}
                            </span>
                            {/* Show username if we have a name but username is different */}
                            {displayName && username && !email && (
                              <span className="block text-xs text-muted-foreground/60">
                                @{username}
                              </span>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  </td>
                  {showEmployee && (
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        {/* Service account with owner */}
                        {license.is_service_account && license.service_account_owner_id && (
                          <Link href={`/users/${license.service_account_owner_id}`} className="flex items-center gap-2 hover:text-foreground group">
                            <div className="h-6 w-6 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center group-hover:bg-blue-200 dark:group-hover:bg-blue-800 transition-colors">
                              <span className="text-xs font-medium text-blue-600 dark:text-blue-400">{license.service_account_owner_name?.charAt(0) || 'O'}</span>
                            </div>
                            <span className="hover:underline text-muted-foreground text-xs">{t('owner')}: {license.service_account_owner_name}</span>
                          </Link>
                        )}
                        {/* Regular employee assignment */}
                        {!license.is_service_account && license.employee_id && license.employee_status !== 'offboarded' && (
                          <Link href={`/users/${license.employee_id}`} className="flex items-center gap-2 hover:text-foreground group">
                            <div className="h-6 w-6 rounded-full bg-muted flex items-center justify-center group-hover:bg-accent transition-colors">
                              <span className="text-xs font-medium">{license.employee_name?.charAt(0)}</span>
                            </div>
                            <span className="hover:underline">{license.employee_name}</span>
                          </Link>
                        )}
                        {!license.is_service_account && license.employee_id && license.employee_status === 'offboarded' && (
                          <Link href={`/users/${license.employee_id}`} className="flex items-center gap-2 hover:text-foreground group">
                            <div className="h-6 w-6 rounded-full bg-red-100 dark:bg-red-900 flex items-center justify-center">
                              <span className="text-xs font-medium text-red-600 dark:text-red-400">{license.employee_name?.charAt(0)}</span>
                            </div>
                            <span className="hover:underline text-muted-foreground line-through">{license.employee_name}</span>
                          </Link>
                        )}
                        <LicenseStatusBadge license={license} showUnassigned={!license.employee_id && !license.is_service_account} />
                      </div>
                    </td>
                  )}
                  {showSuggestion && (
                    <td className="px-4 py-3">
                      {license.suggested_employee_id ? (
                        <div className="flex items-center gap-3">
                          <div className="flex items-center gap-2">
                            <div className="h-6 w-6 rounded-full bg-amber-100 dark:bg-amber-900 flex items-center justify-center">
                              <Lightbulb className="h-3 w-3 text-amber-600 dark:text-amber-400" />
                            </div>
                            <div className="flex flex-col">
                              <span className="text-sm font-medium">{license.suggested_employee_name}</span>
                              <span className="text-xs text-muted-foreground">
                                {license.match_confidence ? `${Math.round(license.match_confidence * 100)}%` : ''} {license.match_method && `(${license.match_method})`}
                              </span>
                            </div>
                          </div>
                          {hasMatchActions && (
                            <div className="flex items-center gap-1">
                              {onConfirmMatch && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-7 w-7 p-0 text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 hover:bg-emerald-50 dark:hover:bg-emerald-950"
                                  onClick={() => onConfirmMatch(license)}
                                  title={t('confirmMatch')}
                                >
                                  <Check className="h-4 w-4" />
                                </Button>
                              )}
                              {onRejectMatch && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-7 w-7 p-0 text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-950"
                                  onClick={() => onRejectMatch(license)}
                                  title={t('rejectMatch')}
                                >
                                  <X className="h-4 w-4" />
                                </Button>
                              )}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-sm">-</span>
                      )}
                    </td>
                  )}
                  <td className="px-4 py-3 text-muted-foreground">
                    <div>
                      <span>{license.license_type_display_name || license.license_type || '-'}</span>
                      {license.license_type_display_name && license.license_type && (
                        <span className="block text-xs text-muted-foreground/60 font-mono">{license.license_type}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-sm">
                    {license.monthly_cost ? formatMonthlyCost(license.monthly_cost, license.currency) : '-'}
                  </td>
                  {hasActions && (
                    <td className="px-4 py-3">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {onServiceAccountClick && (
                            <DropdownMenuItem onClick={() => onServiceAccountClick(license)}>
                              <Bot className="h-4 w-4 mr-2" />
                              {license.is_service_account ? t('editServiceAccount') : t('markAsServiceAccount')}
                            </DropdownMenuItem>
                          )}
                          {onAdminAccountClick && (
                            <DropdownMenuItem onClick={() => onAdminAccountClick(license)}>
                              <ShieldCheck className="h-4 w-4 mr-2" />
                              {license.is_admin_account ? t('editAdminAccount') : t('markAsAdminAccount')}
                            </DropdownMenuItem>
                          )}
                          {onLicenseTypeClick && (
                            <DropdownMenuItem onClick={() => onLicenseTypeClick(license)}>
                              <Tags className="h-4 w-4 mr-2" />
                              {t('changeLicenseType')}
                            </DropdownMenuItem>
                          )}
                          {onAssignClick && !license.is_service_account && (
                            <DropdownMenuItem onClick={() => onAssignClick(license)}>
                              <UserPlus className="h-4 w-4 mr-2" />
                              {t('assignToEmployee')}
                            </DropdownMenuItem>
                          )}
                          {(onServiceAccountClick || onAdminAccountClick || onAssignClick) && (onDeleteClick || onCancelClick) && (
                            <DropdownMenuSeparator />
                          )}
                          {onCancelClick && license.status === 'active' && (
                            <DropdownMenuItem
                              onClick={() => onCancelClick(license)}
                              className="text-red-600 focus:text-red-600"
                            >
                              <Ban className="h-4 w-4 mr-2" />
                              {tLifecycle('cancelLicense')}
                            </DropdownMenuItem>
                          )}
                          {onDeleteClick && (
                            <DropdownMenuItem
                              onClick={() => onDeleteClick(license)}
                              className="text-red-600 focus:text-red-600"
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              {tCommon('delete')}
                            </DropdownMenuItem>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      <Pagination
        page={page}
        totalPages={totalPages}
        totalItems={filteredLicenses.length}
        pageSize={pageSize}
        onPageChange={setPage}
      />
    </div>
  );
}

// Memoize to prevent unnecessary re-renders when parent state changes
export const LicenseTable = memo(LicenseTableComponent);
