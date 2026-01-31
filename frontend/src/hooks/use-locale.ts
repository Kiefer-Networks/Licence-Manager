'use client';

import { useRouter } from 'next/navigation';
import { useTransition } from 'react';

export type Locale = 'en' | 'de';

export function useLocale() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const setLocale = (locale: Locale) => {
    // Set the locale cookie
    document.cookie = `locale=${locale}; path=/; max-age=${365 * 24 * 60 * 60}; samesite=lax`;

    // Refresh the page to apply the new locale
    startTransition(() => {
      router.refresh();
    });
  };

  return { setLocale, isPending };
}
