'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { ChevronRight, Home } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  className?: string;
  showHome?: boolean;
}

export function Breadcrumbs({
  items,
  className,
  showHome = true,
}: BreadcrumbsProps) {
  const t = useTranslations('nav');
  const allItems: BreadcrumbItem[] = showHome
    ? [{ label: t('dashboard'), href: '/dashboard' }, ...items]
    : items;

  return (
    <nav className={cn('flex items-center text-sm', className)} aria-label={t('breadcrumb')}>
      <ol className="flex items-center gap-1">
        {allItems.map((item, index) => {
          const isLast = index === allItems.length - 1;
          const isHome = index === 0 && showHome;

          return (
            <li key={index} className="flex items-center">
              {index > 0 && (
                <ChevronRight className="h-3.5 w-3.5 mx-1.5 text-muted-foreground" />
              )}
              {item.href && !isLast ? (
                <Link
                  href={item.href}
                  className="text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
                >
                  {isHome && <Home className="h-3.5 w-3.5" />}
                  {!isHome && item.label}
                </Link>
              ) : (
                <span
                  className={cn(
                    'flex items-center gap-1',
                    isLast ? 'text-foreground font-medium' : 'text-muted-foreground'
                  )}
                >
                  {isHome && <Home className="h-3.5 w-3.5" />}
                  {(!isHome || isLast) && item.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
