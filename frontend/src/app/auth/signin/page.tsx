'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/components/auth-provider';
import { ShieldCheck, ArrowLeft } from 'lucide-react';

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

  // TOTP state
  const [totpRequired, setTotpRequired] = useState(false);
  const [totpCode, setTotpCode] = useState('');

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
      const result = await login(email, password);
      if (result.totpRequired) {
        // TOTP verification required
        setTotpRequired(true);
      }
      // AuthProvider's login() already pushes to /dashboard on success
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('invalidCredentials');
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTotpVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const result = await login(email, password, totpCode);
      if (result.totpRequired) {
        // This shouldn't happen after entering a code, but handle it
        setError(t('totpInvalidCode'));
      }
      // AuthProvider's login() already pushes to /dashboard on success
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('totpInvalidCode');
      setError(errorMessage);
      setTotpCode(''); // Clear the code on error
    } finally {
      setIsLoading(false);
    }
  };

  const handleBackToLogin = () => {
    setTotpRequired(false);
    setTotpCode('');
    setPassword('');
    setError('');
  };

  // Show loading while checking existing auth
  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  // TOTP verification step
  if (totpRequired) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/50">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                <ShieldCheck className="h-6 w-6 text-primary" />
              </div>
            </div>
            <CardTitle className="text-2xl">{t('twoFactorRequired')}</CardTitle>
            <CardDescription>
              {t('totpVerifyDescription')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-4 bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                {error}
              </div>
            )}

            <form onSubmit={handleTotpVerify} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="totp-code">{t('totpCode')}</Label>
                <Input
                  id="totp-code"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  placeholder={t('totpCodePlaceholder')}
                  value={totpCode}
                  onChange={(e) => {
                    const value = e.target.value.replace(/\D/g, '');
                    setTotpCode(value);
                    setError('');
                  }}
                  required
                  disabled={isLoading}
                  autoComplete="one-time-code"
                  className="text-center text-2xl tracking-widest font-mono"
                  autoFocus
                />
              </div>
              <Button
                type="submit"
                className="w-full"
                size="lg"
                disabled={isLoading || totpCode.length !== 6}
              >
                {isLoading ? t('totpVerifying') : t('totpVerify')}
              </Button>
            </form>

            <div className="mt-4 pt-4 border-t">
              <Button
                variant="ghost"
                className="w-full"
                onClick={handleBackToLogin}
                disabled={isLoading}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                {t('goBack')}
              </Button>
            </div>
          </CardContent>
        </Card>
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
