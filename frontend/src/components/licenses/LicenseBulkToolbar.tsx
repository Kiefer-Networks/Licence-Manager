'use client';

import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { CheckSquare, UserX, UserMinus, Trash2, X } from 'lucide-react';

export type BulkAction = 'remove' | 'delete' | 'unassign';

interface LicenseBulkToolbarProps {
  selectedCount: number;
  assignedCount: number;
  removableCount: number;
  onUnassign: () => void;
  onRemove: () => void;
  onDelete: () => void;
  onClear: () => void;
}

export function LicenseBulkToolbar({
  selectedCount,
  assignedCount,
  removableCount,
  onUnassign,
  onRemove,
  onDelete,
  onClear,
}: LicenseBulkToolbarProps) {
  const t = useTranslations('licenses');

  if (selectedCount === 0) return null;

  return (
    <div className="flex items-center gap-3 p-3 bg-zinc-900 text-white rounded-lg">
      <CheckSquare className="h-4 w-4" />
      <span className="text-sm font-medium">{t('selectedCount', { count: selectedCount })}</span>
      <div className="flex-1" />
      {assignedCount > 0 && (
        <Button
          variant="ghost"
          size="sm"
          className="text-white hover:bg-zinc-800"
          onClick={onUnassign}
        >
          <UserX className="h-4 w-4 mr-1.5" />
          {t('unassignCount', { count: assignedCount })}
        </Button>
      )}
      {removableCount > 0 && (
        <Button
          variant="ghost"
          size="sm"
          className="text-white hover:bg-zinc-800"
          onClick={onRemove}
        >
          <UserMinus className="h-4 w-4 mr-1.5" />
          {t('removeFromProviderCount', { count: removableCount })}
        </Button>
      )}
      <Button
        variant="ghost"
        size="sm"
        className="text-white hover:bg-zinc-800"
        onClick={onDelete}
      >
        <Trash2 className="h-4 w-4 mr-1.5" />
        {t('deleteFromDatabase')}
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="text-zinc-400 hover:text-white hover:bg-zinc-800"
        onClick={onClear}
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  );
}
