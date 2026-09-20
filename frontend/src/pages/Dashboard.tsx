import React, { useEffect, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  dashboardApi,
  decisionsApi,
  digestApi,
  ScheduleActivity,
  PlannerDecision,
  ExecutionEvent,
} from '@/api';
import {
  AlertTriangle,
  TrendingDown,
  CheckCircle2,
  Layers,
  Clock,
  RefreshCw,
  ArrowUpRight,
  ShieldCheck,
  Download,
  BrainCircuit,
  FileSpreadsheet,
  XCircle,
  BarChart3,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, PieChart, Pie } from 'recharts';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';

const CHART_COLORS = {
  indigo: '#14B8A6',
  blue: '#22D3EE',
  amber: '#f59e0b',
  violet: '#818cf8',
  emerald: '#10b981',
  orange: '#FF7A18',
  navy: '#0A2340',
};

const DISCIPLINE_COLORS: Record<string, string> = {
  CIVIL: CHART_COLORS.orange,
  PIPING: CHART_COLORS.blue,
  ELECTRICAL: CHART_COLORS.amber,
  INSTRUMENTATION: CHART_COLORS.violet,
  HSE: CHART_COLORS.emerald,
  STATIC_ROTATING_EQUIPMENT: CHART_COLORS.navy,
  UNASSIGNED: '#94a3b8',
};

export default function Dashboard() {
  const { t } = useTranslation();
  const [delayReasons, setDelayReasons] = useState<{ reason: string; count: number }[]>([]);
  const [institutionalMemory, setInstitutionalMemory] = useState<{ topic: string; resolution: string; count: number }[]>([]);
  const [forecasts, setForecasts] = useState<{ milestone: string; target_date: string; forecast_date: string; slippage_days: number }[]>([]);
  const [silentActivities, setSilentActivities] = useState<ScheduleActivity[]>([]);
  const [recentDecisions, setRecentDecisions] = useState<PlannerDecision[]>([]);
  const [claims, setClaims] = useState<ExecutionEvent[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const loadDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [reasons, memory, fc, silent, decisions, allClaims] = await Promise.all([
        dashboardApi.getDelayReasons(),
        dashboardApi.getInstitutionalMemory(),
        dashboardApi.getForecast(),
        dashboardApi.getSilentActivities(),
        decisionsApi.getRecent(),
        digestApi.getAll(),
      ]);
      setDelayReasons(reasons);
      setInstitutionalMemory(memory);
      setForecasts(fc);
      setSilentActivities(silent);
      setRecentDecisions(decisions);
      setClaims(allClaims);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to load dashboard data';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleExportCsv = async () => {
    setIsExporting(true);
    setExportError(null);
    try {
      const blob = await dashboardApi.exportCsv();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'approved_actuals.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to export CSV';
      setExportError(msg);
    } finally {
      setIsExporting(false);
    }
  };

  const disciplineData = useMemo(() => {
    if (!claims || claims.length === 0) return [];
    const counts: Record<string, number> = {};
    claims.forEach((c) => {
      const d = c.discipline || 'UNASSIGNED';
      counts[d] = (counts[d] || 0) + 1;
    });
    return Object.entries(counts).map(([name, value]) => ({
      name,
      value,
      fill: DISCIPLINE_COLORS[name] || CHART_COLORS.indigo,
    }));
  }, [claims]);

  const kpiCards = useMemo(() => {
    const totalClaimsCount = claims.length;
    const pendingReviewCount = claims.filter(
      (c) => c.status === 'REVIEW_REQUIRED' || c.status === 'VALIDATED'
    ).length;
    const actualsCommittedCount = claims.filter(
      (c) => c.status === 'APPROVED' || c.status === 'EDITED'
    ).length;

    return [
      {
        label: t('dashboard.kpiTotalClaims'),
        value: isLoading ? '...' : String(totalClaimsCount),
        delta: t('dashboard.kpiTotalClaimsDelta'),
        deltaPositive: true,
        icon: FileSpreadsheet,
        accent: 'text-[#14B8A6] dark:text-[#22D3EE]',
        bg: 'bg-teal-50 dark:bg-[#0A2340]',
        border: 'border-teal-200 dark:border-[#1E3A5F]',
      },
      {
        label: t('dashboard.kpiPendingReview'),
        value: isLoading ? '...' : String(pendingReviewCount),
        delta: t('dashboard.kpiPendingReviewDelta'),
        deltaPositive: null,
        icon: Clock,
        accent: 'text-amber-600 dark:text-amber-400',
        bg: 'bg-amber-50 dark:bg-amber-950/60',
        border: 'border-amber-200 dark:border-amber-900/60',
      },
      {
        label: t('dashboard.kpiActualsCommitted'),
        value: isLoading ? '...' : String(actualsCommittedCount),
        delta: t('dashboard.kpiActualsCommittedDelta'),
        deltaPositive: true,
        icon: CheckCircle2,
        accent: 'text-emerald-600 dark:text-emerald-400',
        bg: 'bg-emerald-50 dark:bg-emerald-950/60',
        border: 'border-emerald-200 dark:border-emerald-900/60',
      },
      {
        label: t('dashboard.kpiOpenConflicts'),
        value: t('review.notAvailable'), // Open conflicts cannot be computed without a project-wide conflicts endpoint
        delta: t('dashboard.kpiOpenConflictsDelta'),
        deltaPositive: false,
        icon: XCircle,
        accent: 'text-rose-600 dark:text-rose-400',
        bg: 'bg-rose-50 dark:bg-rose-950/60',
        border: 'border-rose-200 dark:border-rose-900/60',
      },
    ];
  }, [claims, isLoading, t]);

  return (
    <div className="space-y-6">
      {/* Top Header Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-300 dark:border-[#214766]/60 pb-4">
        <div>
          <h1 className="text-2xl font-extrabold text-[#071A2D] dark:text-[#F5F7FA] tracking-tight flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-[#FF7A18]/10 border border-[#FF7A18]/20">
              <BarChart3 className="w-5 h-5 text-[#FF7A18]" />
            </div>
            {t('dashboard.title')}
          </h1>
          <p className="text-[#334155] dark:text-[#CBD5E1] text-xs font-semibold mt-1">
            {t('dashboard.subtitle')}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={loadDashboardData}
            variant="outline"
            disabled={isLoading}
            className="border-slate-300 dark:border-[#1E3A5F] text-foreground hover:bg-secondary h-9 text-xs gap-1.5"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', isLoading && 'animate-spin')} />
            {t('dashboard.refresh')}
          </Button>
          <Button
            onClick={handleExportCsv}
            disabled={isExporting}
            className="bg-gradient-to-r from-[#FF7A18] to-[#FF941F] hover:from-[#E06810] hover:to-[#FF7A18] text-white font-semibold text-xs h-9 shadow-md shadow-orange-500/25 gap-1.5"
          >
            {isExporting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            {t('dashboard.exportCsv')}
          </Button>
        </div>
      </div>

      {/* Error Banners */}
      {error && (
        <ErrorState
          message={error}
          onRetry={loadDashboardData}
          retryText={t('common.retry')}
        />
      )}

      {exportError && (
        <ErrorState
          message={exportError}
          onRetry={handleExportCsv}
          retryText={t('common.retry')}
        />
      )}

      {/* Silent Activities Alert Banner */}
      {silentActivities.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-400/40 dark:border-amber-500/30 text-amber-800 dark:text-amber-300 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5 text-amber-500" />
          <div className="flex-1">
            <h4 className="font-bold text-xs uppercase tracking-wider text-amber-700 dark:text-amber-400">
              {t('dashboard.silentAlertTitle', { count: silentActivities.length })}
            </h4>
            <p className="text-xs mt-0.5 text-amber-700 dark:text-amber-200/90">
              {t('dashboard.silentAlertDesc')}
            </p>
            <div className="flex flex-wrap gap-2 mt-2">
              {silentActivities.map((act) => (
                <span key={act.activity_id} className="bg-amber-100 dark:bg-amber-950/80 border border-amber-400/40 dark:border-amber-500/40 text-amber-800 dark:text-amber-300 text-[11px] px-2.5 py-1 rounded-md font-mono">
                  {act.activity_id}: {act.activity_name}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards Bar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {kpiCards.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <Card key={kpi.label} className={cn('border', kpi.border, 'bg-card shadow-xs hover:shadow-sm transition-shadow')}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className={cn('p-2 rounded-lg', kpi.bg)}>
                    <Icon className={cn('w-4 h-4', kpi.accent)} />
                  </div>
                </div>
                {isLoading ? (
                  <Skeleton className="h-8 w-16 mt-3" />
                ) : (
                  <div className={cn('text-3xl font-bold mt-3 font-mono', kpi.accent)}>{kpi.value}</div>
                )}
                <div className="text-xs text-muted-foreground font-semibold uppercase tracking-wide mt-1">{kpi.label}</div>
                {kpi.delta && (
                  <div className={cn('text-[11px] mt-1.5 flex items-center gap-1 font-medium', kpi.deltaPositive === true ? 'text-emerald-600 dark:text-emerald-400' : kpi.deltaPositive === false ? 'text-rose-500 dark:text-rose-400' : 'text-muted-foreground')}>
                    {kpi.deltaPositive === true && <ArrowUpRight className="w-3.5 h-3.5" />}
                    {kpi.deltaPositive === false && <TrendingDown className="w-3.5 h-3.5" />}
                    {kpi.delta}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Grid: Delay Reasons Chart & Discipline Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Delay Reasons Bar Chart (7 Cols) */}
        <Card className="bg-card border-border text-foreground lg:col-span-7 shadow-xs">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center justify-between">
              <span className="flex items-center gap-2">
                <TrendingDown className="w-4 h-4 text-rose-500" />
                {t('dashboard.delayReasonsTitle')}
              </span>
              <span className="text-[10px] bg-secondary text-secondary-foreground px-2 py-0.5 rounded-full font-mono">{t('dashboard.paretoAnalysis')}</span>
            </CardTitle>
            <CardDescription className="text-muted-foreground text-xs">
              {t('dashboard.delayReasonsDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4 h-64">
            {isLoading ? (
              <div className="space-y-3 pt-4">
                <Skeleton className="h-6 w-full" />
                <Skeleton className="h-6 w-4/5" />
                <Skeleton className="h-6 w-3/5" />
                <Skeleton className="h-6 w-2/5" />
              </div>
            ) : delayReasons.length === 0 ? (
              <div className="text-center py-16 text-muted-foreground text-xs">
                {t('dashboard.delayReasonsDesc')}
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={delayReasons} layout="vertical" margin={{ top: 5, right: 30, left: 100, bottom: 5 }}>
                  <XAxis type="number" stroke="#94a3b8" fontSize={11} />
                  <YAxis dataKey="reason" type="category" stroke="#94a3b8" fontSize={10} tickLine={false} width={150} />
                  <Tooltip contentStyle={{ backgroundColor: '#001E60', borderColor: '#1e3a8a', borderRadius: '8px', fontSize: '11px', color: '#f8fafc' }} />
                  <Bar dataKey="count" fill={CHART_COLORS.orange} radius={[0, 4, 4, 0]} barSize={16} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Discipline Pie (5 Cols) */}
        <Card className="bg-card border-border text-foreground lg:col-span-5 shadow-xs">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#1565C0] dark:text-blue-400" />
              {t('dashboard.disciplineVolumeTitle')}
            </CardTitle>
            <CardDescription className="text-muted-foreground text-xs">
              {t('dashboard.disciplineVolumeDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-2 flex items-center justify-center h-64">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center gap-2">
                <Skeleton className="h-36 w-36 rounded-full" />
                <Skeleton className="h-4 w-24" />
              </div>
            ) : disciplineData.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground text-xs">
                {t('dashboard.disciplineVolumeDesc')}
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={disciplineData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={75}
                    innerRadius={40}
                    paddingAngle={4}
                    label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                    fontSize={10}
                  >
                    {disciplineData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#001E60', borderColor: '#1e3a8a', borderRadius: '8px', fontSize: '11px' }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Grid: Institutional Memory & Schedule Forecast */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Institutional Memory (6 Cols) */}
        <Card className="bg-card border-border text-foreground lg:col-span-6 shadow-xs">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-900/60">
                <BrainCircuit className="w-3.5 h-3.5 text-[#1565C0] dark:text-blue-400" />
              </div>
              <span className="text-[#003087] dark:text-blue-300">{t('dashboard.institutionalMemoryTitle')}</span>
            </CardTitle>
            <CardDescription className="text-muted-foreground text-xs">
              {t('dashboard.institutionalMemoryDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4 space-y-3">
            {isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full rounded-xl" />
                <Skeleton className="h-16 w-full rounded-xl" />
              </div>
            ) : institutionalMemory.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground text-xs">{t('dashboard.noInstitutionalMemory')}</div>
            ) : institutionalMemory.map((mem, idx) => (
              <div key={idx} className="p-3 bg-card-subtle border border-border rounded-xl space-y-1 text-xs hover:border-[#1565C0]/40 transition-colors">
                <div className="flex items-center justify-between text-foreground font-bold">
                  <span>{mem.topic}</span>
                  <span className="text-[10px] bg-blue-100 dark:bg-blue-950/80 text-[#1565C0] dark:text-blue-300 border border-blue-200 dark:border-blue-900/60 px-2 py-0.5 rounded-full font-mono">
                    {mem.count}×
                  </span>
                </div>
                <p className="text-muted-foreground leading-relaxed text-[11px]">{mem.resolution}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Schedule Forecast (6 Cols) */}
        <Card className="bg-card border-border text-foreground lg:col-span-6 shadow-xs">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center justify-between">
              <span className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-900/60">
                  <Clock className="w-3.5 h-3.5 text-[#1565C0] dark:text-blue-400" />
                </div>
                {t('dashboard.forecastTitle')}
              </span>
              <span className="text-[10px] bg-secondary text-secondary-foreground px-2 py-0.5 rounded-full font-mono">
                {t('dashboard.ratioForecast')}
              </span>
            </CardTitle>
            <CardDescription className="text-muted-foreground text-xs">
              {t('dashboard.forecastDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4 space-y-3 text-xs">
            {isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full rounded-xl" />
                <Skeleton className="h-16 w-full rounded-xl" />
              </div>
            ) : forecasts.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground text-xs">{t('dashboard.noForecastData')}</div>
            ) : forecasts.map((fc, idx) => (
              <div key={idx} className="p-3 bg-card-subtle border border-border rounded-xl flex items-center justify-between hover:border-amber-300 dark:hover:border-amber-700/50 transition-colors">
                <div>
                  <div className="font-bold text-foreground">{fc.milestone}</div>
                  <div className="text-muted-foreground text-[11px] mt-0.5">
                    {t('dashboard.target')}: <span className="font-mono">{fc.target_date}</span> · {t('dashboard.forecast')}: <span className="font-mono text-amber-600 dark:text-amber-400">{fc.forecast_date}</span>
                  </div>
                </div>
                <div className="text-right font-mono">
                  <span className="text-rose-600 dark:text-rose-400 font-bold text-sm">+{fc.slippage_days}d</span>
                  <div className="text-[10px] text-muted-foreground">{t('dashboard.slippage')}</div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Recent Supervisor Decisions */}
      <Card className="bg-card border-border text-foreground shadow-xs">
        <CardHeader className="pb-2 border-b border-border">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
            {t('dashboard.recentDecisionsTitle')}
          </CardTitle>
          <CardDescription className="text-muted-foreground text-xs">
            {t('dashboard.recentDecisionsDesc')}
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-2">
          <div className="divide-y divide-border/60 text-xs">
            {isLoading ? (
              <div className="space-y-3 py-3">
                <Skeleton className="h-12 w-full rounded-lg" />
                <Skeleton className="h-12 w-full rounded-lg" />
              </div>
            ) : recentDecisions.length === 0 ? (
              <div className="py-8 text-center text-muted-foreground">{t('dashboard.noRecentDecisions')}</div>
            ) : recentDecisions.map((dec) => (
              <div key={dec.decision_id} className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 group hover:bg-secondary/40 px-2 rounded-lg transition-colors">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono font-bold text-[#003087] dark:text-blue-200 bg-blue-100 dark:bg-blue-900/80 px-2 py-0.5 rounded-md text-[11px]">
                      {dec.selected_activity_id}
                    </span>
                    <span className={cn(
                      'text-[10px] font-bold px-2 py-0.5 rounded-full uppercase',
                      dec.action === 'APPROVE'
                        ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                        : dec.action === 'EDIT' || dec.action === 'HOLD'
                        ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400'
                        : 'bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-400'
                    )}>
                      {dec.action}
                    </span>
                    <span className="text-muted-foreground font-mono">{t('dashboard.eventLabel')}: {dec.event_id}</span>
                  </div>
                  <p className="text-foreground/90 text-xs">"{dec.justification}"</p>
                </div>
                <div className="text-muted-foreground font-mono text-[11px] shrink-0">
                  {t('dashboard.plannerLabel')}: {dec.planner_id}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
