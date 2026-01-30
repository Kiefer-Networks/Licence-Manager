'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
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
  const router = useRouter();
  const [step, setStep] = useState<SetupStep>('welcome');
  const [setupStatus, setSetupStatus] = useState<SetupStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // HiBob credentials
  const [hibobAuthToken, setHibobAuthToken] = useState('');

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
        display_name: 'HiBob',
        credentials: {
          auth_token: token,
        },
      });

      // Clear sensitive data from state after successful submission
      setHibobAuthToken('');
      setStep('providers');
    } catch (err: unknown) {
      // Sanitize error message - don't expose internal details
      const message = err instanceof Error ? err.message : 'Configuration failed';
      setError(message.includes('token') ? 'Invalid credentials' : message);
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
    { id: 'welcome', label: 'Welcome' },
    { id: 'hibob', label: 'HiBob' },
    { id: 'providers', label: 'Providers' },
    { id: 'complete', label: 'Complete' },
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
              <CardTitle className="text-3xl">License Management System</CardTitle>
              <CardDescription className="text-lg">
                Track and manage software licenses across your organization
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-start gap-4">
                  <div className="rounded-full bg-primary/10 p-2">
                    <CheckCircle className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium">Sync with HiBob</h3>
                    <p className="text-sm text-muted-foreground">
                      Automatically import employees from your HRIS
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="rounded-full bg-primary/10 p-2">
                    <CheckCircle className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium">Track Multiple Providers</h3>
                    <p className="text-sm text-muted-foreground">
                      Google Workspace, Slack, OpenAI, Figma, and more
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="rounded-full bg-primary/10 p-2">
                    <CheckCircle className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium">Get Alerts</h3>
                    <p className="text-sm text-muted-foreground">
                      Slack notifications for offboarding and inactive licenses
                    </p>
                  </div>
                </div>
              </div>
              <Button onClick={() => setStep('hibob')} className="w-full" size="lg">
                Get Started <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        )}

        {step === 'hibob' && (
          <Card>
            <CardHeader>
              <CardTitle>Connect HiBob</CardTitle>
              <CardDescription>
                Connect your HiBob account to sync employee data.
                This is your source of truth for employees.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="hibob-auth-token">Auth Token (Base64)</Label>
                <Input
                  id="hibob-auth-token"
                  type="password"
                  value={hibobAuthToken}
                  onChange={(e) => setHibobAuthToken(e.target.value)}
                  placeholder="Base64 encoded user:password"
                />
                <p className="text-xs text-muted-foreground">
                  Base64 encoded string of service_user_id:api_key for Basic Auth
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
                {loading ? 'Connecting...' : 'Connect HiBob'}
              </Button>
            </CardContent>
          </Card>
        )}

        {step === 'providers' && (
          <Card>
            <CardHeader>
              <CardTitle>Add More Providers</CardTitle>
              <CardDescription>
                You can add more license providers now or later from Settings.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4">
                <Button variant="outline" className="justify-start" disabled>
                  Google Workspace (Coming next)
                </Button>
                <Button variant="outline" className="justify-start" disabled>
                  Slack
                </Button>
                <Button variant="outline" className="justify-start" disabled>
                  OpenAI
                </Button>
                <Button variant="outline" className="justify-start" disabled>
                  Figma
                </Button>
              </div>
              <div className="flex gap-4">
                <Button variant="outline" onClick={handleSkipProviders} className="flex-1">
                  Skip for Now
                </Button>
                <Button onClick={() => setStep('complete')} className="flex-1">
                  Continue
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {step === 'complete' && (
          <Card>
            <CardHeader className="text-center">
              <CheckCircle className="mx-auto h-16 w-16 text-green-500 mb-4" />
              <CardTitle>Setup Complete!</CardTitle>
              <CardDescription>
                Your license management system is ready to use.
                We'll start syncing your data in the background.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button onClick={handleComplete} className="w-full" size="lg">
                Go to Dashboard <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
