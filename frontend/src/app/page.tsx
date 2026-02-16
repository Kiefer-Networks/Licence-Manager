'use client';

import { useTranslations } from 'next-intl';
import { useRootRedirect } from '@/hooks/use-root-redirect';

export default function HomePage() {
  const t = useTranslations('common');
  useRootRedirect();

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
        <p className="mt-4 text-muted-foreground">{t('loading')}</p>
      </div>
    </div>
  );
}
