'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Check, X, UserPlus, Loader2, AlertCircle } from 'lucide-react';
import { api, License } from '@/lib/api';

interface SuggestedMatchCardProps {
  license: License;
  onUpdate?: () => void;
}

/**
 * Card component for displaying a license with a suggested match.
 * Allows users to confirm, reject, or mark as external guest.
 *
 * GDPR-compliant: No private emails are stored.
 * Admins must manually decide what to do with each suggestion.
 */
export function SuggestedMatchCard({ license, onUpdate }: SuggestedMatchCardProps) {
  const t = useTranslations('licenses');
  const tCommon = useTranslations('common');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const confidence = license.match_confidence
    ? Math.round(license.match_confidence * 100)
    : 0;

  const handleConfirm = async () => {
    setIsLoading(true);
    setError(null);
    try {
      await api.confirmLicenseMatch(license.id);
      onUpdate?.();
    } catch (err) {
      setError(t('failedToConfirmMatch'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleReject = async () => {
    setIsLoading(true);
    setError(null);
    try {
      await api.rejectLicenseMatch(license.id);
      onUpdate?.();
    } catch (err) {
      setError(t('failedToRejectMatch'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleMarkAsGuest = async () => {
    setIsLoading(true);
    setError(null);
    try {
      await api.markAsExternalGuest(license.id);
      onUpdate?.();
    } catch (err) {
      setError(t('failedToMarkAsGuest'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        {error && (
          <div className="flex items-center gap-2 text-sm text-red-600 mb-3 p-2 bg-red-50 rounded">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        <div className="flex items-start justify-between gap-4">
          {/* License info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-sm truncate">
                {license.external_user_id}
              </span>
              <Badge variant="outline" className="text-xs">
                {license.provider_name}
              </Badge>
            </div>
            {license.license_type && (
              <p className="text-xs text-muted-foreground">
                {license.license_type_display_name || license.license_type}
              </p>
            )}
          </div>

          {/* Suggested match */}
          <div className="text-right">
            <div className="flex items-center gap-2 justify-end">
              <Badge
                variant="outline"
                className={
                  confidence >= 80
                    ? 'text-green-600 border-green-200 bg-green-50'
                    : confidence >= 60
                      ? 'text-yellow-600 border-yellow-200 bg-yellow-50'
                      : 'text-orange-600 border-orange-200 bg-orange-50'
                }
              >
                {t('matchPercent', { percent: confidence })}
              </Badge>
            </div>
            <p className="text-sm font-medium mt-1">
              {license.suggested_employee_name}
            </p>
            {license.suggested_employee_email && (
              <p className="text-xs text-muted-foreground">
                {license.suggested_employee_email}
              </p>
            )}
            {license.match_method && (
              <p className="text-xs text-muted-foreground mt-0.5">
                {t('viaMethod', { method: license.match_method.replace('_', ' ') })}
              </p>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end mt-4 pt-3 border-t gap-2">
          {license.is_external_email && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleMarkAsGuest}
              disabled={isLoading}
            >
              <UserPlus className="h-3.5 w-3.5 mr-1" />
              {t('externalGuest')}
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleReject}
            disabled={isLoading}
            className="text-red-600 hover:text-red-700"
          >
            {isLoading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <X className="h-3.5 w-3.5" />
            )}
          </Button>
          <Button
            size="sm"
            onClick={handleConfirm}
            disabled={isLoading}
            className="bg-green-600 hover:bg-green-700"
          >
            {isLoading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <>
                <Check className="h-3.5 w-3.5 mr-1" />
                {tCommon('confirm')}
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
