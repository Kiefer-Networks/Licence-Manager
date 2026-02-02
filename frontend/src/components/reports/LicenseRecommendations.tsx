'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { api, LicenseRecommendationsReport, LicenseRecommendation, Provider } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Loader2,
  Lightbulb,
  TrendingDown,
  AlertTriangle,
  XCircle,
  RefreshCcw,
  Eye,
  ChevronRight,
  Building2,
  User,
  Clock,
  DollarSign,
  ArrowRight,
} from 'lucide-react';
import { formatMonthlyCost } from '@/lib/format';
import Link from 'next/link';

interface LicenseRecommendationsProps {
  department?: string;
}

export function LicenseRecommendations({ department }: LicenseRecommendationsProps) {
  const t = useTranslations('reports');
  const tCommon = useTranslations('common');
  const tLicenses = useTranslations('licenses');

  const [report, setReport] = useState<LicenseRecommendationsReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>('all');
  const [minDaysInactive, setMinDaysInactive] = useState<number>(60);

  // Load providers once
  useEffect(() => {
    api.getProviders().then((res) => setProviders(res.items)).catch((e) => handleSilentError('getProviders', e));
  }, []);

  // Load recommendations when filters change
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    api.getLicenseRecommendations({
      min_days_inactive: minDaysInactive,
      department: department,
      provider_id: selectedProvider !== 'all' ? selectedProvider : undefined,
      limit: 100,
    }).then((data) => {
      if (!cancelled) {
        setReport(data);
      }
    }).catch((e) => handleSilentError('getLicenseRecommendations', e))
      .finally(() => !cancelled && setLoading(false));

    return () => { cancelled = true; };
  }, [department, selectedProvider, minDaysInactive]);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-700 border-red-200';
      case 'medium': return 'bg-amber-100 text-amber-700 border-amber-200';
      case 'low': return 'bg-blue-100 text-blue-700 border-blue-200';
      default: return 'bg-zinc-100 text-zinc-700 border-zinc-200';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'cancel': return <XCircle className="h-4 w-4 text-red-500" />;
      case 'reassign': return <RefreshCcw className="h-4 w-4 text-amber-500" />;
      case 'review': return <Eye className="h-4 w-4 text-blue-500" />;
      default: return <Lightbulb className="h-4 w-4 text-zinc-500" />;
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'cancel': return t('recommendCancel');
      case 'reassign': return t('recommendReassign');
      case 'review': return t('recommendReview');
      default: return type;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
      </div>
    );
  }

  if (!report || report.total_recommendations === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
        <Lightbulb className="h-12 w-12 mb-3 opacity-30" />
        <p className="text-lg font-medium">{t('noRecommendations')}</p>
        <p className="text-sm">{t('noRecommendationsHint')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-5 pb-4">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {t('totalRecommendations')}
            </p>
            <p className="text-3xl font-semibold mt-1 tabular-nums">{report.total_recommendations}</p>
            <div className="flex gap-2 mt-2">
              <Badge variant="outline" className={getPriorityColor('high')}>
                {report.high_priority_count} {t('priorityHigh')}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="border-emerald-200 bg-emerald-50/30 dark:bg-emerald-950/20 dark:border-emerald-800">
          <CardContent className="pt-5 pb-4">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {t('potentialMonthlySavings')}
            </p>
            <p className="text-3xl font-semibold mt-1 tabular-nums text-emerald-600 dark:text-emerald-400">
              {formatMonthlyCost(report.total_monthly_savings, report.currency)}
            </p>
            <p className="text-xs text-muted-foreground mt-1">{t('ifAllImplemented')}</p>
          </CardContent>
        </Card>

        <Card className="border-emerald-200 bg-emerald-50/30 dark:bg-emerald-950/20 dark:border-emerald-800">
          <CardContent className="pt-5 pb-4">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {t('potentialYearlySavings')}
            </p>
            <p className="text-3xl font-semibold mt-1 tabular-nums text-emerald-600 dark:text-emerald-400">
              {formatMonthlyCost(report.total_yearly_savings, report.currency)}
            </p>
            <p className="text-xs text-muted-foreground mt-1">{t('projectedAnnual')}</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-5 pb-4">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {t('byPriority')}
            </p>
            <div className="flex flex-col gap-1 mt-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-red-600 dark:text-red-400">{t('priorityHigh')}</span>
                <span className="font-medium">{report.high_priority_count}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-amber-600 dark:text-amber-400">{t('priorityMedium')}</span>
                <span className="font-medium">{report.medium_priority_count}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-blue-600 dark:text-blue-400">{t('priorityLow')}</span>
                <span className="font-medium">{report.low_priority_count}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Select value={selectedProvider} onValueChange={setSelectedProvider}>
          <SelectTrigger className="w-52 h-9 bg-zinc-50 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700">
            <Building2 className="h-4 w-4 mr-2 text-zinc-400" />
            <SelectValue placeholder={tLicenses('provider')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{tLicenses('allProviders')}</SelectItem>
            {providers.filter(p => p.name !== 'hibob' && p.name !== 'personio').map((provider) => (
              <SelectItem key={provider.id} value={provider.id}>{provider.display_name}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={minDaysInactive.toString()} onValueChange={(v) => setMinDaysInactive(parseInt(v))}>
          <SelectTrigger className="w-44 h-9 bg-zinc-50 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700">
            <Clock className="h-4 w-4 mr-2 text-zinc-400" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="30">{t('inactiveDays', { days: 30 })}</SelectItem>
            <SelectItem value="60">{t('inactiveDays', { days: 60 })}</SelectItem>
            <SelectItem value="90">{t('inactiveDays', { days: 90 })}</SelectItem>
            <SelectItem value="180">{t('inactiveDays', { days: 180 })}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Recommendations List */}
      <div className="space-y-3">
        {report.recommendations.map((rec) => (
          <Card key={rec.license_id} className="hover:shadow-md transition-shadow">
            <CardContent className="py-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div className="mt-1">{getTypeIcon(rec.recommendation_type)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium truncate">{rec.external_user_id}</span>
                      <Badge variant="outline" className={getPriorityColor(rec.priority)}>
                        {rec.priority === 'high' ? t('priorityHigh') : rec.priority === 'medium' ? t('priorityMedium') : t('priorityLow')}
                      </Badge>
                      <Badge variant="outline" className="bg-zinc-50 dark:bg-zinc-800">
                        {getTypeLabel(rec.recommendation_type)}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">{rec.recommendation_reason}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Building2 className="h-3 w-3" />
                        {rec.provider_name}
                      </span>
                      {rec.employee_name && (
                        <span className="flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {rec.employee_name}
                          {rec.employee_status === 'offboarded' && (
                            <Badge variant="destructive" className="ml-1 h-4 px-1 text-[10px]">
                              {tLicenses('offboarded')}
                            </Badge>
                          )}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {t('daysInactiveCount', { days: rec.days_inactive })}
                      </span>
                      {rec.license_type && (
                        <span className="text-zinc-500">{rec.license_type}</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4 flex-shrink-0">
                  {rec.monthly_cost && parseFloat(rec.monthly_cost) > 0 && (
                    <div className="text-right">
                      <p className="font-medium tabular-nums">
                        {formatMonthlyCost(rec.monthly_cost, 'EUR')}
                        <span className="text-xs text-muted-foreground">/mo</span>
                      </p>
                      {rec.yearly_savings && parseFloat(rec.yearly_savings) > 0 && (
                        <p className="text-xs text-emerald-600 dark:text-emerald-400">
                          {formatMonthlyCost(rec.yearly_savings, 'EUR')}/yr
                        </p>
                      )}
                    </div>
                  )}
                  <Link href={`/licenses?search=${encodeURIComponent(rec.external_user_id)}`}>
                    <Button variant="ghost" size="sm">
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
