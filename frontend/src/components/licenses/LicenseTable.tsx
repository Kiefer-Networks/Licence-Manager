'use client';

import { useState, useMemo } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { License } from '@/lib/api';
import { formatMonthlyCost } from '@/lib/format';
import { LicenseStatusBadge } from './LicenseStatusBadge';
import { Search, ChevronUp, ChevronDown, ChevronsUpDown, Key } from 'lucide-react';
import Link from 'next/link';

interface LicenseTableProps {
  licenses: License[];
  showProvider?: boolean;
  showEmployee?: boolean;
  emptyMessage?: string;
  onSelect?: (license: License) => void;
  selectedIds?: Set<string>;
  onToggleSelect?: (id: string) => void;
  onToggleSelectAll?: () => void;
}

type SortColumn = 'external_user_id' | 'employee_name' | 'license_type' | 'monthly_cost' | 'provider_name';

export function LicenseTable({
  licenses,
  showProvider = true,
  showEmployee = true,
  emptyMessage = 'No licenses found',
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
}: LicenseTableProps) {
  const [search, setSearch] = useState('');
  const [sortColumn, setSortColumn] = useState<SortColumn>('external_user_id');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const SortIcon = ({ column }: { column: SortColumn }) => {
    if (sortColumn !== column) return <ChevronsUpDown className="h-3.5 w-3.5 text-zinc-400" />;
    return sortDirection === 'asc' ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />;
  };

  // Filter and sort licenses
  const filteredLicenses = useMemo(() => {
    let result = licenses;

    // Search filter
    if (search) {
      const searchLower = search.toLowerCase();
      result = result.filter(
        (l) =>
          l.external_user_id.toLowerCase().includes(searchLower) ||
          l.employee_name?.toLowerCase().includes(searchLower) ||
          l.employee_email?.toLowerCase().includes(searchLower) ||
          l.provider_name.toLowerCase().includes(searchLower) ||
          l.license_type?.toLowerCase().includes(searchLower)
      );
    }

    // Sort
    result = [...result].sort((a, b) => {
      let aVal: string | number = '';
      let bVal: string | number = '';

      switch (sortColumn) {
        case 'external_user_id':
          aVal = a.external_user_id.toLowerCase();
          bVal = b.external_user_id.toLowerCase();
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
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
        <Input
          placeholder="Search by email, name, provider..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="pl-9 h-9 bg-zinc-50 border-zinc-200"
        />
      </div>

      {/* Table */}
      <div className="border rounded-lg bg-white overflow-hidden">
        {paginatedLicenses.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
            <Key className="h-8 w-8 mb-2 opacity-30" />
            <p className="text-sm">{emptyMessage}</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-zinc-50/50">
                {showSelection && (
                  <th className="w-10 px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.size === paginatedLicenses.length && paginatedLicenses.length > 0}
                      onChange={onToggleSelectAll}
                      className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-500"
                    />
                  </th>
                )}
                {showProvider && (
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <button onClick={() => handleSort('provider_name')} className="flex items-center gap-1.5 hover:text-foreground">
                      Provider <SortIcon column="provider_name" />
                    </button>
                  </th>
                )}
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                  <button onClick={() => handleSort('external_user_id')} className="flex items-center gap-1.5 hover:text-foreground">
                    License <SortIcon column="external_user_id" />
                  </button>
                </th>
                {showEmployee && (
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <button onClick={() => handleSort('employee_name')} className="flex items-center gap-1.5 hover:text-foreground">
                      Employee <SortIcon column="employee_name" />
                    </button>
                  </th>
                )}
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                  <button onClick={() => handleSort('license_type')} className="flex items-center gap-1.5 hover:text-foreground">
                    Type <SortIcon column="license_type" />
                  </button>
                </th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">
                  <button onClick={() => handleSort('monthly_cost')} className="flex items-center gap-1.5 justify-end hover:text-foreground ml-auto">
                    Cost <SortIcon column="monthly_cost" />
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {paginatedLicenses.map((license) => (
                <tr
                  key={license.id}
                  className={`border-b last:border-0 hover:bg-zinc-50/50 transition-colors ${
                    selectedIds?.has(license.id) ? 'bg-zinc-50' : ''
                  }`}
                >
                  {showSelection && (
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(license.id)}
                        onChange={() => onToggleSelect(license.id)}
                        className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-500"
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
                    <span className="text-muted-foreground">{license.external_user_id}</span>
                  </td>
                  {showEmployee && (
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        {license.employee_id && license.employee_status !== 'offboarded' && (
                          <Link href={`/users/${license.employee_id}`} className="flex items-center gap-2 hover:text-zinc-900 group">
                            <div className="h-6 w-6 rounded-full bg-zinc-100 flex items-center justify-center group-hover:bg-zinc-200 transition-colors">
                              <span className="text-xs font-medium">{license.employee_name?.charAt(0)}</span>
                            </div>
                            <span className="hover:underline">{license.employee_name}</span>
                          </Link>
                        )}
                        {license.employee_id && license.employee_status === 'offboarded' && (
                          <Link href={`/users/${license.employee_id}`} className="flex items-center gap-2 hover:text-zinc-900 group">
                            <div className="h-6 w-6 rounded-full bg-red-100 flex items-center justify-center">
                              <span className="text-xs font-medium text-red-600">{license.employee_name?.charAt(0)}</span>
                            </div>
                            <span className="hover:underline text-muted-foreground line-through">{license.employee_name}</span>
                          </Link>
                        )}
                        <LicenseStatusBadge license={license} showUnassigned={!license.employee_id} />
                      </div>
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
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {page} of {totalPages} ({filteredLicenses.length} total)
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setPage(page - 1)} disabled={page === 1}>
              Previous
            </Button>
            <Button variant="outline" size="sm" onClick={() => setPage(page + 1)} disabled={page === totalPages}>
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
