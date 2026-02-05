'use client';

import { useTranslations } from 'next-intl';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface PaginationProps {
  page: number;
  totalPages: number;
  totalItems?: number;
  onPageChange: (page: number) => void;
  showItemCount?: boolean;
  pageSize?: number;
  showFirstLast?: boolean;
  className?: string;
}

export function Pagination({
  page,
  totalPages,
  totalItems,
  onPageChange,
  showItemCount = true,
  pageSize,
  showFirstLast = false,
  className = '',
}: PaginationProps) {
  const t = useTranslations('common');

  if (totalPages <= 1) {
    return null;
  }

  const startItem = pageSize ? (page - 1) * pageSize + 1 : undefined;
  const endItem = pageSize && totalItems
    ? Math.min(page * pageSize, totalItems)
    : undefined;

  return (
    <div className={`flex items-center justify-between ${className}`}>
      <p className="text-sm text-muted-foreground">
        {showItemCount && totalItems !== undefined ? (
          startItem && endItem ? (
            t('showingRange', { start: startItem, end: endItem, total: totalItems })
          ) : (
            t('pageOfTotal', { page, total: totalPages, items: totalItems })
          )
        ) : (
          t('pageOf', { page, total: totalPages })
        )}
      </p>
      <div className="flex gap-1">
        {showFirstLast && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(1)}
            disabled={page === 1}
            className="h-8 w-8 p-0"
          >
            <ChevronsLeft className="h-4 w-4" />
            <span className="sr-only">{t('firstPage')}</span>
          </Button>
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          {t('previous')}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page + 1)}
          disabled={page === totalPages}
        >
          {t('next')}
          <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
        {showFirstLast && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(totalPages)}
            disabled={page === totalPages}
            className="h-8 w-8 p-0"
          >
            <ChevronsRight className="h-4 w-4" />
            <span className="sr-only">{t('lastPage')}</span>
          </Button>
        )}
      </div>
    </div>
  );
}
