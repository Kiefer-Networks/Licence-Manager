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
import { Search, Building2 } from 'lucide-react';
import { Provider } from '@/lib/api';

interface LicenseFiltersProps {
  search: string;
  onSearchChange: (value: string) => void;
  selectedProvider: string;
  onProviderChange: (value: string) => void;
  selectedDepartment: string;
  onDepartmentChange: (value: string) => void;
  providers: Provider[];
  departments: string[];
  filteredCount: number;
  onClearFilters: () => void;
}

export function LicenseFilters({
  search,
  onSearchChange,
  selectedProvider,
  onProviderChange,
  selectedDepartment,
  onDepartmentChange,
  providers,
  departments,
  filteredCount,
  onClearFilters,
}: LicenseFiltersProps) {
  const t = useTranslations('licenses');

  const hasActiveFilters = selectedProvider !== 'all' || selectedDepartment !== 'all';

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="relative flex-1 min-w-[200px]">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
        <Input
          placeholder={t('searchPlaceholder')}
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-9 h-9 bg-zinc-50 border-zinc-200"
        />
      </div>

      <Select value={selectedProvider} onValueChange={onProviderChange}>
        <SelectTrigger className="w-36 h-9 text-sm bg-zinc-50 border-zinc-200">
          <SelectValue placeholder={t('provider')} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">{t('allProviders')}</SelectItem>
          {providers.map((p) => (
            <SelectItem key={p.id} value={p.id}>{p.display_name}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={selectedDepartment} onValueChange={onDepartmentChange}>
        <SelectTrigger className="w-36 h-9 text-sm bg-zinc-50 border-zinc-200">
          <Building2 className="h-4 w-4 mr-2 text-zinc-400" />
          <SelectValue placeholder={t('department')} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">{t('allDepartments')}</SelectItem>
          {departments.map((dept) => (
            <SelectItem key={dept} value={dept}>{dept}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      {hasActiveFilters && (
        <Button
          variant="ghost"
          size="sm"
          className="h-9 text-sm text-muted-foreground hover:text-foreground"
          onClick={onClearFilters}
        >
          {t('clearFilters')}
        </Button>
      )}

      <span className="text-sm text-muted-foreground ml-auto">
        {t('licenseCount', { count: filteredCount })}
      </span>
    </div>
  );
}
