'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { RefreshCw } from 'lucide-react';

interface RenewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (newExpirationDate: string, clearCancellation: boolean) => Promise<void>;
  title: string;
  description: string;
  itemName: string;
  currentExpiration?: string;
  hasPendingCancellation?: boolean;
}

export function RenewDialog({
  open,
  onOpenChange,
  onConfirm,
  title,
  description,
  itemName,
  currentExpiration,
  hasPendingCancellation,
}: RenewDialogProps) {
  // Default to 1 year from now or current expiration
  const getDefaultDate = () => {
    const baseDate = currentExpiration ? new Date(currentExpiration) : new Date();
    baseDate.setFullYear(baseDate.getFullYear() + 1);
    return baseDate.toISOString().split('T')[0];
  };

  const [newExpirationDate, setNewExpirationDate] = useState(getDefaultDate());
  const [clearCancellation, setClearCancellation] = useState(true);
  const [loading, setLoading] = useState(false);

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm(newExpirationDate, clearCancellation);
      onOpenChange(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5 text-emerald-500" />
            {title}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3">
            <p className="text-sm text-emerald-800">
              Renewing: <strong>{itemName}</strong>
            </p>
            {currentExpiration && (
              <p className="text-xs text-emerald-700 mt-1">
                Current expiration: {new Date(currentExpiration).toLocaleDateString('de-DE')}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="newExpirationDate">New Expiration Date</Label>
            <Input
              id="newExpirationDate"
              type="date"
              value={newExpirationDate}
              onChange={(e) => setNewExpirationDate(e.target.value)}
              min={new Date().toISOString().split('T')[0]}
            />
          </div>

          {hasPendingCancellation && (
            <div className="flex items-start space-x-3">
              <Checkbox
                id="clearCancellation"
                checked={clearCancellation}
                onCheckedChange={(checked) => setClearCancellation(checked as boolean)}
              />
              <div className="grid gap-1.5 leading-none">
                <Label
                  htmlFor="clearCancellation"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  Clear pending cancellation
                </Label>
                <p className="text-xs text-muted-foreground">
                  Remove the scheduled cancellation and keep the license active.
                </p>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={loading || !newExpirationDate}>
            {loading ? 'Renewing...' : 'Confirm Renewal'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
