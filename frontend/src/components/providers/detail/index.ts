/**
 * Provider detail page components.
 *
 * These components are extracted from the monolithic providers/[id]/page.tsx
 * to improve maintainability and separation of concerns.
 *
 * TODO: Extract remaining tabs:
 * - PricingTab (~670 lines) - complex pricing management with packages and org licenses
 * - SettingsTab (~750 lines) - provider settings and credentials management
 */

export { OverviewTab } from './OverviewTab';
export { LicensesTab } from './LicensesTab';
export { FilesTab } from './FilesTab';

export type * from './types';
