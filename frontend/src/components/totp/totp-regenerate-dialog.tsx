'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { api } from '@/lib/api';
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
import { Loader2, RefreshCw, AlertTriangle } from 'lucide-react';

interface TotpRegenerateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (backupCodes: string[]) => void;
}

export function TotpRegenerateDialog({ open, onOpenChange, onSuccess }: TotpRegenerateDialogProps) {
  const t = useTranslations('profile');

  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleRegenerate = async () => {
    if (!password) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      const result = await api.regenerateBackupCodes(password);
      onSuccess(result.backup_codes);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('totpInvalidPassword'));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setPassword('');
    setError('');
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5" />
            {t('totpRegenerateTitle')}
          </DialogTitle>
          <DialogDescription>
            {t('totpRegenerateDescription')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Warning */}
          <div className="flex items-start gap-3 p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg">
            <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
            <p className="text-sm text-amber-800 dark:text-amber-200">
              {t('totpRegenerateDescription')}
            </p>
          </div>

          {error && (
            <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
              {error}
            </div>
          )}

          {/* Password Input */}
          <div className="space-y-2">
            <Label htmlFor="regenerate-password">{t('currentPassword')}</Label>
            <Input
              id="regenerate-password"
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError('');
              }}
              placeholder="••••••••"
            />
          </div>
        </div>

        <DialogFooter className="flex gap-2 sm:gap-0">
          <Button variant="outline" onClick={handleClose}>
            {t('totpCancel')}
          </Button>
          <Button
            onClick={handleRegenerate}
            disabled={loading || !password}
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                {t('totpRegenerating')}
              </>
            ) : (
              t('totpRegenerateConfirm')
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
