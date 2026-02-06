'use client';

import { useTranslations } from 'next-intl';
import { Badge } from '@/components/ui/badge';
import { Globe, Skull, UserMinus, Bot, HelpCircle, UserCheck, AlertCircle } from 'lucide-react';

// Minimal type for LicenseStatusBadge - only the fields it actually needs
interface LicenseForBadge {
  is_external_email?: boolean;
  employee_id?: string | null;
  employee_status?: string | null;
  status?: string;
  is_service_account?: boolean;
  service_account_name?: string | null;
  // Match fields
  match_status?: string | null;
  match_confidence?: number | null;
  suggested_employee_name?: string | null;
}

interface LicenseStatusBadgeProps {
  license: LicenseForBadge;
  showUnassigned?: boolean;
}

/**
 * Shows multiple status badges based on license state.
 * Badge Priority (all applicable badges shown):
 * 1. Service Account (blue) - intentionally not linked to HRIS
 * 2. External Guest (green) - confirmed external guest
 * 3. Suggested Match (purple) - has suggested employee, needs review
 * 4. External Review (orange) - external email, needs decision
 * 5. External (orange) - external email (legacy)
 * 6. Offboarded (red) - if employee status is offboarded
 * 7. Inactive (gray) - if provider status is inactive/suspended
 * 8. Unassigned (amber) - if no employee linked (optional)
 */
export function LicenseStatusBadge({ license, showUnassigned = true }: LicenseStatusBadgeProps) {
  const t = useTranslations('licenses');

  const badges: React.ReactNode[] = [];

  // Service Account badge - shown when is_service_account=true
  if (license.is_service_account) {
    badges.push(
      <Badge
        key="service-account"
        variant="outline"
        className="text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950"
      >
        <Bot className="h-3 w-3 mr-1" />
        {license.service_account_name || t('serviceAccount')}
      </Badge>
    );
  }

  // External Guest badge - confirmed external guest
  if (license.match_status === 'external_guest') {
    badges.push(
      <Badge
        key="external-guest"
        variant="outline"
        className="text-green-600 dark:text-green-400 border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950"
      >
        <UserCheck className="h-3 w-3 mr-1" />
        {t('externalGuest')}
      </Badge>
    );
  }

  // Suggested Match badge - has suggested employee, needs review
  if (license.match_status === 'suggested' && license.suggested_employee_name) {
    const confidence = license.match_confidence ? Math.round(license.match_confidence * 100) : 0;
    badges.push(
      <Badge
        key="suggested"
        variant="outline"
        className="text-purple-600 dark:text-purple-400 border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-950"
      >
        <HelpCircle className="h-3 w-3 mr-1" />
        {t('suggestedMatch', { name: license.suggested_employee_name, percent: confidence })}
      </Badge>
    );
  }

  // External Review badge - external email needing decision
  if (license.match_status === 'external_review') {
    badges.push(
      <Badge
        key="external-review"
        variant="outline"
        className="text-orange-600 dark:text-orange-400 border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-950"
      >
        <AlertCircle className="h-3 w-3 mr-1" />
        {t('externalReview')}
      </Badge>
    );
  }

  // External badge - ALWAYS shown when is_external_email=true (legacy, not categorized yet)
  if (license.is_external_email && !license.match_status) {
    badges.push(
      <Badge
        key="external"
        variant="outline"
        className="text-orange-600 dark:text-orange-400 border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-950"
      >
        <Globe className="h-3 w-3 mr-1" />
        {t('external')}
      </Badge>
    );
  }

  // Offboarded badge - if employee status is offboarded
  if (license.employee_status === 'offboarded') {
    badges.push(
      <Badge
        key="offboarded"
        variant="outline"
        className="text-red-600 dark:text-red-400 border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950"
      >
        <Skull className="h-3 w-3 mr-1" />
        {t('offboarded')}
      </Badge>
    );
  }

  // Inactive badge - if status is inactive or suspended
  if (license.status === 'inactive' || license.status === 'suspended') {
    badges.push(
      <Badge
        key="inactive"
        variant="outline"
        className="text-muted-foreground border-border bg-muted"
      >
        <UserMinus className="h-3 w-3 mr-1" />
        {t('inactive')}
      </Badge>
    );
  }

  // Unassigned badge - if no employee linked and no suggested match
  if (showUnassigned && !license.employee_id && !license.match_status && badges.length === 0) {
    badges.push(
      <Badge
        key="unassigned"
        variant="outline"
        className="text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950"
      >
        {t('unassigned')}
      </Badge>
    );
  }

  if (badges.length === 0) {
    return null;
  }

  return <div className="flex items-center gap-1 flex-wrap">{badges}</div>;
}
