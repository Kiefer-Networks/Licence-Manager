'use client';

import { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { AppLayout } from '@/components/layout/app-layout';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
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
import { Badge } from '@/components/ui/badge';
import { api, License, Provider } from '@/lib/api';
import { Search, ChevronUp, ChevronDown, ChevronsUpDown, Loader2, Key, Trash2, UserMinus, Building2, X, CheckSquare, UserX, Globe, Skull } from 'lucide-react';
import Link from 'next/link';

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
}

// Providers that support remote member removal
const REMOVABLE_PROVIDERS = ['cursor'];

export default function LicensesPage() {
  const searchParams = useSearchParams();
  const [licenses, setLicenses] = useState<License[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [departments, setDepartments] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [selectedProvider, setSelectedProvider] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
  const [unassignedOnly, setUnassignedOnly] = useState(searchParams.get('unassigned') === 'true');
  const [externalOnly, setExternalOnly] = useState(searchParams.get('external') === 'true');
  const [sortColumn, setSortColumn] = useState<string>('synced_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  // Multi-select state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkActionDialog, setBulkActionDialog] = useState<'remove' | 'delete' | 'unassign' | null>(null);
  const [bulkActionLoading, setBulkActionLoading] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const debouncedSearch = useDebounce(search, 300);
  const licenseProviders = providers.filter((p) => p.name !== 'hibob').sort((a, b) => a.display_name.localeCompare(b.display_name));

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const SortIcon = ({ column }: { column: string }) => {
    if (sortColumn !== column) return <ChevronsUpDown className="h-3.5 w-3.5 text-zinc-400" />;
    return sortDirection === 'asc' ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />;
  };

  // Load providers and departments once
  useEffect(() => {
    api.getProviders().then((data) => setProviders(data.items)).catch(console.error);
    api.getDepartments().then(setDepartments).catch(console.error);
  }, []);

  // Load licenses when filters change
  const loadLicenses = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getLicenses({
        page,
        search: debouncedSearch || undefined,
        provider_id: selectedProvider !== 'all' ? selectedProvider : undefined,
        status: selectedStatus !== 'all' ? selectedStatus : undefined,
        department: selectedDepartment !== 'all' ? selectedDepartment : undefined,
        unassigned: unassignedOnly,
        external: externalOnly,
        sort_by: sortColumn,
        sort_dir: sortDirection,
      });
      setLicenses(data.items);
      setTotal(data.total);
      // Clear selection when data changes
      setSelectedIds(new Set());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, selectedProvider, selectedStatus, selectedDepartment, unassignedOnly, externalOnly, sortColumn, sortDirection]);

  useEffect(() => {
    loadLicenses();
  }, [loadLicenses]);

  // Selection handlers
  const toggleSelectAll = () => {
    if (selectedIds.size === licenses.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(licenses.map(l => l.id)));
    }
  };

  const toggleSelect = (id: string) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedIds(newSet);
  };

  // Get selected licenses info
  const selectedLicenses = licenses.filter(l => selectedIds.has(l.id));
  const removableLicenses = selectedLicenses.filter(l => {
    const provider = providers.find(p => p.id === l.provider_id);
    return provider && REMOVABLE_PROVIDERS.includes(provider.name);
  });
  const assignedLicenses = selectedLicenses.filter(l => l.employee_id);

  // Bulk actions
  const handleBulkRemove = async () => {
    if (removableLicenses.length === 0) return;
    setBulkActionLoading(true);
    try {
      const result = await api.bulkRemoveFromProvider(removableLicenses.map(l => l.id));
      setToast({
        message: `Removed ${result.successful} of ${result.total} licenses from providers`,
        type: result.failed > 0 ? 'error' : 'success',
      });
      setBulkActionDialog(null);
      loadLicenses();
    } catch (e) {
      setToast({ message: 'Failed to remove licenses', type: 'error' });
    } finally {
      setBulkActionLoading(false);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    setBulkActionLoading(true);
    try {
      const result = await api.bulkDeleteLicenses(Array.from(selectedIds));
      setToast({
        message: `Deleted ${result.successful} of ${result.total} licenses from database`,
        type: result.failed > 0 ? 'error' : 'success',
      });
      setBulkActionDialog(null);
      loadLicenses();
    } catch (e) {
      setToast({ message: 'Failed to delete licenses', type: 'error' });
    } finally {
      setBulkActionLoading(false);
    }
  };

  const handleBulkUnassign = async () => {
    if (assignedLicenses.length === 0) return;
    setBulkActionLoading(true);
    try {
      const result = await api.bulkUnassignLicenses(assignedLicenses.map(l => l.id));
      setToast({
        message: `Unassigned ${result.successful} of ${result.total} licenses`,
        type: result.failed > 0 ? 'error' : 'success',
      });
      setBulkActionDialog(null);
      loadLicenses();
    } catch (e) {
      setToast({ message: 'Failed to unassign licenses', type: 'error' });
    } finally {
      setBulkActionLoading(false);
    }
  };

  // Auto-hide toast
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const pageSize = 50;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="pt-2">
          <h1 className="text-2xl font-semibold tracking-tight">Licenses</h1>
          <p className="text-muted-foreground text-sm mt-0.5">Manage software licenses across all providers</p>
        </div>

        {/* Bulk Action Toolbar */}
        {selectedIds.size > 0 && (
          <div className="flex items-center gap-3 p-3 bg-zinc-900 text-white rounded-lg">
            <CheckSquare className="h-4 w-4" />
            <span className="text-sm font-medium">{selectedIds.size} selected</span>
            <div className="flex-1" />
            {assignedLicenses.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="text-white hover:bg-zinc-800"
                onClick={() => setBulkActionDialog('unassign')}
              >
                <UserX className="h-4 w-4 mr-1.5" />
                Unassign ({assignedLicenses.length})
              </Button>
            )}
            {removableLicenses.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="text-white hover:bg-zinc-800"
                onClick={() => setBulkActionDialog('remove')}
              >
                <UserMinus className="h-4 w-4 mr-1.5" />
                Remove from Provider ({removableLicenses.length})
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="text-white hover:bg-zinc-800"
              onClick={() => setBulkActionDialog('delete')}
            >
              <Trash2 className="h-4 w-4 mr-1.5" />
              Delete from Database
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-zinc-400 hover:text-white hover:bg-zinc-800"
              onClick={() => setSelectedIds(new Set())}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* Search and Filters */}
        <div className="space-y-3">
          {/* Main Search */}
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
              <Input
                placeholder="Search by email, name, provider..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 h-10 bg-zinc-50 border-zinc-200"
              />
            </div>
            <span className="text-sm text-muted-foreground whitespace-nowrap">
              {total} license{total !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Quick Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground mr-1">Quick filters:</span>

            <Button
              variant={unassignedOnly ? 'default' : 'outline'}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setUnassignedOnly(!unassignedOnly)}
            >
              Unassigned
            </Button>

            <Button
              variant={externalOnly ? 'default' : 'outline'}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setExternalOnly(!externalOnly)}
            >
              <Globe className="h-3 w-3 mr-1" />
              External
            </Button>

            <div className="w-px h-5 bg-zinc-200 mx-1" />

            <Select value={selectedProvider} onValueChange={setSelectedProvider}>
              <SelectTrigger className="w-36 h-7 text-xs bg-zinc-50 border-zinc-200">
                <SelectValue placeholder="Provider" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Providers</SelectItem>
                {licenseProviders.map((p) => (
                  <SelectItem key={p.id} value={p.id}>{p.display_name}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selectedStatus} onValueChange={setSelectedStatus}>
              <SelectTrigger className="w-28 h-7 text-xs bg-zinc-50 border-zinc-200">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="suspended">Suspended</SelectItem>
              </SelectContent>
            </Select>

            <Select value={selectedDepartment} onValueChange={setSelectedDepartment}>
              <SelectTrigger className="w-36 h-7 text-xs bg-zinc-50 border-zinc-200">
                <SelectValue placeholder="Department" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Departments</SelectItem>
                {departments.map((dept) => (
                  <SelectItem key={dept} value={dept}>{dept}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Active Filter Tags */}
            {(selectedProvider !== 'all' || selectedStatus !== 'all' || selectedDepartment !== 'all' || unassignedOnly || externalOnly) && (
              <>
                <div className="w-px h-5 bg-zinc-200 mx-1" />
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs text-muted-foreground hover:text-foreground"
                  onClick={() => {
                    setSelectedProvider('all');
                    setSelectedStatus('all');
                    setSelectedDepartment('all');
                    setUnassignedOnly(false);
                    setExternalOnly(false);
                  }}
                >
                  Clear filters
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Table */}
        <div className="border rounded-lg bg-white overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
            </div>
          ) : licenses.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <Key className="h-8 w-8 mb-2 opacity-30" />
              <p className="text-sm">No licenses found</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-zinc-50/50">
                  <th className="w-10 px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.size === licenses.length && licenses.length > 0}
                      onChange={toggleSelectAll}
                      className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-500"
                    />
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <button onClick={() => handleSort('provider_name')} className="flex items-center gap-1.5 hover:text-foreground">
                      Provider <SortIcon column="provider_name" />
                    </button>
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <button onClick={() => handleSort('external_user_id')} className="flex items-center gap-1.5 hover:text-foreground">
                      User <SortIcon column="external_user_id" />
                    </button>
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <button onClick={() => handleSort('employee_name')} className="flex items-center gap-1.5 hover:text-foreground">
                      Employee <SortIcon column="employee_name" />
                    </button>
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Type</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <button onClick={() => handleSort('last_activity_at')} className="flex items-center gap-1.5 hover:text-foreground">
                      Last Active <SortIcon column="last_activity_at" />
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
                {licenses.map((license) => {
                  const provider = providers.find(p => p.id === license.provider_id);
                  const isRemovable = provider && REMOVABLE_PROVIDERS.includes(provider.name);

                  // Determine license status for badge display
                  const isExternal = license.is_external_email;
                  const isOffboarded = license.employee_status === 'offboarded';
                  const isUnassigned = !license.employee_id;

                  return (
                    <tr
                      key={license.id}
                      className={`border-b last:border-0 hover:bg-zinc-50/50 transition-colors ${selectedIds.has(license.id) ? 'bg-zinc-50' : ''}`}
                    >
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(license.id)}
                          onChange={() => toggleSelect(license.id)}
                          className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-500"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Link href={`/providers/${license.provider_id}`} className="font-medium hover:underline">
                            {license.provider_name}
                          </Link>
                          {isRemovable && (
                            <span className="text-[10px] px-1.5 py-0.5 bg-emerald-50 text-emerald-700 rounded">API</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{license.external_user_id}</td>
                      <td className="px-4 py-3">
                        {/* Priority: External > Offboarded > Assigned > Unassigned */}
                        {isExternal ? (
                          <Badge variant="outline" className="text-red-600 border-red-200 bg-red-50">
                            <Globe className="h-3 w-3 mr-1" />
                            External
                          </Badge>
                        ) : isOffboarded ? (
                          <div className="flex items-center gap-2">
                            <Link href={`/users/${license.employee_id}`} className="flex items-center gap-2 hover:text-zinc-900 group">
                              <div className="h-6 w-6 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                                <span className="text-xs font-medium text-red-600">
                                  {license.employee_name?.charAt(0)}
                                </span>
                              </div>
                              <span className="truncate text-muted-foreground line-through">{license.employee_name}</span>
                            </Link>
                            <Badge variant="outline" className="text-red-600 border-red-200 bg-red-50">
                              <Skull className="h-3 w-3 mr-1" />
                              Offboarded
                            </Badge>
                          </div>
                        ) : isUnassigned ? (
                          <Badge variant="outline" className="text-amber-600 border-amber-200 bg-amber-50">
                            Unassigned
                          </Badge>
                        ) : (
                          <Link href={`/users/${license.employee_id}`} className="flex items-center gap-2 hover:text-zinc-900 group">
                            <div className="h-6 w-6 rounded-full bg-zinc-100 flex items-center justify-center flex-shrink-0 group-hover:bg-zinc-200 transition-colors">
                              <span className="text-xs font-medium text-zinc-600">
                                {license.employee_name?.charAt(0)}
                              </span>
                            </div>
                            <span className="truncate hover:underline">{license.employee_name}</span>
                          </Link>
                        )}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        <div>
                          <span>{license.license_type_display_name || license.license_type || '-'}</span>
                          {license.license_type_display_name && license.license_type && (
                            <span className="block text-xs text-muted-foreground/60 font-mono">{license.license_type}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {license.last_activity_at ? new Date(license.last_activity_at).toLocaleDateString('de-DE') : '-'}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {license.monthly_cost ? `€${Number(license.monthly_cost).toFixed(2)}` : '-'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Page {page} of {totalPages}
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

      {/* Bulk Remove Dialog */}
      <Dialog open={bulkActionDialog === 'remove'} onOpenChange={() => setBulkActionDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove from Provider</DialogTitle>
            <DialogDescription>
              This will remove {removableLicenses.length} user(s) from their provider system via API.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-zinc-600 mb-3">The following actions will be performed:</p>
            <ul className="text-sm space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-emerald-600">•</span>
                <span>Users will be removed from the external provider (e.g., Cursor team)</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-600">•</span>
                <span>Licenses will be deleted from this database</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600">•</span>
                <span>Only Cursor licenses support remote removal ({removableLicenses.length} of {selectedIds.size} selected)</span>
              </li>
            </ul>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBulkActionDialog(null)} disabled={bulkActionLoading}>
              Cancel
            </Button>
            <Button onClick={handleBulkRemove} disabled={bulkActionLoading}>
              {bulkActionLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Remove {removableLicenses.length} Licenses
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Delete Dialog */}
      <Dialog open={bulkActionDialog === 'delete'} onOpenChange={() => setBulkActionDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete from Database</DialogTitle>
            <DialogDescription>
              This will delete {selectedIds.size} license(s) from the local database.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-zinc-600 mb-3">Important:</p>
            <ul className="text-sm space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-red-600">•</span>
                <span>This does NOT remove users from the external provider systems</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600">•</span>
                <span>Licenses may reappear after the next sync if users still exist in the provider</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-zinc-600">•</span>
                <span>Use "Remove from Provider" to actually revoke access</span>
              </li>
            </ul>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBulkActionDialog(null)} disabled={bulkActionLoading}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleBulkDelete} disabled={bulkActionLoading}>
              {bulkActionLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Delete {selectedIds.size} Licenses
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Unassign Dialog */}
      <Dialog open={bulkActionDialog === 'unassign'} onOpenChange={() => setBulkActionDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Unassign Licenses</DialogTitle>
            <DialogDescription>
              This will unassign {assignedLicenses.length} license(s) from their employees.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-zinc-600 mb-3">This action will:</p>
            <ul className="text-sm space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-amber-600">•</span>
                <span>Remove the employee association from the selected licenses</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-zinc-600">•</span>
                <span>Mark the licenses as "Unassigned" in the system</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-zinc-600">•</span>
                <span>The licenses remain in the database and users remain in the provider</span>
              </li>
            </ul>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBulkActionDialog(null)} disabled={bulkActionLoading}>
              Cancel
            </Button>
            <Button onClick={handleBulkUnassign} disabled={bulkActionLoading}>
              {bulkActionLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Unassign {assignedLicenses.length} Licenses
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-4 right-4 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
          toast.type === 'success' ? 'bg-zinc-900 text-white' : 'bg-red-600 text-white'
        }`}>
          {toast.message}
        </div>
      )}
    </AppLayout>
  );
}
