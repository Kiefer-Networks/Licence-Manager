'use client';

import { useTranslations } from 'next-intl';
import { Users, AlertTriangle, Package, Globe } from 'lucide-react';
import { LicenseTab } from '@/hooks/use-licenses';

interface Tab {
  id: LicenseTab;
  label: string;
  count: number;
  icon: React.ReactNode;
  warning?: boolean;
}

interface LicenseTabsProps {
  activeTab: LicenseTab;
  onTabChange: (tab: LicenseTab) => void;
  assignedCount: number;
  notInHrisCount: number;
  unassignedCount: number;
  externalCount: number;
}

export function LicenseTabs({
  activeTab,
  onTabChange,
  assignedCount,
  notInHrisCount,
  unassignedCount,
  externalCount,
}: LicenseTabsProps) {
  const t = useTranslations('licenses');

  const tabs: Tab[] = [
    { id: 'assigned', label: t('assigned'), count: assignedCount, icon: <Users className="h-4 w-4" /> },
    ...(notInHrisCount > 0 ? [{ id: 'not_in_hris' as LicenseTab, label: t('notInHRIS'), count: notInHrisCount, icon: <AlertTriangle className="h-4 w-4" />, warning: true }] : []),
    ...(unassignedCount > 0 ? [{ id: 'unassigned' as LicenseTab, label: t('unassigned'), count: unassignedCount, icon: <Package className="h-4 w-4" />, warning: true }] : []),
    { id: 'external', label: t('external'), count: externalCount, icon: <Globe className="h-4 w-4" /> },
  ];

  return (
    <div className="border-b">
      <nav className="flex gap-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex items-center gap-2 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-zinc-900 text-zinc-900'
                : 'border-transparent text-muted-foreground hover:text-zinc-900'
            }`}
          >
            <span className={tab.warning ? 'text-red-500' : ''}>{tab.icon}</span>
            <span className={tab.warning ? 'text-red-600' : ''}>{tab.label}</span>
            <span
              className={`px-2 py-0.5 text-xs rounded-full ${
                activeTab === tab.id
                  ? tab.warning ? 'bg-red-600 text-white' : 'bg-zinc-900 text-white'
                  : tab.warning ? 'bg-red-100 text-red-700' : 'bg-zinc-100 text-zinc-600'
              }`}
            >
              {tab.count}
            </span>
          </button>
        ))}
      </nav>
    </div>
  );
}
