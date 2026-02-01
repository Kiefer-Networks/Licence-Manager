'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { api } from '@/lib/api';
import { CheckCircle, Circle, ArrowRight } from 'lucide-react';

// Skip auth step in dev mode
type SetupStep = 'welcome' | 'hibob' | 'providers' | 'complete';

interface SetupStatus {
  is_complete: boolean;
}

export default function SetupPage() {
  const t = useTranslations('setup');
  const tProviders = useTranslations('providers');
  const router = useRouter();
  const [step, setStep] = useState<SetupStep>('welcome');
  const [setupStatus, setSetupStatus] = useState<SetupStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // HiBob credentials - cleared on unmount for security
  const [hibobAuthToken, setHibobAuthToken] = useState('');

  // Clear sensitive data on unmount to prevent memory exposure
  useEffect(() => {
    return () => {
      setHibobAuthToken('');
    };
  }, []);

  useEffect(() => {
    async function checkStatus() {
      try {
        const status = await api.getSetupStatus();
        setSetupStatus(status);
        if (status.is_complete) {
          router.push('/dashboard');
        }
      } catch {
        // Silently handle - user will see setup page
      }
    }
    checkStatus();
  }, [router]);

  const handleHibobSetup = async () => {
    setLoading(true);
    setError(null);

    // Copy token for use, then clear from state immediately for security
    const token = hibobAuthToken;

    try {
      // Test connection first
      const testResult = await api.testProviderConnection('hibob', {
        auth_token: token,
      });

      if (!testResult.success) {
        setError(testResult.message);
        return;
      }

      // Create provider
      await api.createProvider({
        name: 'hibob',
        display_name: tProviders('hibob'),
        credentials: {
          auth_token: token,
        },
      });

      // Clear sensitive data from state after successful submission
      setHibobAuthToken('');
      setStep('providers');
    } catch (err: unknown) {
      // Sanitize error message - don't expose internal details
      const message = err instanceof Error ? err.message : t('configurationFailed');
      setError(message.includes('token') ? t('invalidCredentials') : message);
    } finally {
      setLoading(false);
    }
  };

  const handleSkipProviders = () => {
    setStep('complete');
  };

  const handleComplete = async () => {
    // Trigger initial sync (non-blocking, errors are logged server-side)
    try {
      await api.triggerSync();
    } catch {
      // Sync failures are handled server-side, don't block navigation
    }
    router.push('/dashboard');
  };

  const steps = [
    { id: 'welcome', label: t('welcome') },
    { id: 'hibob', label: tProviders('hibob') },
    { id: 'providers', label: tProviders('title') },
    { id: 'complete', label: t('complete') },
  ];

  const currentStepIndex = steps.findIndex((s) => s.id === step);

  return (
    <div className="min-h-screen bg-muted/50 py-12">
      <div className="container max-w-2xl">
        {/* Progress */}
        <div className="mb-8">
          <div className="flex justify-between">
            {steps.map((s, i) => (
              <div key={s.id} className="flex items-center">
                {i <= currentStepIndex ? (
                  <CheckCircle className="h-6 w-6 text-primary" />
                ) : (
                  <Circle className="h-6 w-6 text-muted-foreground" />
                )}
                {i < steps.length - 1 && (
                  <div
                    className={`h-0.5 w-12 mx-2 ${
                      i < currentStepIndex ? 'bg-primary' : 'bg-muted-foreground/30'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        {step === 'welcome' && (
          <Card>
            <CardHeader className="text-center">
              <CardTitle className="text-3xl">{t('welcomeMessage')}</CardTitle>
              <CardDescription className="text-lg">
                {t('welcomeDescription')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-start gap-4">
                  <div className="rounded-full bg-primary/10 p-2">
                    <CheckCircle className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium">{t('syncWithHibob')}</h3>
                    <p className="text-sm text-muted-foreground">
                      {t('syncDescription')}
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="rounded-full bg-primary/10 p-2">
                    <CheckCircle className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium">{t('trackMultipleProviders')}</h3>
                    <p className="text-sm text-muted-foreground">
                      {t('trackDescription')}
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="rounded-full bg-primary/10 p-2">
                    <CheckCircle className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium">{t('getAlerts')}</h3>
                    <p className="text-sm text-muted-foreground">
                      {t('notificationsDescription')}
                    </p>
                  </div>
                </div>
              </div>
              <Button onClick={() => setStep('hibob')} className="w-full" size="lg">
                {t('getStarted')} <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        )}

        {step === 'hibob' && (
          <Card>
            <CardHeader>
              <CardTitle>{t('connectHibob')}</CardTitle>
              <CardDescription>
                {t('hibobDescription')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="hibob-auth-token">{t('authToken')}</Label>
                <Input
                  id="hibob-auth-token"
                  type="password"
                  value={hibobAuthToken}
                  onChange={(e) => setHibobAuthToken(e.target.value)}
                  placeholder={t('authTokenPlaceholder')}
                />
                <p className="text-xs text-muted-foreground">
                  {t('authTokenHelp')}
                </p>
              </div>
              {error && (
                <p className="text-sm text-destructive">{error}</p>
              )}
              <Button
                onClick={handleHibobSetup}
                disabled={!hibobAuthToken || loading}
                className="w-full"
              >
                {loading ? t('connecting') : t('connectHibob')}
              </Button>
            </CardContent>
          </Card>
        )}

        {step === 'providers' && (
          <Card>
            <CardHeader>
              <CardTitle>{t('addMoreProviders')}</CardTitle>
              <CardDescription>
                {t('providersDescription')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4">
                <Button variant="outline" className="justify-start" disabled>
                  {tProviders('google')} ({t('comingNext')})
                </Button>
                <Button variant="outline" className="justify-start" disabled>
                  {tProviders('slack')}
                </Button>
                <Button variant="outline" className="justify-start" disabled>
                  {tProviders('openai')}
                </Button>
                <Button variant="outline" className="justify-start" disabled>
                  {tProviders('figma')}
                </Button>
              </div>
              <div className="flex gap-4">
                <Button variant="outline" onClick={handleSkipProviders} className="flex-1">
                  {t('skipForNow')}
                </Button>
                <Button onClick={() => setStep('complete')} className="flex-1">
                  {t('continue')}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {step === 'complete' && (
          <Card>
            <CardHeader className="text-center">
              <CheckCircle className="mx-auto h-16 w-16 text-green-500 mb-4" />
              <CardTitle>{t('completeTitle')}</CardTitle>
              <CardDescription>
                {t('completeDescription')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button onClick={handleComplete} className="w-full" size="lg">
                {t('goToDashboard')} <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
