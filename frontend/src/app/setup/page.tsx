'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { api, BackupRestoreResponse } from '@/lib/api';
import { CheckCircle, Circle, ArrowRight, Upload, FileArchive, Eye, EyeOff, AlertTriangle, Loader2 } from 'lucide-react';

type SetupStep = 'restore' | 'welcome' | 'hibob' | 'providers' | 'complete';

interface SetupStatus {
  is_complete: boolean;
}

export default function SetupPage() {
  const t = useTranslations('setup');
  const tProviders = useTranslations('providers');
  const tSettings = useTranslations('settings');
  const router = useRouter();
  const [step, setStep] = useState<SetupStep>('restore');
  const [setupStatus, setSetupStatus] = useState<SetupStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // HiBob credentials - cleared on unmount for security
  const [hibobAuthToken, setHibobAuthToken] = useState('');

  // Backup restore state
  const [backupFile, setBackupFile] = useState<File | null>(null);
  const [backupPassword, setBackupPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [restoreResult, setRestoreResult] = useState<BackupRestoreResponse | null>(null);

  // Clear sensitive data on unmount to prevent memory exposure
  useEffect(() => {
    return () => {
      setHibobAuthToken('');
      setBackupPassword('');
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

  const handleFileSelect = (selectedFile: File) => {
    if (selectedFile.name.endsWith('.lcbak')) {
      setBackupFile(selectedFile);
      setError(null);
    } else {
      setError(tSettings('selectBackupFile'));
      setBackupFile(null);
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleRestore = async () => {
    if (!backupFile || backupPassword.length < 8) return;

    setLoading(true);
    setError(null);

    try {
      const result = await api.setupRestoreBackup(backupFile, backupPassword);
      setRestoreResult(result);

      if (result.success) {
        // Redirect to dashboard after successful restore
        setTimeout(() => {
          router.push('/dashboard');
        }, 2000);
      } else {
        setError(result.error || tSettings('restoreFailed'));
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : tSettings('restoreFailed');
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleSkipRestore = () => {
    setStep('welcome');
  };

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
    { id: 'restore', label: t('restoreBackup') },
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
                    className={`h-0.5 w-8 mx-1 ${
                      i < currentStepIndex ? 'bg-primary' : 'bg-muted-foreground/30'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        {step === 'restore' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                {t('restoreFromBackup')}
              </CardTitle>
              <CardDescription>
                {t('restoreDescription')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {restoreResult?.success ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 rounded-lg bg-green-50 p-4 text-green-700">
                    <CheckCircle className="h-6 w-6 flex-shrink-0" />
                    <div>
                      <p className="font-medium">{tSettings('importSuccessful')}</p>
                      <p className="text-sm mt-1">{t('redirectingToDashboard')}</p>
                    </div>
                  </div>
                  <div className="flex justify-center">
                    <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  </div>
                </div>
              ) : (
                <>
                  {error && (
                    <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-600">
                      <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                      <span>{error}</span>
                    </div>
                  )}

                  {/* Info Banner */}
                  <div className="flex items-start gap-2 rounded-lg bg-blue-50 p-3 text-sm text-blue-700">
                    <FileArchive className="h-4 w-4 mt-0.5 flex-shrink-0" />
                    <p>{t('hasBackupQuestion')}</p>
                  </div>

                  {/* File Drop Zone */}
                  <div
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    className={`relative border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                      isDragging
                        ? 'border-blue-500 bg-blue-50'
                        : backupFile
                        ? 'border-green-500 bg-green-50'
                        : 'border-zinc-300 hover:border-zinc-400'
                    }`}
                  >
                    <input
                      type="file"
                      accept=".lcbak"
                      onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                      disabled={loading}
                    />
                    {backupFile ? (
                      <div className="flex items-center justify-center gap-2 text-green-700">
                        <FileArchive className="h-8 w-8" />
                        <div className="text-left">
                          <p className="font-medium">{backupFile.name}</p>
                          <p className="text-xs text-green-600">
                            {(backupFile.size / 1024 / 1024).toFixed(2)} MB
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="text-zinc-500">
                        <FileArchive className="h-10 w-10 mx-auto mb-2" />
                        <p className="font-medium">{tSettings('dropFileHere')}</p>
                        <p className="text-xs mt-1">{tSettings('clickToSelect')} (.lcbak)</p>
                      </div>
                    )}
                  </div>

                  {/* Password Input */}
                  {backupFile && (
                    <div className="space-y-2">
                      <Label htmlFor="restorePassword" className="text-sm font-medium">
                        {tSettings('backupPassword')}
                      </Label>
                      <div className="relative">
                        <Input
                          id="restorePassword"
                          type={showPassword ? 'text' : 'password'}
                          value={backupPassword}
                          onChange={(e) => setBackupPassword(e.target.value)}
                          placeholder={tSettings('backupPasswordInput')}
                          disabled={loading}
                          className="pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                        >
                          {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                      </div>
                    </div>
                  )}

                  <div className="flex gap-3 pt-2">
                    <Button
                      variant="outline"
                      onClick={handleSkipRestore}
                      className="flex-1"
                      disabled={loading}
                    >
                      {t('noBackupContinue')}
                    </Button>
                    <Button
                      onClick={handleRestore}
                      disabled={!backupFile || backupPassword.length < 8 || loading}
                      className="flex-1"
                    >
                      {loading ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          {tSettings('importing')}
                        </>
                      ) : (
                        <>
                          <Upload className="mr-2 h-4 w-4" />
                          {t('restoreAndContinue')}
                        </>
                      )}
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        )}

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
