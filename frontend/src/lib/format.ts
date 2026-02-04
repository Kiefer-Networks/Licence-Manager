/**
 * Formatting utilities for dates, currencies, and other common formats.
 * These functions use default locale settings.
 * For user-preference-aware formatting, use the useLocale() hook from locale-provider.
 */

import { getLocale } from './locale';

// Currency symbols mapping
export const CURRENCY_SYMBOLS: Record<string, string> = {
  EUR: '\u20AC',
  USD: '$',
  GBP: '\u00A3',
  CHF: 'CHF',
};

// Number format locale mapping
export const NUMBER_FORMAT_LOCALES: Record<string, string> = {
  'de-DE': 'de-DE',
  'en-US': 'en-US',
  'de-CH': 'de-CH',
};

// Date format patterns
export type DateFormatPattern = 'DD.MM.YYYY' | 'MM/DD/YYYY' | 'YYYY-MM-DD';

/**
 * Format a date according to user preference pattern
 */
export function formatDateWithPattern(
  date: string | Date | null | undefined,
  pattern: DateFormatPattern = 'DD.MM.YYYY'
): string {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '-';

  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();

  switch (pattern) {
    case 'MM/DD/YYYY':
      return `${month}/${day}/${year}`;
    case 'YYYY-MM-DD':
      return `${year}-${month}-${day}`;
    case 'DD.MM.YYYY':
    default:
      return `${day}.${month}.${year}`;
  }
}

/**
 * Format a number according to user preference locale
 */
export function formatNumberWithLocale(
  value: number | string | null | undefined,
  locale: string = 'de-DE',
  decimals: number = 2
): string {
  if (value === null || value === undefined || value === '') return '-';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '-';

  const numberLocale = NUMBER_FORMAT_LOCALES[locale] || 'de-DE';
  return new Intl.NumberFormat(numberLocale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(num);
}

/**
 * Format currency according to user preferences
 */
export function formatCurrencyWithPrefs(
  value: number | string | null | undefined,
  currency: string = 'EUR',
  numberLocale: string = 'de-DE'
): string {
  if (value === null || value === undefined || value === '') return '-';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '-';

  const locale = NUMBER_FORMAT_LOCALES[numberLocale] || 'de-DE';
  const symbol = CURRENCY_SYMBOLS[currency] || currency;

  const formatted = new Intl.NumberFormat(locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);

  // Format with proper currency symbol placement
  if (currency === 'EUR' || currency === 'GBP') {
    return `${formatted} ${symbol}`;
  }
  return `${symbol}${formatted}`;
}

/**
 * Format a date as relative time (e.g., "2 hours ago", "3 days ago")
 */
export function formatRelativeTime(date: string | Date, dateFormat: DateFormatPattern = 'DD.MM.YYYY'): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  const diffWeek = Math.floor(diffDay / 7);
  const diffMonth = Math.floor(diffDay / 30);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  if (diffWeek < 4) return `${diffWeek}w ago`;
  if (diffMonth < 12) return `${diffMonth}mo ago`;

  return formatDateWithPattern(d, dateFormat);
}

/**
 * Format a date for display (uses browser locale - for backwards compatibility)
 */
export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString(getLocale(), {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

/**
 * Format a date with time
 */
export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleString(getLocale(), {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format a date with time including seconds
 */
export function formatDateTimeWithSeconds(date: string | Date | null | undefined): string {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleString(getLocale(), {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Format currency for display (uses browser locale - for backwards compatibility)
 */
export function formatCurrency(
  value: number | string | null | undefined,
  currency = 'EUR'
): string {
  if (value === null || value === undefined || value === '') return '-';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '-';

  return new Intl.NumberFormat(getLocale(), {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

/**
 * Format a number with thousands separator
 */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat(getLocale()).format(value);
}

/**
 * Truncate a string with ellipsis
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - 3) + '...';
}

/**
 * Format bytes to human-readable size
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Format monthly cost with currency symbol
 */
export function formatMonthlyCost(
  value: number | string | null | undefined,
  currency = 'EUR',
  numberLocale = 'de-DE'
): string {
  if (value === null || value === undefined || value === '') return '-';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '-';

  const symbol = CURRENCY_SYMBOLS[currency] || currency;
  const locale = NUMBER_FORMAT_LOCALES[numberLocale] || 'de-DE';

  const formatted = new Intl.NumberFormat(locale, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(num);

  if (currency === 'EUR' || currency === 'GBP') {
    return `${formatted} ${symbol} / month`;
  }
  return `${symbol}${formatted} / month`;
}
