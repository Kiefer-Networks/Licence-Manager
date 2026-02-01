'use client';

import { useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  const t = useTranslations('common');

  useEffect(() => {
    // Log error to error reporting service in production
    // Error details are sanitized - do not log sensitive information
    if (process.env.NODE_ENV === 'production') {
      // Production: Only log error digest for tracking
      const errorInfo = {
        digest: error.digest,
        timestamp: new Date().toISOString(),
      };
      // Could send to error tracking service here
      void errorInfo;
    }
  }, [error]);

  return (
    <div className="min-h-screen bg-zinc-50 flex items-center justify-center p-4">
      <Card className="max-w-md w-full">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-red-100 flex items-center justify-center">
            <AlertTriangle className="h-6 w-6 text-red-600" />
          </div>
          <CardTitle className="text-xl">{t('errorTitle')}</CardTitle>
          <CardDescription>
            {t('errorDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-2">
            <Button onClick={reset} className="w-full">
              <RefreshCw className="mr-2 h-4 w-4" />
              {t('tryAgain')}
            </Button>
            <Button variant="outline" className="w-full" asChild>
              <a href="/dashboard">
                <Home className="mr-2 h-4 w-4" />
                {t('backToDashboard')}
              </a>
            </Button>
          </div>
          {error.digest && (
            <p className="text-xs text-center text-muted-foreground">
              {t('errorReference')}: {error.digest}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
