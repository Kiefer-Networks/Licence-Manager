'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/components/auth-provider';
import { api } from '@/lib/api';

// Allowlist of safe route prefixes for callback URLs
const SAFE_ROUTE_PREFIXES = [
  '/dashboard',
  '/providers',
  '/users',
  '/reports',
  '/settings',
  '/profile',
  '/admin',
];

/**
 * Validates callback URL to prevent open redirect attacks.
 */
function isValidCallbackUrl(url: string | null): boolean {
  if (!url) return false;

  let decodedUrl: string;
  try {
    decodedUrl = decodeURIComponent(url);
  } catch {
    return false;
  }

  if (!decodedUrl.startsWith('/')) return false;
  if (decodedUrl.startsWith('//')) return false;
  if (decodedUrl.includes(':')) return false;

  return SAFE_ROUTE_PREFIXES.some(prefix => decodedUrl.startsWith(prefix));
}

export interface UseSignInReturn {
  error: string;
  setError: (error: string) => void;
  isLoading: boolean;
  googleEnabled: boolean;
  authLoading: boolean;
  callbackUrl: string;
  oauthError: string | null;
  handleGoogleLogin: () => void;
}

export function useSignIn(t: (key: string) => string): UseSignInReturn {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [googleEnabled, setGoogleEnabled] = useState(false);

  const rawCallbackUrl = searchParams.get('callbackUrl');
  const callbackUrl = isValidCallbackUrl(rawCallbackUrl) ? rawCallbackUrl! : '/dashboard';
  const oauthError = searchParams.get('error');

  // Fetch auth config on mount
  useEffect(() => {
    api.getAuthConfig()
      .then(config => setGoogleEnabled(config.google_oauth_enabled))
      .catch(() => setGoogleEnabled(false));
  }, []);

  // Show OAuth error if present
  useEffect(() => {
    if (oauthError) {
      if (oauthError === 'account_not_found') {
        setError(t('googleAccountNotFound'));
      } else if (oauthError === 'oauth_failed') {
        setError(t('googleAuthFailed'));
      } else {
        setError(t('googleAuthFailed'));
      }
    }
  }, [oauthError, t]);

  // Redirect if already authenticated
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.push(callbackUrl);
    }
  }, [authLoading, isAuthenticated, router, callbackUrl]);

  const handleGoogleLogin = () => {
    setIsLoading(true);
    setError('');
    window.location.href = api.getGoogleLoginUrl();
  };

  return {
    error,
    setError,
    isLoading,
    googleEnabled,
    authLoading,
    callbackUrl,
    oauthError,
    handleGoogleLogin,
  };
}
