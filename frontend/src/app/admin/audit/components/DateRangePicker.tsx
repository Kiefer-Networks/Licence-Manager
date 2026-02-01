'use client';

import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Calendar, X } from 'lucide-react';

export type DatePreset = 'today' | 'last7Days' | 'last30Days' | 'custom';

interface DateRangePickerProps {
  preset: DatePreset;
  dateFrom: string;
  dateTo: string;
  onPresetChange: (preset: DatePreset) => void;
  onDateFromChange: (date: string) => void;
  onDateToChange: (date: string) => void;
  onClear: () => void;
}

export function DateRangePicker({
  preset,
  dateFrom,
  dateTo,
  onPresetChange,
  onDateFromChange,
  onDateToChange,
  onClear,
}: DateRangePickerProps) {
  const t = useTranslations('audit');

  const hasDateFilter = preset !== 'custom' || dateFrom || dateTo;

  return (
    <div className="flex items-center gap-2">
      <Calendar className="h-4 w-4 text-muted-foreground" />
      <Select
        value={preset}
        onValueChange={(v) => onPresetChange(v as DatePreset)}
      >
        <SelectTrigger className="w-[160px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="today">{t('today')}</SelectItem>
          <SelectItem value="last7Days">{t('last7Days')}</SelectItem>
          <SelectItem value="last30Days">{t('last30Days')}</SelectItem>
          <SelectItem value="custom">{t('custom')}</SelectItem>
        </SelectContent>
      </Select>

      {preset === 'custom' && (
        <>
          <span className="text-sm text-muted-foreground">{t('from')}:</span>
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => onDateFromChange(e.target.value)}
            className="w-[150px]"
          />
          <span className="text-sm text-muted-foreground">{t('to')}:</span>
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => onDateToChange(e.target.value)}
            className="w-[150px]"
          />
        </>
      )}

      {hasDateFilter && (
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onClear}
          title={t('clearFilters')}
        >
          <X className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
