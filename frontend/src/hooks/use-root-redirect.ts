'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export function useRootRedirect(): void {
  const router = useRouter();

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
}
