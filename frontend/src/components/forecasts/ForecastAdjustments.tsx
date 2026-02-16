'use client';

import { useTranslations } from 'next-intl';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import { RotateCcw, Loader2 } from 'lucide-react';

interface ForecastAdjustmentsProps {
  priceAdjustment: number;
  onPriceAdjustmentChange: (value: number) => void;
  headcountChange: number;
  onHeadcountChangeChange: (value: number) => void;
  onReset: () => void;
  hasAdjustments: boolean;
  adjusting: boolean;
}

export function ForecastAdjustments({
  priceAdjustment,
  onPriceAdjustmentChange,
  headcountChange,
  onHeadcountChangeChange,
  onReset,
  hasAdjustments,
  adjusting,
}: ForecastAdjustmentsProps) {
  const t = useTranslations('forecasts');

  return (
    <Card className="w-80 shrink-0">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{t('adjustments')}</CardTitle>
          {adjusting && (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
          )}
        </div>
        <p className="text-xs text-muted-foreground">{t('adjustmentsDescription')}</p>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Price adjustment slider */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-xs">{t('priceAdjustment')}</Label>
            <span className={`text-xs font-medium tabular-nums ${
              priceAdjustment > 0
                ? 'text-red-500'
                : priceAdjustment < 0
                  ? 'text-emerald-500'
                  : 'text-muted-foreground'
            }`}>
              {priceAdjustment > 0 ? '+' : ''}{priceAdjustment}%
            </span>
          </div>
          <Slider
            value={[priceAdjustment]}
            onValueChange={([v]) => onPriceAdjustmentChange(v)}
            min={-50}
            max={50}
            step={1}
          />
          <div className="flex justify-between text-[10px] text-muted-foreground">
            <span>-50%</span>
            <span>0%</span>
            <span>+50%</span>
          </div>
        </div>

        {/* Headcount change slider */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-xs">{t('headcountChange')}</Label>
            <span className={`text-xs font-medium tabular-nums ${
              headcountChange > 0
                ? 'text-red-500'
                : headcountChange < 0
                  ? 'text-emerald-500'
                  : 'text-muted-foreground'
            }`}>
              {headcountChange > 0 ? '+' : ''}{headcountChange}
            </span>
          </div>
          <Slider
            value={[headcountChange]}
            onValueChange={([v]) => onHeadcountChangeChange(v)}
            min={-50}
            max={50}
            step={1}
          />
          <div className="flex justify-between text-[10px] text-muted-foreground">
            <span>-50</span>
            <span>0</span>
            <span>+50</span>
          </div>
        </div>

        {/* Reset button */}
        <Button
          variant="outline"
          size="sm"
          onClick={onReset}
          disabled={!hasAdjustments}
          className="w-full"
        >
          <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
          {t('resetToBaseline')}
        </Button>
      </CardContent>
    </Card>
  );
}
