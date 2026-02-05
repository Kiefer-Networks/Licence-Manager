'use client';

import { useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { toast } from '@/components/ui/use-toast';

export function ApiErrorHandler() {
  const t = useTranslations('errors');

  useEffect(() => {
    const handleRateLimit = (event: CustomEvent<{ waitSeconds: number }>) => {
      toast({
        title: t('rateLimited'),
        variant: 'warning',
      });
    };

    window.addEventListener('api:ratelimit', handleRateLimit as EventListener);
    return () => {
      window.removeEventListener('api:ratelimit', handleRateLimit as EventListener);
    };
  }, [t]);

  return null;
}
