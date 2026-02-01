'use client';

import { cn } from '@/lib/utils';
import { useTranslations } from 'next-intl';
import { LucideIcon, FileQuestion } from 'lucide-react';
import { Button } from './button';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({
  icon: Icon = FileQuestion,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-12 px-4 text-center',
        className
      )}
    >
      <div className="h-12 w-12 rounded-full bg-zinc-100 flex items-center justify-center mb-4">
        <Icon className="h-6 w-6 text-zinc-400" />
      </div>
      <h3 className="text-sm font-medium text-zinc-900 mb-1">{title}</h3>
      {description && (
        <p className="text-sm text-zinc-500 max-w-sm">{description}</p>
      )}
      {action && (
        <Button
          variant="outline"
          size="sm"
          onClick={action.onClick}
          className="mt-4"
        >
          {action.label}
        </Button>
      )}
    </div>
  );
}

// Pre-built empty states for common scenarios

export function NoDataEmptyState({ onRefresh }: { onRefresh?: () => void }) {
  const t = useTranslations('common');
  return (
    <EmptyState
      title={t('noData')}
      description=""
      action={onRefresh ? { label: t('refresh'), onClick: onRefresh } : undefined}
    />
  );
}

export function NoResultsEmptyState({ onClear }: { onClear?: () => void }) {
  const t = useTranslations('common');
  const tLicenses = useTranslations('licenses');
  return (
    <EmptyState
      title={t('noResults')}
      description=""
      action={onClear ? { label: tLicenses('clearFilters'), onClick: onClear } : undefined}
    />
  );
}

export function ErrorEmptyState({
  message,
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  const t = useTranslations('common');
  const tErrors = useTranslations('errors');
  return (
    <EmptyState
      title={tErrors('generic')}
      description={message || ''}
      action={onRetry ? { label: t('tryAgain'), onClick: onRetry } : undefined}
    />
  );
}
