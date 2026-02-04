'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { api, TotpSetupResponse } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Loader2, Copy, Check, ShieldCheck, Key } from 'lucide-react';

interface TotpSetupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (backupCodes: string[]) => void;
}

type SetupStep = 'qr' | 'verify';

export function TotpSetupDialog({ open, onOpenChange, onSuccess }: TotpSetupDialogProps) {
  const t = useTranslations('profile');

  const [step, setStep] = useState<SetupStep>('qr');
  const [setupData, setSetupData] = useState<TotpSetupResponse | null>(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState('');
  const [secretCopied, setSecretCopied] = useState(false);

  const handleOpen = async () => {
    if (!setupData) {
      setLoading(true);
      setError('');
      try {
        const data = await api.setupTotp();
        setSetupData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to setup TOTP');
      } finally {
        setLoading(false);
      }
    }
  };

  const handleVerify = async () => {
    if (!verificationCode || verificationCode.length !== 6) {
      setError(t('totpInvalidCode'));
      return;
    }

    setVerifying(true);
    setError('');

    try {
      const result = await api.verifyAndEnableTotp(verificationCode);
      onSuccess(result.backup_codes);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('totpInvalidCode'));
    } finally {
      setVerifying(false);
    }
  };

  const handleClose = () => {
    setStep('qr');
    setSetupData(null);
    setVerificationCode('');
    setError('');
    setSecretCopied(false);
    onOpenChange(false);
  };

  const copySecret = async () => {
    if (setupData?.secret) {
      await navigator.clipboard.writeText(setupData.secret);
      setSecretCopied(true);
      setTimeout(() => setSecretCopied(false), 2000);
    }
  };

  // Load setup data when dialog opens
  if (open && !setupData && !loading) {
    handleOpen();
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-green-600" />
            {t('totpSetupTitle')}
          </DialogTitle>
          <DialogDescription>
            {step === 'qr' ? t('totpSetupStep1') : t('totpSetupStep2')}
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : setupData ? (
          <div className="space-y-4">
            {step === 'qr' && (
              <>
                {/* QR Code */}
                <div className="flex justify-center">
                  <div className="p-4 bg-white rounded-lg border">
                    <img
                      src={setupData.qr_code_data_uri}
                      alt="TOTP QR Code"
                      className="w-48 h-48"
                    />
                  </div>
                </div>

                {/* Secret Key for manual entry */}
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Key className="h-4 w-4" />
                    {t('totpSecretKey')}
                  </Label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 p-2 bg-muted rounded text-sm font-mono break-all">
                      {setupData.secret}
                    </code>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={copySecret}
                      className="shrink-0"
                    >
                      {secretCopied ? (
                        <Check className="h-4 w-4 text-green-600" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t('totpCopied') && secretCopied ? t('totpCopied') : t('totpCopySecret')}
                  </p>
                </div>
              </>
            )}

            {/* Verification Code Input (shown in both steps but focused in step 2) */}
            <div className="space-y-2">
              <Label htmlFor="totp-code">{t('totpVerifyCode')}</Label>
              <Input
                id="totp-code"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                placeholder={t('totpVerifyPlaceholder')}
                value={verificationCode}
                onChange={(e) => {
                  const value = e.target.value.replace(/\D/g, '');
                  setVerificationCode(value);
                  setError('');
                }}
                className="text-center text-2xl tracking-widest font-mono"
                autoComplete="one-time-code"
              />
            </div>
          </div>
        ) : null}

        <DialogFooter className="flex gap-2 sm:gap-0">
          <Button variant="outline" onClick={handleClose}>
            {t('totpCancel')}
          </Button>
          <Button
            onClick={handleVerify}
            disabled={verifying || !verificationCode || verificationCode.length !== 6}
          >
            {verifying ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                {t('totpVerifying')}
              </>
            ) : (
              t('totpVerify')
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
