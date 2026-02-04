'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Copy, Check, AlertTriangle, ShieldCheck } from 'lucide-react';

interface TotpBackupCodesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  backupCodes: string[];
}

export function TotpBackupCodesDialog({ open, onOpenChange, backupCodes }: TotpBackupCodesDialogProps) {
  const t = useTranslations('profile');
  const [copied, setCopied] = useState(false);

  const copyAllCodes = async () => {
    const codesText = backupCodes.join('\n');
    await navigator.clipboard.writeText(codesText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClose = () => {
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-green-600" />
            {t('totpBackupCodesTitle')}
          </DialogTitle>
          <DialogDescription>
            {t('totpBackupCodesDescription')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Warning */}
          <div className="flex items-start gap-3 p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg">
            <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
            <p className="text-sm text-amber-800 dark:text-amber-200">
              {t('totpBackupCodesWarning')}
            </p>
          </div>

          {/* Backup Codes Grid */}
          <div className="grid grid-cols-2 gap-2 p-4 bg-muted rounded-lg">
            {backupCodes.map((code, index) => (
              <code
                key={index}
                className="p-2 bg-background rounded text-center font-mono text-sm"
              >
                {code}
              </code>
            ))}
          </div>

          {/* Copy Button */}
          <Button
            variant="outline"
            onClick={copyAllCodes}
            className="w-full"
          >
            {copied ? (
              <>
                <Check className="h-4 w-4 mr-2 text-green-600" />
                {t('totpBackupCodesCopied')}
              </>
            ) : (
              <>
                <Copy className="h-4 w-4 mr-2" />
                {t('totpBackupCodesCopy')}
              </>
            )}
          </Button>
        </div>

        <DialogFooter>
          <Button onClick={handleClose}>
            {t('totpBackupCodesDone')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
