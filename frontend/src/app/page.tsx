'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { api } from '@/lib/api';

export default function HomePage() {
  const router = useRouter();
  const t = useTranslations('common');

  useEffect(() => {
    async function checkSetup() {
      try {
        const setupStatus = await api.getSetupStatus();

        if (!setupStatus.is_complete) {
          router.push('/setup');
        } else {
          router.push('/dashboard');
        }
      } catch (error) {
        // API not available, redirect to setup
        router.push('/setup');
      }
    }

    checkSetup();
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
        <p className="mt-4 text-muted-foreground">{t('loading')}</p>
      </div>
    </div>
  );
}
