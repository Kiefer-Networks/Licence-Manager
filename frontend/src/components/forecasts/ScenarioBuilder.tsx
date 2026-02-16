'use client';

import { useTranslations } from 'next-intl';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Loader2, Plus, Trash2, Play, RotateCcw } from 'lucide-react';
import { ScenarioAdjustment, ScenarioResult, ScenarioType, ProviderForecast } from '@/lib/api';
import { useLocale } from '@/components/locale-provider';

interface ScenarioBuilderProps {
  adjustments: ScenarioAdjustment[];
  onAddAdjustment: () => void;
  onRemoveAdjustment: (index: number) => void;
  onUpdateAdjustment: (index: number, update: Partial<ScenarioAdjustment>) => void;
  onRunSimulation: () => void;
  onReset: () => void;
  scenarioResult: ScenarioResult | null;
  loading: boolean;
  providers: ProviderForecast[];
  departments: string[];
}

const SCENARIO_TYPES: ScenarioType[] = [
  'add_employees',
  'remove_employees',
  'add_provider',
  'remove_provider',
  'change_seats',
  'change_billing',
];

export function ScenarioBuilder({
  adjustments,
  onAddAdjustment,
  onRemoveAdjustment,
  onUpdateAdjustment,
  onRunSimulation,
  onReset,
  scenarioResult,
  loading,
  providers,
  departments,
}: ScenarioBuilderProps) {
  const t = useTranslations('forecasts');
  const { formatCurrency } = useLocale();

  const typeLabels: Record<ScenarioType, string> = {
    add_employees: t('addEmployees'),
    remove_employees: t('removeEmployees'),
    add_provider: t('addProvider'),
    remove_provider: t('removeProvider'),
    change_seats: t('changeSeats'),
    change_billing: t('changeBilling'),
  };

  const needsProvider = (type: ScenarioType) =>
    ['remove_provider', 'change_seats', 'change_billing'].includes(type);

  const needsDepartment = (type: ScenarioType) =>
    ['add_employees', 'remove_employees'].includes(type);

  const needsBillingCycle = (type: ScenarioType) =>
    type === 'change_billing';

  const getValueLabel = (type: ScenarioType) => {
    switch (type) {
      case 'add_employees':
      case 'remove_employees':
        return t('employeeCount');
      case 'add_provider':
        return t('monthlyCost');
      case 'change_seats':
        return t('newSeatCount');
      default:
        return t('adjustmentValue');
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">{t('scenarioBuilder')}</CardTitle>
            <p className="text-xs text-muted-foreground mt-1">{t('scenarioDescription')}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onReset} disabled={adjustments.length === 0}>
              <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
              {t('resetScenario')}
            </Button>
            <Button size="sm" onClick={onRunSimulation} disabled={adjustments.length === 0 || loading}>
              {loading ? (
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
              ) : (
                <Play className="h-3.5 w-3.5 mr-1.5" />
              )}
              {t('runSimulation')}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {adjustments.map((adj, idx) => (
          <div key={idx} className="flex items-end gap-2 p-3 rounded-lg border bg-zinc-50 dark:bg-zinc-900">
            {/* Type selector */}
            <div className="flex-1 min-w-[140px]">
              <Label className="text-xs">{t('adjustmentType')}</Label>
              <Select
                value={adj.type}
                onValueChange={(value: string) =>
                  onUpdateAdjustment(idx, { type: value as ScenarioType })
                }
              >
                <SelectTrigger className="mt-1 h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SCENARIO_TYPES.map((type) => (
                    <SelectItem key={type} value={type} className="text-xs">
                      {typeLabels[type]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Provider selector (conditional) */}
            {needsProvider(adj.type) && (
              <div className="flex-1 min-w-[140px]">
                <Label className="text-xs">{t('selectProvider')}</Label>
                <Select
                  value={adj.provider_id || ''}
                  onValueChange={(value: string) =>
                    onUpdateAdjustment(idx, { provider_id: value })
                  }
                >
                  <SelectTrigger className="mt-1 h-8 text-xs">
                    <SelectValue placeholder={t('selectProvider')} />
                  </SelectTrigger>
                  <SelectContent>
                    {providers.map((p) => (
                      <SelectItem key={p.provider_id} value={p.provider_id} className="text-xs">
                        {p.display_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Provider name for add_provider */}
            {adj.type === 'add_provider' && (
              <div className="flex-1 min-w-[120px]">
                <Label className="text-xs">{t('providerName')}</Label>
                <Input
                  className="mt-1 h-8 text-xs"
                  value={adj.provider_name || ''}
                  onChange={(e) =>
                    onUpdateAdjustment(idx, { provider_name: e.target.value })
                  }
                />
              </div>
            )}

            {/* Department selector (conditional) */}
            {needsDepartment(adj.type) && (
              <div className="flex-1 min-w-[120px]">
                <Label className="text-xs">{t('selectDepartment')}</Label>
                <Select
                  value={adj.department || ''}
                  onValueChange={(value: string) =>
                    onUpdateAdjustment(idx, { department: value })
                  }
                >
                  <SelectTrigger className="mt-1 h-8 text-xs">
                    <SelectValue placeholder={t('selectDepartment')} />
                  </SelectTrigger>
                  <SelectContent>
                    {departments.map((d) => (
                      <SelectItem key={d} value={d} className="text-xs">
                        {d}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Value input (not needed for remove_provider) */}
            {adj.type !== 'remove_provider' && !needsBillingCycle(adj.type) && (
              <div className="w-28">
                <Label className="text-xs">{getValueLabel(adj.type)}</Label>
                <Input
                  type="number"
                  className="mt-1 h-8 text-xs"
                  min={0}
                  value={adj.value}
                  onChange={(e) =>
                    onUpdateAdjustment(idx, { value: Number(e.target.value) || 0 })
                  }
                />
              </div>
            )}

            {/* Billing cycle selector */}
            {needsBillingCycle(adj.type) && (
              <div className="w-28">
                <Label className="text-xs">{t('newBillingCycle')}</Label>
                <Select
                  value={adj.new_billing_cycle || ''}
                  onValueChange={(value: string) =>
                    onUpdateAdjustment(idx, { new_billing_cycle: value })
                  }
                >
                  <SelectTrigger className="mt-1 h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="monthly" className="text-xs">{t('monthly')}</SelectItem>
                    <SelectItem value="yearly" className="text-xs">{t('yearly')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Effective month */}
            <div className="w-20">
              <Label className="text-xs">{t('effectiveMonth')}</Label>
              <Input
                type="number"
                className="mt-1 h-8 text-xs"
                min={1}
                max={24}
                value={adj.effective_month}
                onChange={(e) =>
                  onUpdateAdjustment(idx, {
                    effective_month: Math.max(1, Math.min(24, Number(e.target.value) || 1)),
                  })
                }
              />
            </div>

            {/* Remove button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onRemoveAdjustment(idx)}
              className="h-8 w-8 p-0 text-muted-foreground hover:text-red-500"
              aria-label={t('removeAdjustment')}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        ))}

        <Button
          variant="outline"
          size="sm"
          onClick={onAddAdjustment}
          className="w-full"
          disabled={adjustments.length >= 20}
        >
          <Plus className="h-3.5 w-3.5 mr-1.5" />
          {t('addAdjustment')}
        </Button>

        {/* Scenario result */}
        {scenarioResult && (
          <div className="mt-4 p-4 rounded-lg border bg-white dark:bg-zinc-950">
            <h4 className="text-sm font-medium mb-3">{t('scenarioResult')}</h4>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">{t('baselineTotal')}</p>
                <p className="text-base font-semibold tabular-nums mt-0.5">
                  {formatCurrency(scenarioResult.baseline_total)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{t('scenarioTotal')}</p>
                <p className="text-base font-semibold tabular-nums mt-0.5">
                  {formatCurrency(scenarioResult.scenario_total)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{t('difference')}</p>
                <p className={`text-base font-semibold tabular-nums mt-0.5 ${
                  Number(scenarioResult.difference) > 0
                    ? 'text-red-600'
                    : Number(scenarioResult.difference) < 0
                      ? 'text-emerald-600'
                      : ''
                }`}>
                  {Number(scenarioResult.difference) > 0 ? '+' : ''}
                  {formatCurrency(scenarioResult.difference)}
                  <span className="text-xs ml-1">
                    ({scenarioResult.difference_percent > 0 ? '+' : ''}{scenarioResult.difference_percent}%)
                  </span>
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
