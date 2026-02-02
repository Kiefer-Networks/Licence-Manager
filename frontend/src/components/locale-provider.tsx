'use client';

import { createContext, useContext, useMemo, useCallback } from 'react';
import { useAuth } from './auth-provider';

// Currency symbols mapping
const CURRENCY_SYMBOLS: Record<string, string> = {
  EUR: '\u20AC',
  USD: '$',
  GBP: '\u00A3',
  CHF: 'CHF',
};

// Number format locale mapping
const NUMBER_FORMAT_LOCALES: Record<string, string> = {
  'de-DE': 'de-DE',
  'en-US': 'en-US',
  'de-CH': 'de-CH',
};

// Date format patterns
export type DateFormatPattern = 'DD.MM.YYYY' | 'MM/DD/YYYY' | 'YYYY-MM-DD';

interface LocaleContextValue {
  dateFormat: DateFormatPattern;
  numberFormat: string;
  currency: string;
  currencySymbol: string;
  formatDate: (date: Date | string | null | undefined) => string;
  formatNumber: (value: number | string | null | undefined, decimals?: number) => string;
  formatCurrency: (value: number | string | null | undefined, currencyOverride?: string) => string;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();

  // Get user preferences with defaults
  const dateFormat = (user?.date_format as DateFormatPattern) || 'DD.MM.YYYY';
  const numberFormat = user?.number_format || 'de-DE';
  const currency = user?.currency || 'EUR';
  const currencySymbol = CURRENCY_SYMBOLS[currency] || currency;

  // Format date according to user preference
  const formatDate = useCallback((date: Date | string | null | undefined): string => {
    if (!date) return '-';

    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return '-';

    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();

    switch (dateFormat) {
      case 'MM/DD/YYYY':
        return `${month}/${day}/${year}`;
      case 'YYYY-MM-DD':
        return `${year}-${month}-${day}`;
      case 'DD.MM.YYYY':
      default:
        return `${day}.${month}.${year}`;
    }
  }, [dateFormat]);

  // Format number according to user preference
  const formatNumber = useCallback((value: number | string | null | undefined, decimals = 2): string => {
    if (value === null || value === undefined || value === '') return '-';

    const num = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(num)) return '-';

    const locale = NUMBER_FORMAT_LOCALES[numberFormat] || 'de-DE';
    return new Intl.NumberFormat(locale, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(num);
  }, [numberFormat]);

  // Format currency according to user preference
  const formatCurrency = useCallback((value: number | string | null | undefined, currencyOverride?: string): string => {
    if (value === null || value === undefined || value === '') return '-';

    const num = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(num)) return '-';

    const locale = NUMBER_FORMAT_LOCALES[numberFormat] || 'de-DE';
    const currencyCode = currencyOverride || currency;
    const symbol = CURRENCY_SYMBOLS[currencyCode] || currencyCode;

    const formatted = new Intl.NumberFormat(locale, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);

    // Format with proper currency symbol placement
    if (currencyCode === 'EUR' || currencyCode === 'GBP') {
      return `${formatted} ${symbol}`;
    }
    return `${symbol}${formatted}`;
  }, [numberFormat, currency]);

  const value = useMemo<LocaleContextValue>(() => ({
    dateFormat,
    numberFormat,
    currency,
    currencySymbol,
    formatDate,
    formatNumber,
    formatCurrency,
  }), [dateFormat, numberFormat, currency, currencySymbol, formatDate, formatNumber, formatCurrency]);

  return (
    <LocaleContext.Provider value={value}>
      {children}
    </LocaleContext.Provider>
  );
}

export function useLocale(): LocaleContextValue {
  const context = useContext(LocaleContext);
  if (!context) {
    throw new Error('useLocale must be used within a LocaleProvider');
  }
  return context;
}

// Helper hook for formatting with defaults (for use outside of provider)
export function useLocaleFormatters() {
  try {
    return useLocale();
  } catch {
    // Fallback for components outside of LocaleProvider
    return {
      dateFormat: 'DD.MM.YYYY' as DateFormatPattern,
      numberFormat: 'de-DE',
      currency: 'EUR',
      currencySymbol: '\u20AC',
      formatDate: (date: Date | string | null | undefined): string => {
        if (!date) return '-';
        const d = typeof date === 'string' ? new Date(date) : date;
        if (isNaN(d.getTime())) return '-';
        const day = String(d.getDate()).padStart(2, '0');
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const year = d.getFullYear();
        return `${day}.${month}.${year}`;
      },
      formatNumber: (value: number | string | null | undefined, decimals = 2): string => {
        if (value === null || value === undefined || value === '') return '-';
        const num = typeof value === 'string' ? parseFloat(value) : value;
        if (isNaN(num)) return '-';
        return new Intl.NumberFormat('de-DE', {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals,
        }).format(num);
      },
      formatCurrency: (value: number | string | null | undefined): string => {
        if (value === null || value === undefined || value === '') return '-';
        const num = typeof value === 'string' ? parseFloat(value) : value;
        if (isNaN(num)) return '-';
        return `${new Intl.NumberFormat('de-DE', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }).format(num)} \u20AC`;
      },
    };
  }
}
