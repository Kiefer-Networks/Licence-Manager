'use client';

import { useTranslations } from 'next-intl';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DateRangePicker, DatePreset } from './DateRangePicker';
import { Search, Filter, Download, X } from 'lucide-react';

interface AuditUser {
  id: string;
  email: string;
}

interface AuditFiltersProps {
  // Search
  search: string;
  onSearchChange: (value: string) => void;

  // Date range
  datePreset: DatePreset;
  dateFrom: string;
  dateTo: string;
  onDatePresetChange: (preset: DatePreset) => void;
  onDateFromChange: (date: string) => void;
  onDateToChange: (date: string) => void;

  // Filters
  actionFilter: string;
  resourceTypeFilter: string;
  userFilter: string;
  onActionFilterChange: (value: string) => void;
  onResourceTypeFilterChange: (value: string) => void;
  onUserFilterChange: (value: string) => void;

  // Options
  availableActions: string[];
  availableResourceTypes: string[];
  availableUsers: AuditUser[];

  // Actions
  onClearFilters: () => void;
  onExport: () => void;
  isExporting: boolean;

  // Stats
  totalEntries: number;
}

export function AuditFilters({
  search,
  onSearchChange,
  datePreset,
  dateFrom,
  dateTo,
  onDatePresetChange,
  onDateFromChange,
  onDateToChange,
  actionFilter,
  resourceTypeFilter,
  userFilter,
  onActionFilterChange,
  onResourceTypeFilterChange,
  onUserFilterChange,
  availableActions,
  availableResourceTypes,
  availableUsers,
  onClearFilters,
  onExport,
  isExporting,
  totalEntries,
}: AuditFiltersProps) {
  const t = useTranslations('audit');
  const tCommon = useTranslations('common');

  const hasFilters =
    search ||
    datePreset !== 'custom' ||
    dateFrom ||
    dateTo ||
    actionFilter ||
    resourceTypeFilter ||
    userFilter;

  return (
    <div className="space-y-4 bg-zinc-50 border rounded-lg p-4">
      {/* Search row */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={t('searchPlaceholder')}
          className="pl-10 bg-white"
        />
      </div>

      {/* Date range row */}
      <div className="flex items-center gap-4">
        <span className="text-sm font-medium text-muted-foreground">
          {t('dateRange')}:
        </span>
        <DateRangePicker
          preset={datePreset}
          dateFrom={dateFrom}
          dateTo={dateTo}
          onPresetChange={onDatePresetChange}
          onDateFromChange={onDateFromChange}
          onDateToChange={onDateToChange}
          onClear={() => {
            onDatePresetChange('custom');
            onDateFromChange('');
            onDateToChange('');
          }}
        />
      </div>

      {/* Filters row */}
      <div className="flex items-center gap-3 flex-wrap">
        <Filter className="h-4 w-4 text-muted-foreground" />

        <Select
          value={actionFilter || '__all__'}
          onValueChange={(v) => onActionFilterChange(v === '__all__' ? '' : v)}
        >
          <SelectTrigger className="w-[160px] bg-white">
            <SelectValue placeholder={t('allActions')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">{t('allActions')}</SelectItem>
            {availableActions.map((action) => (
              <SelectItem key={action} value={action}>
                {action}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={resourceTypeFilter || '__all__'}
          onValueChange={(v) => onResourceTypeFilterChange(v === '__all__' ? '' : v)}
        >
          <SelectTrigger className="w-[180px] bg-white">
            <SelectValue placeholder={t('allResources')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">{t('allResources')}</SelectItem>
            {availableResourceTypes.map((type) => (
              <SelectItem key={type} value={type}>
                {type}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={userFilter || '__all__'}
          onValueChange={(v) => onUserFilterChange(v === '__all__' ? '' : v)}
        >
          <SelectTrigger className="w-[220px] bg-white">
            <SelectValue placeholder={t('allUsers')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">{t('allUsers')}</SelectItem>
            {availableUsers.map((user) => (
              <SelectItem key={user.id} value={user.id}>
                {user.email}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {hasFilters && (
          <Button variant="ghost" size="sm" onClick={onClearFilters}>
            <X className="h-4 w-4 mr-1" />
            {t('clearFilters')}
          </Button>
        )}

        <div className="flex-1" />

        <span className="text-sm text-muted-foreground">
          {t('entries', { count: totalEntries })}
        </span>

        <Button
          variant="outline"
          size="sm"
          onClick={onExport}
          disabled={isExporting}
        >
          <Download className="h-4 w-4 mr-2" />
          {t('export')}
        </Button>
      </div>
    </div>
  );
}
