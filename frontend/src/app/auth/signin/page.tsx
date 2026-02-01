'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/components/auth-provider';

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
 * Uses an allowlist of known safe route prefixes instead of regex.
 */
function isValidCallbackUrl(url: string | null): boolean {
  if (!url) return false;

  // Decode URL to catch encoded attacks (e.g., %2F%2F for //)
  let decodedUrl: string;
  try {
    decodedUrl = decodeURIComponent(url);
  } catch {
    return false; // Invalid encoding
  }

  // Must start with / and not contain protocol or double slashes
  if (!decodedUrl.startsWith('/')) return false;
  if (decodedUrl.startsWith('//')) return false;
  if (decodedUrl.includes(':')) return false;

  // Check against allowlist of safe routes
  return SAFE_ROUTE_PREFIXES.some(prefix => decodedUrl.startsWith(prefix));
}

function SignInContent() {
  const t = useTranslations('auth');
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const rawCallbackUrl = searchParams.get('callbackUrl');
  const callbackUrl = isValidCallbackUrl(rawCallbackUrl) ? rawCallbackUrl! : '/dashboard';

  // Redirect if already authenticated
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.push(callbackUrl);
    }
  }, [authLoading, isAuthenticated, router, callbackUrl]);

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      // Use AuthProvider's login which handles CSRF, token refresh, and user state
      await login(email, password);
      // AuthProvider's login() already pushes to /dashboard
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('invalidCredentials');
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Show loading while checking existing auth
  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/50">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">{t('signIn')}</CardTitle>
          <CardDescription>
            {t('pleaseSignIn')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mb-4 bg-destructive/10 text-destructive text-sm p-3 rounded-md">
              {error}
            </div>
          )}

          <form onSubmit={handleSignIn} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">{t('emailAddress')}</Label>
              <Input
                id="email"
                type="email"
                placeholder={t('emailPlaceholder')}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
                autoComplete="email"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">{t('password')}</Label>
              <Input
                id="password"
                type="password"
                placeholder={t('password')}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
                autoComplete="current-password"
              />
            </div>
            <Button type="submit" className="w-full" size="lg" disabled={isLoading}>
              {isLoading ? t('signingIn') : t('signIn')}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default function SignInPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    }>
      <SignInContent />
    </Suspense>
  );
}
