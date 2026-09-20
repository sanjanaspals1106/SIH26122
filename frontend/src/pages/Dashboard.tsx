import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  dashboardApi,
  decisionsApi,
  executionSummaryApi,
  ExecutionSummaryResponse,
  ScheduleActivity,
  PlannerDecision,
  DisciplineForecastData,
  DisciplineForecastItem,
} from '@/api';
import {
  AlertTriangle,
  Activity,
  TrendingDown,
  CheckCircle2,
  Layers,
  Clock,
  RefreshCw,
  ArrowUpRight,
  ShieldCheck,
  Download,
  BrainCircuit,
  Volume2,
  FileSpreadsheet,
  TrendingUp,
  XCircle,
  BarChart3,
  Zap,
  Sparkles,
  Globe2,
  Filter,
  Calendar,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, PieChart, Pie } from 'recharts';
import { cn } from '@/lib/utils';

const CHART_COLORS = {
  indigo: '#6366f1',
  blue: '#3b82f6',
  amber: '#f59e0b',
  violet: '#a855f7',
  emerald: '#10b981',
  orange: '#FC4C02',
  navy: '#001E60',
};

export default function Dashboard() {
  const { t } = useTranslation();
  const [summary, setSummary] = useState<{
    total_claims: number;
    pending_review: number;
    actuals: number;
    conflicts: number;
    discipline_breakdown: { discipline: string; name: string; count: number; value: number }[];
  } | null>(null);
  const [delayReasons, setDelayReasons] = useState<{ reason: string; count: number }[]>([]);
  const [institutionalMemory, setInstitutionalMemory] = useState<{ topic: string; resolution: string; count: number }[]>([]);
  const [forecastData, setForecastData] = useState<DisciplineForecastData | null>(null);
  const [selectedDiscipline, setSelectedDiscipline] = useState<string>('CIVIL');
  const [isForecastLoading, setIsForecastLoading] = useState<boolean>(false);
  const [silentActivities, setSilentActivities] = useState<ScheduleActivity[]>([]);
  const [recentDecisions, setRecentDecisions] = useState<PlannerDecision[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Phase 7: AI Execution Summary & Dynamic Translation
  const [execSummary, setExecSummary] = useState<ExecutionSummaryResponse | null>(null);
  const [summaryPeriod, setSummaryPeriod] = useState<'last_7_days' | 'this_month' | 'custom'>('last_7_days');
  const [summaryStartDate, setSummaryStartDate] = useState<string>('');
  const [summaryEndDate, setSummaryEndDate] = useState<string>('');
  const [summaryDiscipline, setSummaryDiscipline] = useState<string>('ALL');
  const [summaryLanguage, setSummaryLanguage] = useState<'en' | 'hi' | 'te'>('en');
  const [isSummaryLoading, setIsSummaryLoading] = useState<boolean>(false);

  const handleDisciplineChange = async (discipline: string) => {
    setSelectedDiscipline(discipline);
    setIsForecastLoading(true);
    try {
      const data = await dashboardApi.getForecast(discipline);
      setForecastData(data);
    } catch (err) {
      console.error('Failed to load forecast for discipline:', discipline, err);
    } finally {
      setIsForecastLoading(false);
    }
  };

  const loadExecutionSummary = async (
    period = summaryPeriod,
    discipline = summaryDiscipline,
    language = summaryLanguage,
    startDate = summaryStartDate,
    endDate = summaryEndDate
  ) => {
    setIsSummaryLoading(true);
    try {
      const data = await executionSummaryApi.getSummary({
        period,
        discipline,
        language,
        start_date: period === 'custom' ? startDate : undefined,
        end_date: period === 'custom' ? endDate : undefined,
      });
      setExecSummary(data);
    } catch (e) {
      console.error('Failed to load execution summary:', e);
    } finally {
      setIsSummaryLoading(false);
    }
  };

  const loadDashboardData = async () => {
    setIsLoading(true);
    try {
      const [sum, reasons, memory, fc, silent, decisions] = await Promise.all([
        dashboardApi.getSummary(),
        dashboardApi.getDelayReasons(),
        dashboardApi.getInstitutionalMemory(),
        dashboardApi.getForecast(selectedDiscipline),
        dashboardApi.getSilentActivities(),
        decisionsApi.getRecent(),
      ]);
      setSummary(sum);
      setDelayReasons(reasons);
      setInstitutionalMemory(memory);
      setForecastData(fc);
      setSilentActivities(silent);
      setRecentDecisions(decisions);
    } catch (e) {
      // Fallback handled gracefully
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
    loadExecutionSummary();
  }, []);

  const handleExportCsv = () => {
    window.open(dashboardApi.getExportCsvUrl(), '_blank');
  };

  const disciplinePalette = [
    CHART_COLORS.orange,
    CHART_COLORS.blue,
    CHART_COLORS.amber,
    CHART_COLORS.violet,
    CHART_COLORS.emerald,
  ];

  const disciplineData = summary?.discipline_breakdown?.length
    ? summary.discipline_breakdown.map((item, idx) => ({
        name: item.name || item.discipline,
        value: item.value ?? item.count,
        fill: disciplinePalette[idx % disciplinePalette.length],
      }))
    : [
        { name: 'CIVIL', value: 0, fill: CHART_COLORS.orange },
      ];

  const kpiCards = [
    {
      label: t('dashboard.totalClaims'),
      value: summary?.total_claims ?? 0,
      icon: Activity,
      accent: 'text-[#001E60] dark:text-blue-300',
      bg: 'bg-blue-50 dark:bg-blue-900/30',
      border: 'border-blue-200 dark:border-blue-800',
      delta: '+12% vs last week',
      deltaPositive: true,
    },
    {
      label: t('dashboard.pendingReview'),
      value: summary?.pending_review ?? 0,
      icon: Clock,
      accent: 'text-amber-600 dark:text-amber-400',
      bg: 'bg-amber-50 dark:bg-amber-900/30',
      border: 'border-amber-200 dark:border-amber-800',
      delta: 'Requires action',
      deltaPositive: false,
    },
    {
      label: t('dashboard.approvedActuals'),
      value: summary?.actuals ?? 0,
      icon: CheckCircle2,
      accent: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-50 dark:bg-emerald-900/30',
      border: 'border-emerald-200 dark:border-emerald-800',
      delta: 'P6 Sync ready',
      deltaPositive: true,
    },
    {
      label: t('dashboard.activeConflicts'),
      value: summary?.conflicts ?? 0,
      icon: AlertTriangle,
      accent: 'text-rose-600 dark:text-rose-400',
      bg: 'bg-rose-50 dark:bg-rose-900/30',
      border: 'border-rose-200 dark:border-rose-800',
      delta: 'Flagged for review',
      deltaPositive: null,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Header Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-blue-900/50 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-[#FC4C02]/10 border border-[#FC4C02]/20">
              <BarChart3 className="w-5 h-5 text-[#FC4C02]" />
            </div>
            {t('dashboard.title')}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-xs mt-1">
            {t('dashboard.subtitle')}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={() => {
              loadDashboardData();
              loadExecutionSummary();
            }}
            variant="outline"
            className="border-slate-300 dark:border-blue-800 text-slate-700 dark:text-blue-100 hover:bg-slate-100 dark:hover:bg-blue-900/50 h-9 text-xs gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            {t('dashboard.refresh')}
          </Button>
          <Button
            onClick={handleExportCsv}
            className="bg-[#FC4C02] hover:bg-[#e04302] text-white font-medium text-xs h-9 shadow-md shadow-[#FC4C02]/20 gap-1.5"
          >
            <Download className="w-4 h-4" /> {t('dashboard.exportCsv')}
          </Button>
        </div>
      </div>

      {/* Phase 7: AI Execution Summary & Dynamic Translation Panel */}
      <Card className="bg-gradient-to-br from-white to-blue-50/40 dark:from-[#001E60]/90 dark:to-[#001440] border-blue-200 dark:border-blue-900/60 shadow-sm">
        <CardHeader className="pb-3 border-b border-blue-100 dark:border-blue-900/40">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-blue-600 text-white shadow-sm shadow-blue-500/30">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <CardTitle className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  AI Execution Summary
                  {execSummary?.generated_by === 'llm' && (
                    <span className="text-[10px] font-semibold uppercase tracking-wider bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 px-2 py-0.5 rounded-full">
                      LLM Synthesized
                    </span>
                  )}
                  {execSummary?.generated_by === 'deterministic_fallback' && (
                    <span className="text-[10px] font-semibold uppercase tracking-wider bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 px-2 py-0.5 rounded-full">
                      Deterministic Verified
                    </span>
                  )}
                  {execSummary?.cached && (
                    <span className="text-[10px] font-semibold uppercase tracking-wider bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 px-2 py-0.5 rounded-full">
                      Cache HIT
                    </span>
                  )}
                </CardTitle>
                <CardDescription className="text-xs text-slate-500 dark:text-slate-400">
                  Supervisor intelligence compiled from verified site logs, actuals, conflicts, and delay records
                </CardDescription>
              </div>
            </div>

            {/* Filter Toolbar: Period, Discipline, Language */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              {/* Period Selector */}
              <div className="flex items-center gap-1 bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-blue-900/60 rounded-lg p-0.5">
                <button
                  type="button"
                  onClick={() => {
                    setSummaryPeriod('last_7_days');
                    loadExecutionSummary('last_7_days', summaryDiscipline, summaryLanguage);
                  }}
                  className={cn(
                    'px-2.5 py-1 rounded-md font-medium transition-colors',
                    summaryPeriod === 'last_7_days'
                      ? 'bg-blue-600 text-white shadow-xs'
                      : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
                  )}
                >
                  Last 7 Days
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSummaryPeriod('this_month');
                    loadExecutionSummary('this_month', summaryDiscipline, summaryLanguage);
                  }}
                  className={cn(
                    'px-2.5 py-1 rounded-md font-medium transition-colors',
                    summaryPeriod === 'this_month'
                      ? 'bg-blue-600 text-white shadow-xs'
                      : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
                  )}
                >
                  This Month
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSummaryPeriod('custom');
                  }}
                  className={cn(
                    'px-2.5 py-1 rounded-md font-medium transition-colors',
                    summaryPeriod === 'custom'
                      ? 'bg-blue-600 text-white shadow-xs'
                      : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
                  )}
                >
                  Custom
                </button>
              </div>

              {/* Discipline Dropdown */}
              <select
                value={summaryDiscipline}
                onChange={(e) => {
                  const val = e.target.value;
                  setSummaryDiscipline(val);
                  loadExecutionSummary(summaryPeriod, val, summaryLanguage, summaryStartDate, summaryEndDate);
                }}
                className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-blue-900/60 text-slate-700 dark:text-slate-200 rounded-lg px-2 py-1 font-medium focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="ALL">All Disciplines</option>
                <option value="CIVIL">Civil</option>
                <option value="PIPING">Piping</option>
                <option value="STATIC_ROTATING_EQUIPMENT">Mechanical / Equipment</option>
                <option value="ELECTRICAL">Electrical</option>
                <option value="INSTRUMENTATION">Instrumentation</option>
                <option value="HSE">HSE</option>
              </select>

              {/* Language Dropdown */}
              <div className="flex items-center gap-1 bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-blue-900/60 rounded-lg px-2 py-1 text-slate-700 dark:text-slate-200">
                <Globe2 className="w-3.5 h-3.5 text-blue-500" />
                <select
                  value={summaryLanguage}
                  onChange={(e) => {
                    const lang = e.target.value as 'en' | 'hi' | 'te';
                    setSummaryLanguage(lang);
                    loadExecutionSummary(summaryPeriod, summaryDiscipline, lang, summaryStartDate, summaryEndDate);
                  }}
                  className="bg-transparent text-slate-700 dark:text-slate-200 font-medium focus:outline-none"
                >
                  <option value="en">English (Canonical)</option>
                  <option value="hi">हिन्दी (Hindi)</option>
                  <option value="te">తెలుగు (Telugu)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Custom Date Range Picker */}
          {summaryPeriod === 'custom' && (
            <div className="flex items-center gap-2 pt-2 text-xs">
              <span className="text-slate-500 dark:text-slate-400">From:</span>
              <input
                type="date"
                value={summaryStartDate}
                onChange={(e) => setSummaryStartDate(e.target.value)}
                className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-blue-900/60 rounded px-2 py-1 text-slate-700 dark:text-slate-200"
              />
              <span className="text-slate-500 dark:text-slate-400">To:</span>
              <input
                type="date"
                value={summaryEndDate}
                onChange={(e) => setSummaryEndDate(e.target.value)}
                className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-blue-900/60 rounded px-2 py-1 text-slate-700 dark:text-slate-200"
              />
              <Button
                size="sm"
                onClick={() => loadExecutionSummary('custom', summaryDiscipline, summaryLanguage, summaryStartDate, summaryEndDate)}
                className="h-7 text-xs bg-blue-600 hover:bg-blue-700 text-white"
              >
                Apply Range
              </Button>
            </div>
          )}
        </CardHeader>

        <CardContent className="pt-3 pb-4">
          {isSummaryLoading ? (
            <div className="py-8 flex flex-col items-center justify-center gap-2 text-slate-400 text-xs">
              <RefreshCw className="w-5 h-5 animate-spin text-blue-500" />
              <span>Generating verified execution summary...</span>
            </div>
          ) : execSummary ? (
            <div className="space-y-3">
              <div className="bg-white/80 dark:bg-slate-900/50 border border-slate-200/80 dark:border-blue-900/40 rounded-xl p-4 text-xs leading-relaxed text-slate-800 dark:text-slate-200 whitespace-pre-line font-normal shadow-xs">
                {execSummary.summary}
              </div>

              {/* Verified Metrics Strip */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-1">
                <div className="p-2 rounded-lg bg-blue-50/80 dark:bg-blue-950/40 border border-blue-100 dark:border-blue-900/40 text-[11px]">
                  <span className="text-slate-500 dark:text-slate-400 block font-medium">Scope Activities</span>
                  <span className="font-bold text-blue-700 dark:text-blue-300 font-mono text-sm">
                    {execSummary.aggregate.activities.total}
                  </span>
                  <span className="text-[10px] text-slate-400 block">
                    {execSummary.aggregate.activities.completed} Done · {execSummary.aggregate.activities.in_progress} Active
                  </span>
                </div>

                <div className="p-2 rounded-lg bg-emerald-50/80 dark:bg-emerald-950/40 border border-emerald-100 dark:border-emerald-900/40 text-[11px]">
                  <span className="text-slate-500 dark:text-slate-400 block font-medium">Progress Claims</span>
                  <span className="font-bold text-emerald-700 dark:text-emerald-300 font-mono text-sm">
                    {execSummary.aggregate.claims.total_claims}
                  </span>
                  <span className="text-[10px] text-slate-400 block">
                    {execSummary.aggregate.approved_progress.total_approved} Approved ({execSummary.aggregate.approved_progress.avg_approved_pct}%)
                  </span>
                </div>

                <div className="p-2 rounded-lg bg-amber-50/80 dark:bg-amber-950/40 border border-amber-100 dark:border-amber-900/40 text-[11px]">
                  <span className="text-slate-500 dark:text-slate-400 block font-medium">Conflicts</span>
                  <span className="font-bold text-amber-700 dark:text-amber-300 font-mono text-sm">
                    {execSummary.aggregate.conflicts.total_conflicts}
                  </span>
                  <span className="text-[10px] text-slate-400 block">
                    {execSummary.aggregate.conflicts.by_status?.OPEN || 0} Open
                  </span>
                </div>

                <div className="p-2 rounded-lg bg-rose-50/80 dark:bg-rose-950/40 border border-rose-100 dark:border-rose-900/40 text-[11px]">
                  <span className="text-slate-500 dark:text-slate-400 block font-medium">Delay Events</span>
                  <span className="font-bold text-rose-700 dark:text-rose-300 font-mono text-sm">
                    {execSummary.aggregate.delays.total_delay_events}
                  </span>
                  <span className="text-[10px] text-slate-400 block">
                    {Object.keys(execSummary.aggregate.delays.reasons || {}).length} Factors Reported
                  </span>
                </div>

                <div className="p-2 rounded-lg bg-violet-50/80 dark:bg-violet-950/40 border border-violet-100 dark:border-violet-900/40 text-[11px] col-span-2 sm:col-span-1">
                  <span className="text-slate-500 dark:text-slate-400 block font-medium">Historical Ratio</span>
                  <span className="font-bold text-violet-700 dark:text-violet-300 font-mono text-sm">
                    {execSummary.aggregate.forecast.historical_ratio ? `${execSummary.aggregate.forecast.historical_ratio}×` : 'N/A'}
                  </span>
                  <span className="text-[10px] text-slate-400 block">
                    {execSummary.aggregate.forecast.historical_ratio ? 'Discipline Multiplier' : 'Select Discipline'}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="py-6 text-center text-slate-400 text-xs">
              Click refresh to generate the project execution summary.
            </div>
          )}
        </CardContent>
      </Card>

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
            <Card key={kpi.label} className={cn('border', kpi.border, 'bg-white dark:bg-[#001E60]/80 shadow-sm hover:shadow-md transition-shadow')}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className={cn('p-2 rounded-lg', kpi.bg)}>
                    <Icon className={cn('w-4 h-4', kpi.accent)} />
                  </div>
                </div>
                <div className={cn('text-3xl font-bold mt-3 font-mono', kpi.accent)}>{kpi.value}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wide mt-1">{kpi.label}</div>
                {kpi.delta && (
                  <div className={cn('text-[11px] mt-1.5 flex items-center gap-1 font-medium', kpi.deltaPositive === true ? 'text-emerald-600 dark:text-emerald-400' : kpi.deltaPositive === false ? 'text-rose-500 dark:text-rose-400' : 'text-slate-500 dark:text-slate-400')}>
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
        <Card className="bg-white dark:bg-[#001E60]/80 border-slate-200 dark:border-blue-900/50 text-slate-900 dark:text-slate-100 lg:col-span-7 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center justify-between">
              <span className="flex items-center gap-2">
                <TrendingDown className="w-4 h-4 text-rose-500" />
                {t('dashboard.delayReasonsTitle')}
              </span>
              <span className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded-full font-mono">{t('dashboard.paretoAnalysis')}</span>
            </CardTitle>
            <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
              {t('dashboard.delayReasonsDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={delayReasons} layout="vertical" margin={{ top: 5, right: 30, left: 100, bottom: 5 }}>
                <XAxis type="number" stroke="#94a3b8" fontSize={11} />
                <YAxis dataKey="reason" type="category" stroke="#94a3b8" fontSize={10} tickLine={false} width={150} />
                <Tooltip contentStyle={{ backgroundColor: '#001E60', borderColor: '#1e3a8a', borderRadius: '8px', fontSize: '11px', color: '#f8fafc' }} />
                <Bar dataKey="count" fill={CHART_COLORS.orange} radius={[0, 4, 4, 0]} barSize={16} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Discipline Pie (5 Cols) */}
        <Card className="bg-white dark:bg-[#001E60]/80 border-slate-200 dark:border-blue-900/50 text-slate-900 dark:text-slate-100 lg:col-span-5 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
              {t('dashboard.disciplineVolumeTitle')}
            </CardTitle>
            <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
              {t('dashboard.disciplineVolumeDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-2 flex items-center justify-center h-64">
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
          </CardContent>
        </Card>
      </div>

      {/* Grid: Institutional Memory & Schedule Forecast */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Institutional Memory (6 Cols) */}
        <Card className="bg-white dark:bg-[#001E60]/80 border-slate-200 dark:border-blue-900/50 text-slate-900 dark:text-slate-100 lg:col-span-6 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-violet-100 dark:bg-violet-500/10 border border-violet-200 dark:border-violet-500/20">
                <BrainCircuit className="w-3.5 h-3.5 text-violet-600 dark:text-violet-400" />
              </div>
              <span className="text-violet-700 dark:text-violet-300">{t('dashboard.institutionalMemoryTitle')}</span>
            </CardTitle>
            <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
              {t('dashboard.institutionalMemoryDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4 space-y-3">
            {institutionalMemory.length === 0 ? (
              <div className="text-center py-8 text-slate-400 dark:text-slate-500 text-xs">{t('dashboard.noInstitutionalMemory')}</div>
            ) : institutionalMemory.map((mem, idx) => (
              <div key={idx} className="p-3 bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-700 rounded-xl space-y-1 text-xs hover:border-violet-300 dark:hover:border-violet-700/50 transition-colors">
                <div className="flex items-center justify-between text-slate-800 dark:text-slate-200 font-bold">
                  <span>{mem.topic}</span>
                  <span className="text-[10px] bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300 border border-violet-200 dark:border-violet-500/30 px-2 py-0.5 rounded-full font-mono">
                    {mem.count}×
                  </span>
                </div>
                <p className="text-slate-500 dark:text-slate-400 leading-relaxed text-[11px]">{mem.resolution}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Schedule Forecast (6 Cols) */}
        <Card className="bg-white dark:bg-[#001E60]/80 border-slate-200 dark:border-blue-900/50 text-slate-900 dark:text-slate-100 lg:col-span-6 shadow-sm flex flex-col">
          <CardHeader className="pb-3 border-b border-slate-100 dark:border-blue-900/40">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-blue-100 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/20">
                    <Clock className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <span>{t('dashboard.forecastTitle')}</span>
                  <span className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded-full font-mono">
                    {t('dashboard.ratioForecast')}
                  </span>
                </CardTitle>
                <CardDescription className="text-slate-500 dark:text-slate-400 text-xs mt-1">
                  {t('dashboard.forecastDesc')}
                </CardDescription>
              </div>

              {forecastData?.historical_ratio != null && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-400 text-xs font-mono font-medium self-start sm:self-auto">
                  <TrendingUp className="w-3.5 h-3.5" />
                  <span>{forecastData.historical_ratio.toFixed(2)}× Multiplier</span>
                </div>
              )}
            </div>

            {/* Discipline Selector Pills */}
            <div className="flex items-center gap-1.5 mt-3 pt-2 border-t border-slate-100 dark:border-slate-800/60 overflow-x-auto pb-1">
              <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium mr-1 flex items-center gap-1 shrink-0">
                <Filter className="w-3 h-3" /> Discipline:
              </span>
              {['CIVIL', 'PIPING', 'ELECTRICAL', 'MECHANICAL', 'STRUCTURAL'].map((disc) => {
                const isActive = selectedDiscipline === disc;
                return (
                  <button
                    key={disc}
                    type="button"
                    onClick={() => handleDisciplineChange(disc)}
                    className={cn(
                      "px-2.5 py-0.5 text-[11px] rounded-md font-medium transition-all shrink-0",
                      isActive
                        ? "bg-blue-600 text-white shadow-sm font-semibold"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
                    )}
                  >
                    {disc}
                  </button>
                );
              })}
            </div>
          </CardHeader>

          <CardContent className="pt-3 space-y-2.5 text-xs flex-1 max-h-[360px] overflow-y-auto">
            {isForecastLoading ? (
              <div className="flex flex-col items-center justify-center py-10 text-slate-400 gap-2">
                <RefreshCw className="w-5 h-5 animate-spin text-blue-500" />
                <span className="text-xs">Computing historical ratio forecast...</span>
              </div>
            ) : !forecastData || forecastData.activities.length === 0 ? (
              <div className="text-center py-10 text-slate-400 dark:text-slate-500 text-xs flex flex-col items-center gap-1">
                <AlertTriangle className="w-6 h-6 text-slate-400 mb-1 opacity-60" />
                <span className="font-medium">No forecast activities for {selectedDiscipline}</span>
                <span className="text-[11px]">No matching schedule activities or baseline durations found.</span>
              </div>
            ) : (
              forecastData.activities.map((fc, idx) => {
                const maxDuration = Math.max(fc.planned_duration || 0, fc.forecast_duration || 0, 1);
                const plannedPct = Math.round(((fc.planned_duration || 0) / maxDuration) * 100);
                const forecastPct = Math.round(((fc.forecast_duration || 0) / maxDuration) * 100);
                const hasSlip = (fc.slippage_days || 0) > 0;

                return (
                  <div
                    key={idx}
                    className="p-3 bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 rounded-xl hover:border-blue-400/40 dark:hover:border-blue-700/50 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-medium text-slate-800 dark:text-slate-200 truncate max-w-[70%] font-mono text-[12px]">
                        {fc.activity_id}
                      </div>
                      <div className="text-right font-mono">
                        {hasSlip ? (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-bold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                            +{fc.slippage_days}d slip
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                            On Schedule
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Dual Duration Comparison Bars */}
                    <div className="space-y-1.5 text-[11px]">
                      <div className="flex items-center gap-2">
                        <span className="w-14 text-slate-500 dark:text-slate-400 text-[10px]">Planned</span>
                        <div className="flex-1 bg-slate-200 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-blue-500 h-full rounded-full transition-all duration-300"
                            style={{ width: `${plannedPct}%` }}
                          />
                        </div>
                        <span className="w-14 text-right font-mono text-slate-700 dark:text-slate-300">
                          {fc.planned_duration != null ? `${fc.planned_duration}d` : 'N/A'}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="w-14 text-slate-500 dark:text-slate-400 text-[10px]">Forecast</span>
                        <div className="flex-1 bg-slate-200 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                          <div
                            className={cn(
                              "h-full rounded-full transition-all duration-300",
                              hasSlip ? "bg-amber-500" : "bg-emerald-500"
                            )}
                            style={{ width: `${forecastPct}%` }}
                          />
                        </div>
                        <span className={cn(
                          "w-14 text-right font-mono font-medium",
                          hasSlip ? "text-amber-600 dark:text-amber-400" : "text-emerald-600 dark:text-emerald-400"
                        )}>
                          {fc.forecast_duration != null ? `${fc.forecast_duration}d` : 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Supervisor Decisions */}
      <Card className="bg-white dark:bg-[#001E60]/80 border-slate-200 dark:border-blue-900/50 text-slate-900 dark:text-slate-100 shadow-sm">
        <CardHeader className="pb-2 border-b border-slate-200 dark:border-blue-900/50">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
            {t('dashboard.recentDecisionsTitle')}
          </CardTitle>
          <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
            {t('dashboard.recentDecisionsDesc')}
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-2">
          <div className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
            {recentDecisions.length === 0 ? (
              <div className="py-8 text-center text-slate-400 dark:text-slate-500">{t('dashboard.noRecentDecisions')}</div>
            ) : recentDecisions.map((dec) => (
              <div key={dec.decision_id} className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 group hover:bg-slate-50 dark:hover:bg-blue-900/20 px-2 rounded-lg transition-colors">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono font-bold text-[#001E60] dark:text-blue-200 bg-blue-100 dark:bg-blue-900/80 px-2 py-0.5 rounded-md text-[11px]">
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
                    <span className="text-slate-500 dark:text-slate-400 font-mono">{t('dashboard.eventLabel')}: {dec.event_id}</span>
                  </div>
                  <p className="text-slate-600 dark:text-slate-300 text-xs">"{dec.justification}"</p>
                </div>
                <div className="text-slate-400 dark:text-slate-500 font-mono text-[11px] shrink-0">
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
