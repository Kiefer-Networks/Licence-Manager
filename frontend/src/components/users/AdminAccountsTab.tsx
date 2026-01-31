'use client';

import { useEffect, useState } from 'react';
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
} from 'lucide-react';

interface AdminAccountsTabProps {
  providers: Provider[];
  showToast: (type: 'success' | 'error' | 'info', text: string) => void;
}

export function AdminAccountsTab({ providers, showToast }: AdminAccountsTabProps) {
  // Patterns state
  const [patterns, setPatterns] = useState<AdminAccountPattern[]>([]);
  const [loadingPatterns, setLoadingPatterns] = useState(true);
  const [showAddPattern, setShowAddPattern] = useState(false);
  const [newPattern, setNewPattern] = useState({
    email_pattern: '',
    name: '',
    owner_id: '',
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
      showToast('error', 'Failed to load patterns');
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
      showToast('error', 'Failed to load admin account licenses');
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
      showToast('error', 'Failed to load matching licenses');
    } finally {
      setLoadingMatches(false);
    }
  };

  const handleCreatePattern = async () => {
    if (!newPattern.email_pattern.trim()) {
      showToast('error', 'Email pattern is required');
      return;
    }

    setCreatingPattern(true);
    try {
      await api.createAdminAccountPattern({
        email_pattern: newPattern.email_pattern.trim(),
        name: newPattern.name.trim() || undefined,
        owner_id: newPattern.owner_id || undefined,
        notes: newPattern.notes.trim() || undefined,
      });
      showToast('success', 'Pattern created');
      setShowAddPattern(false);
      setNewPattern({ email_pattern: '', name: '', owner_id: '', notes: '' });
      loadPatterns();
    } catch (error: any) {
      showToast('error', error.message || 'Failed to create pattern');
    } finally {
      setCreatingPattern(false);
    }
  };

  const handleDeletePattern = async (patternId: string) => {
    setDeletingPatternId(patternId);
    try {
      await api.deleteAdminAccountPattern(patternId);
      showToast('success', 'Pattern deleted');
      loadPatterns();
    } catch (error) {
      showToast('error', 'Failed to delete pattern');
    } finally {
      setDeletingPatternId(null);
    }
  };

  const handleApplyPatterns = async () => {
    setApplyingPatterns(true);
    try {
      const result = await api.applyAdminAccountPatterns();
      if (result.updated_count > 0) {
        showToast('success', `Marked ${result.updated_count} license(s) as admin accounts`);
        loadLicenses();
        loadPatterns();
      } else {
        showToast('info', 'No new licenses matched');
      }
    } catch (error) {
      showToast('error', 'Failed to apply patterns');
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
        owner_id: makeGlobalLicense.admin_account_owner_id || undefined,
      });
      showToast('success', 'Pattern created - this email will now be recognized globally');
      setMakeGlobalLicense(null);
      loadPatterns();
    } catch (error: any) {
      showToast('error', error.message || 'Failed to create pattern');
    } finally {
      setMakingGlobal(false);
    }
  };

  const SortIcon = ({ column }: { column: string }) => {
    if (licensesSortColumn !== column) return <ChevronsUpDown className="h-3.5 w-3.5 text-zinc-400" />;
    return licensesSortDir === 'asc' ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />;
  };

  const licensesPageSize = 50;
  const licensesTotalPages = Math.ceil(licensesTotal / licensesPageSize);

  return (
    <div className="space-y-8">
      {/* Global Patterns Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-medium">Global Patterns</h2>
            <p className="text-sm text-muted-foreground">
              Email patterns that automatically mark licenses as admin accounts during sync
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
              Apply to All Licenses
            </Button>
            <Button size="sm" onClick={() => setShowAddPattern(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Pattern
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
              <p className="text-sm">No patterns configured</p>
              <p className="text-xs">Add a pattern to automatically detect admin accounts</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-zinc-50/50">
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Pattern</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Name</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Owner</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Matches</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">Actions</th>
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

      {/* Admin Account Licenses Section */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-medium">Admin Account Licenses</h2>
          <p className="text-sm text-muted-foreground">
            All licenses currently marked as admin accounts
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
            <Input
              placeholder="Search by email..."
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
              <SelectValue placeholder="Provider" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Providers</SelectItem>
              {providers.map((provider) => (
                <SelectItem key={provider.id} value={provider.id}>
                  {provider.display_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <span className="text-sm text-muted-foreground ml-auto">
            {licensesTotal} license{licensesTotal !== 1 ? 's' : ''}
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
              <ShieldCheck className="h-8 w-8 mb-2 opacity-30" />
              <p className="text-sm">No admin account licenses</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-zinc-50/50">
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <button onClick={() => handleLicenseSort('external_user_id')} className="flex items-center gap-1.5 hover:text-foreground">
                      Email <SortIcon column="external_user_id" />
                    </button>
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Provider</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Name</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Owner</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">Global</th>
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
                      {license.admin_account_name || '-'}
                    </td>
                    <td className="px-4 py-3">
                      {license.admin_account_owner_name ? (
                        <div className="flex items-center gap-1.5">
                          <User className="h-3.5 w-3.5 text-muted-foreground" />
                          <span className={license.admin_account_owner_status === 'offboarded' ? 'text-red-600' : 'text-muted-foreground'}>
                            {license.admin_account_owner_name}
                          </span>
                          {license.admin_account_owner_status === 'offboarded' && (
                            <span title="Owner offboarded"><AlertTriangle className="h-3.5 w-3.5 text-red-500" /></span>
                          )}
                        </div>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={license.status === 'active' ? 'secondary' : 'outline'}
                             className={license.status === 'active' ? 'bg-emerald-50 text-emerald-700 border-0' : ''}>
                        {license.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {isEmailGlobal(license.external_user_id) ? (
                        <div
                          className="inline-flex items-center gap-1 text-emerald-600"
                          title="This email matches a global pattern"
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
                          title="Make global pattern"
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
              Page {licensesPage} of {licensesTotalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setLicensesPage(licensesPage - 1)}
                disabled={licensesPage === 1}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setLicensesPage(licensesPage + 1)}
                disabled={licensesPage === licensesTotalPages}
              >
                Next
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
              Matching Licenses
            </DialogTitle>
            <DialogDescription>
              Licenses matching pattern <code className="bg-zinc-100 px-2 py-0.5 rounded">{matchesDialog?.email_pattern}</code>
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
                <p className="text-sm">No matching licenses found</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-white">
                  <tr className="border-b bg-zinc-50/50">
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Email</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Provider</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">License Type</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Owner</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
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
                              <span title="Owner is offboarded"><AlertTriangle className="h-3.5 w-3.5 text-red-500" /></span>
                            )}
                          </div>
                        ) : (
                          <span className="text-muted-foreground text-xs">Not assigned</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={license.status === 'active' ? 'secondary' : 'outline'} className={license.status === 'active' ? 'bg-emerald-50 text-emerald-700' : ''}>
                          {license.status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setMatchesDialog(null)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Make Global Dialog */}
      <Dialog open={!!makeGlobalLicense} onOpenChange={(open) => !open && setMakeGlobalLicense(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Make Global Pattern</DialogTitle>
            <DialogDescription>
              Add this email as a global pattern. All licenses with this email will automatically
              be marked as admin accounts.
            </DialogDescription>
          </DialogHeader>
          {makeGlobalLicense && (
            <div className="space-y-4 py-4">
              <div className="p-3 bg-zinc-50 rounded-lg space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">Email:</span>
                  <code className="text-sm bg-white px-2 py-0.5 rounded border">
                    {makeGlobalLicense.external_user_id}
                  </code>
                </div>
                {makeGlobalLicense.admin_account_name && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">Name:</span>
                    <span className="text-sm">{makeGlobalLicense.admin_account_name}</span>
                  </div>
                )}
                {makeGlobalLicense.admin_account_owner_name && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">Owner:</span>
                    <span className="text-sm">{makeGlobalLicense.admin_account_owner_name}</span>
                  </div>
                )}
              </div>
              <p className="text-sm text-muted-foreground">
                After adding this pattern, any future syncs will automatically mark licenses
                with this email as admin accounts.
              </p>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setMakeGlobalLicense(null)}>
              Cancel
            </Button>
            <Button onClick={handleMakeGlobal} disabled={makingGlobal}>
              {makingGlobal ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Globe className="h-4 w-4 mr-2" />
              )}
              Make Global
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Pattern Dialog */}
      <Dialog open={showAddPattern} onOpenChange={setShowAddPattern}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Admin Account Pattern</DialogTitle>
            <DialogDescription>
              Add an email pattern to automatically detect admin accounts.
              Use * for wildcard matching (e.g., *-admin@company.com).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="email_pattern">Email Pattern *</Label>
              <Input
                id="email_pattern"
                placeholder="*-admin@company.com"
                value={newPattern.email_pattern}
                onChange={(e) => setNewPattern({ ...newPattern, email_pattern: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                Use * for wildcards. Examples: max-admin@company.com, *-admin@company.com
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                placeholder="IT Admin"
                value={newPattern.name}
                onChange={(e) => setNewPattern({ ...newPattern, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="owner">Owner (optional)</Label>
              <Select value={newPattern.owner_id || '__none__'} onValueChange={(v) => setNewPattern({ ...newPattern, owner_id: v === '__none__' ? '' : v })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select owner..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">No owner</SelectItem>
                  {employees.map((emp) => (
                    <SelectItem key={emp.id} value={emp.id}>
                      {emp.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                placeholder="Optional notes about this admin account..."
                value={newPattern.notes}
                onChange={(e) => setNewPattern({ ...newPattern, notes: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddPattern(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreatePattern} disabled={creatingPattern}>
              {creatingPattern ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : null}
              Add Pattern
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
