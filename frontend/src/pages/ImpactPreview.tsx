import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Activity,
  GitBranch,
  Info,
  AlertTriangle,
  TrendingUp,
} from 'lucide-react';
import { schedulesApi, ImpactPreviewResult, ScheduleActivity } from '@/api';
import { PrecedenceRippleGraph } from '@/components/PrecedenceRippleGraph';

export default function ImpactPreview() {
  const { t } = useTranslation();
  const [activityId, setActivityId] = useState('');
  const [delayDays, setDelayDays] = useState(5);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState<ImpactPreviewResult | null>(null);
  const [activities, setActivities] = useState<ScheduleActivity[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    schedulesApi
      .getActivities()
      .then((data) => setActivities(data))
      .catch(() => {});
  }, []);

  const handleSimulate = async () => {
    setIsSimulating(true);
    setError(null);
    try {
      const res = await schedulesApi.getImpactPreview(activityId, delayDays);
      setSimulationResult(res);
    } catch (e: any) {
      setError(t('impact.failedToCompute', { message: e.message }));
    } finally {
      setIsSimulating(false);
    }
  };

  const originActivity = activities.find(
    (a) => a.activity_id === (simulationResult?.activity_id || activityId)
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-slate-300 dark:border-[#214766]/60 pb-4">
        <div>
          <h1 className="text-2xl font-extrabold text-[#071A2D] dark:text-[#F5F7FA] tracking-tight flex items-center gap-2.5">
            <div className="p-1.5 rounded-xl bg-teal-50 dark:bg-[#0A2340] border border-teal-300 dark:border-[#1E3A5F] shadow-xs">
              <GitBranch className="w-5 h-5 text-[#14B8A6] dark:text-[#22D3EE]" />
            </div>
            {t('impact.title')}
          </h1>
          <p className="text-[#334155] dark:text-[#CBD5E1] text-xs font-semibold mt-1">
            {t('impact.subtitle')}
          </p>
        </div>
      </div>

      {/* Scope Disclaimer */}
      <div className="p-3.5 rounded-xl bg-sky-50 dark:bg-sky-950/40 border border-sky-200 dark:border-sky-800/60 text-sky-900 dark:text-sky-300 text-xs flex items-center gap-2.5 shadow-xs">
        <Info className="w-4 h-4 text-sky-600 dark:text-sky-400 shrink-0" />
        <span>
          <strong className="font-bold">{t('impact.scopeDisclaimerLabel')}</strong> {t('impact.scopeDisclaimer')}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Form Inputs */}
        <Card className="shadow-xl lg:col-span-1 border-slate-200/80 dark:border-[#214766] bg-white/95 dark:bg-[#071A2D]/95 rounded-2xl">
          <CardHeader className="border-b border-slate-300 dark:border-[#214766]/60 pb-4">
            <CardTitle className="text-sm font-extrabold flex items-center gap-2 text-[#071A2D] dark:text-[#F5F7FA]">
              <Activity className="w-4 h-4 text-[#14B8A6] dark:text-[#22D3EE]" />
              {t('impact.simulationInputs')}
            </CardTitle>
            <CardDescription className="text-[#475569] dark:text-[#9FB2C3] text-xs font-medium mt-0.5">
              {t('impact.simulationInputsDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5 text-xs p-6">
            {error && (
              <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 text-rose-700 dark:text-rose-300 rounded-xl flex items-start gap-2">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                {error}
              </div>
            )}

            <div className="space-y-1.5">
              <Label className="text-xs text-[#071A2D] dark:text-[#C5D2DE] font-bold">{t('impact.activityIdLabel')}</Label>
              <Input
                value={activityId}
                onChange={(e) => setActivityId(e.target.value)}
                placeholder={t('impact.activityIdPlaceholder')}
                className="font-mono text-xs rounded-xl bg-white dark:bg-[#0B2742] border-slate-300 dark:border-[#214766] text-[#071A2D] dark:text-[#F5F7FA] placeholder:text-slate-500 dark:placeholder:text-[#8FA6BA]"
              />
              <p className="text-[11px] text-[#64748B] dark:text-[#9FB2C3] font-medium">{t('impact.activityIdHint')}</p>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-[#071A2D] dark:text-[#C5D2DE] font-bold">{t('impact.delayLabel')}</Label>
              <div className="relative">
                <Input
                  type="number"
                  min={1}
                  max={90}
                  value={delayDays}
                  onChange={(e) => setDelayDays(Number(e.target.value))}
                  className="font-mono text-xs rounded-xl bg-white dark:bg-[#0B2742] border-slate-300 dark:border-[#214766] text-[#071A2D] dark:text-[#F5F7FA] pr-16"
                />
                <span className="absolute right-3 top-2.5 text-[#64748B] dark:text-[#9FB2C3] text-xs font-mono">{t('impact.days')}</span>
              </div>
              <p className="text-[11px] text-[#64748B] dark:text-[#9FB2C3] font-medium">{t('impact.delayRangeHint')}</p>
            </div>

            {/* Visual delay severity indicator */}
            <div className="space-y-2">
              <div className="flex justify-between text-[10px] text-[#64748B] dark:text-[#9FB2C3] font-mono font-bold">
                <span>{t('impact.lowImpact')}</span>
                <span>{t('impact.highImpact')}</span>
              </div>
              <div className="h-2 rounded-full bg-gradient-to-r from-amber-400 via-[#FF7A18] to-rose-600 relative shadow-xs">
                <div
                  className="absolute top-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full bg-white border-2 border-slate-800 shadow-md transition-all"
                  style={{ left: `${Math.min(((delayDays - 1) / 89) * 100, 100)}%` }}
                />
              </div>
            </div>

            <Button
              onClick={handleSimulate}
              disabled={isSimulating || !activityId.trim()}
              isLoading={isSimulating}
              className="w-full text-white font-bold h-11 text-xs shadow-md shadow-orange-500/25 rounded-xl gap-2 bg-gradient-to-r from-[#FF7A18] to-[#FF941F] hover:from-[#E06810] hover:to-[#FF7A18]"
            >
              <TrendingUp className="w-4 h-4" />
              {t('impact.runAnalysis')}
            </Button>
          </CardContent>
        </Card>

        {/* Right Column: Results & Precedence Ripple Graph */}
        <div className="lg:col-span-2 space-y-6">
          {!simulationResult ? (
            <Card className="shadow-xl h-full min-h-[320px] flex items-center justify-center text-center p-8 border-slate-200/80 dark:border-[#214766] bg-white/95 dark:bg-[#071A2D]/95 rounded-2xl">
              <div className="space-y-3.5 max-w-sm">
                <div className="w-14 h-14 rounded-2xl bg-teal-50 dark:bg-[#0A2340] border border-teal-200 dark:border-[#1E3A5F] flex items-center justify-center mx-auto shadow-xs">
                  <GitBranch className="w-7 h-7 text-[#14B8A6] dark:text-[#22D3EE]" />
                </div>
                <h3 className="text-[#071A2D] dark:text-[#F5F7FA] font-extrabold text-sm">{t('impact.noSimulationTitle')}</h3>
                <p className="text-xs text-[#475569] dark:text-[#9FB2C3] font-medium leading-relaxed">
                  {t('impact.noSimulationDesc')}{' '}
                  <strong className="text-[#FF7A18] dark:text-[#FF941F]">{t('impact.runAnalysis')}</strong> {t('impact.noSimulationDescEnd')}
                </p>
              </div>
            </Card>
          ) : (
            <div className="space-y-5 animate-in fade-in duration-300">
              {/* Summary Banner */}
              <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800/60 flex items-start gap-3 shadow-xs">
                <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-bold text-amber-900 dark:text-amber-200">
                    {t('impact.delayRippleSummary', {
                      days: simulationResult.delay_days,
                      activityId: simulationResult.activity_id,
                      count: simulationResult.successors.length,
                      plural: simulationResult.successors.length !== 1 ? 's' : '',
                    })}
                  </p>
                  <p className="text-xs text-amber-700 dark:text-amber-300/90 font-medium mt-0.5">
                    {t('impact.commitAfterReview')}
                  </p>
                </div>
              </div>

              {/* Connected Finish-to-Start Precedence Ripple Graph */}
              <PrecedenceRippleGraph
                result={simulationResult}
                originActivityName={originActivity?.activity_name}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}