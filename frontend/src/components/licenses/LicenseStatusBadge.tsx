'use client';

import { Badge } from '@/components/ui/badge';
import { Globe, Skull, UserMinus, Bot } from 'lucide-react';

// Minimal type for LicenseStatusBadge - only the fields it actually needs
interface LicenseForBadge {
  is_external_email?: boolean;
  employee_id?: string | null;
  employee_status?: string | null;
  status?: string;
  is_service_account?: boolean;
  service_account_name?: string | null;
}

interface LicenseStatusBadgeProps {
  license: LicenseForBadge;
  showUnassigned?: boolean;
}

/**
 * Shows multiple status badges based on license state.
 * Badge Priority (all applicable badges shown):
 * 1. External (orange) - ALWAYS if is_external_email=true
 * 2. Offboarded (red) - if employee status is offboarded
 * 3. Inactive (gray) - if provider status is inactive/suspended
 * 4. Unassigned (amber) - if no employee linked (optional)
 */
export function LicenseStatusBadge({ license, showUnassigned = true }: LicenseStatusBadgeProps) {
  const badges: React.ReactNode[] = [];

  // Service Account badge - shown when is_service_account=true
  if (license.is_service_account) {
    badges.push(
      <Badge
        key="service-account"
        variant="outline"
        className="text-blue-600 border-blue-200 bg-blue-50"
      >
        <Bot className="h-3 w-3 mr-1" />
        {license.service_account_name || 'Service Account'}
      </Badge>
    );
  }

  // External badge - ALWAYS shown when is_external_email=true
  if (license.is_external_email) {
    badges.push(
      <Badge
        key="external"
        variant="outline"
        className="text-orange-600 border-orange-200 bg-orange-50"
      >
        <Globe className="h-3 w-3 mr-1" />
        External
      </Badge>
    );
  }

  // Offboarded badge - if employee status is offboarded
  if (license.employee_status === 'offboarded') {
    badges.push(
      <Badge
        key="offboarded"
        variant="outline"
        className="text-red-600 border-red-200 bg-red-50"
      >
        <Skull className="h-3 w-3 mr-1" />
        Offboarded
      </Badge>
    );
  }

  // Inactive badge - if status is inactive or suspended
  if (license.status === 'inactive' || license.status === 'suspended') {
    badges.push(
      <Badge
        key="inactive"
        variant="outline"
        className="text-zinc-500 border-zinc-200 bg-zinc-50"
      >
        <UserMinus className="h-3 w-3 mr-1" />
        Inactive
      </Badge>
    );
  }

  // Unassigned badge - if no employee linked
  if (showUnassigned && !license.employee_id && badges.length === 0) {
    badges.push(
      <Badge
        key="unassigned"
        variant="outline"
        className="text-amber-600 border-amber-200 bg-amber-50"
      >
        Unassigned
      </Badge>
    );
  }

  if (badges.length === 0) {
    return null;
  }

  return <div className="flex items-center gap-1 flex-wrap">{badges}</div>;
}
