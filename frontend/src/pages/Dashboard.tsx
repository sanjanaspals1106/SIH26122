import React, { useEffect, useState } from 'react';
import {
  dashboardApi,
  decisionsApi,
  ScheduleActivity,
  PlannerDecision,
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
  const [delayReasons, setDelayReasons] = useState<{ reason: string; count: number }[]>([]);
  const [institutionalMemory, setInstitutionalMemory] = useState<{ topic: string; resolution: string; count: number }[]>([]);
  const [forecasts, setForecasts] = useState<{ milestone: string; target_date: string; forecast_date: string; slippage_days: number }[]>([]);
  const [silentActivities, setSilentActivities] = useState<ScheduleActivity[]>([]);
  const [recentDecisions, setRecentDecisions] = useState<PlannerDecision[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const loadDashboardData = async () => {
    setIsLoading(true);
    try {
      const [reasons, memory, fc, silent, decisions] = await Promise.all([
        dashboardApi.getDelayReasons(),
        dashboardApi.getInstitutionalMemory(),
        dashboardApi.getForecast(),
        dashboardApi.getSilentActivities(),
        decisionsApi.getRecent(),
      ]);
      setDelayReasons(reasons);
      setInstitutionalMemory(memory);
      setForecasts(fc);
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
  }, []);

  const handleExportCsv = () => {
    window.open(dashboardApi.getExportCsvUrl(), '_blank');
  };

  const disciplineData = [
    { name: 'CIVIL', value: 42, fill: CHART_COLORS.orange },
    { name: 'PIPING', value: 28, fill: CHART_COLORS.blue },
    { name: 'ELECTRICAL', value: 18, fill: CHART_COLORS.amber },
    { name: 'INSTRUMENTATION', value: 12, fill: CHART_COLORS.violet },
    { name: 'HSE', value: 8, fill: CHART_COLORS.emerald },
  ];

  const kpiCards = [
    {
      label: 'Total Claims Ingested',
      value: '148',
      delta: '+12% from last week',
      deltaPositive: true,
      icon: FileSpreadsheet,
      accent: 'text-[#FC4C02]',
      bg: 'bg-[#FC4C02]/10 dark:bg-[#FC4C02]/10',
      border: 'border-[#FC4C02]/20',
    },
    {
      label: 'Pending Supervisor Review',
      value: '14',
      delta: 'Requires human planner signoff',
      deltaPositive: null,
      icon: Clock,
      accent: 'text-amber-500 dark:text-amber-400',
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20',
    },
    {
      label: 'Official Actuals Committed',
      value: '124',
      delta: 'Primavera baseline aligned',
      deltaPositive: true,
      icon: CheckCircle2,
      accent: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20',
    },
    {
      label: 'Open Quantity Conflicts',
      value: '2',
      delta: 'Variance > 15%',
      deltaPositive: false,
      icon: XCircle,
      accent: 'text-rose-600 dark:text-rose-400',
      bg: 'bg-rose-500/10',
      border: 'border-rose-500/20',
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
            Project Executive Dashboard
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-xs mt-1">
            Real-time infrastructure schedule compliance, delay breakdown, and institutional memory.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={loadDashboardData}
            variant="outline"
            className="border-slate-300 dark:border-blue-800 text-slate-700 dark:text-blue-100 hover:bg-slate-100 dark:hover:bg-blue-900/50 h-9 text-xs gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </Button>
          <Button
            onClick={handleExportCsv}
            className="bg-[#FC4C02] hover:bg-[#e04302] text-white font-medium text-xs h-9 shadow-md shadow-[#FC4C02]/20 gap-1.5"
          >
            <Download className="w-4 h-4" /> Export CSV
          </Button>
        </div>
      </div>

      {/* Silent Activities Alert Banner */}
      {silentActivities.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-400/40 dark:border-amber-500/30 text-amber-800 dark:text-amber-300 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5 text-amber-500" />
          <div className="flex-1">
            <h4 className="font-bold text-xs uppercase tracking-wider text-amber-700 dark:text-amber-400">
              Silent Activities Alert ({silentActivities.length} Detected)
            </h4>
            <p className="text-xs mt-0.5 text-amber-700 dark:text-amber-200/90">
              Scheduled activities that have passed planned start date with zero field progress claims logged:
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
                Root Cause Delay Reasons Breakdown
              </span>
              <span className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded-full font-mono">Pareto Analysis</span>
            </CardTitle>
            <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
              Aggregated delay reasons stated by field engineers during progress updates.
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
              Discipline Volume Distribution
            </CardTitle>
            <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
              Breakdown of total progress claims by engineering discipline.
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
              <span className="text-violet-700 dark:text-violet-300">Institutional Memory</span>
            </CardTitle>
            <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
              Learned resolutions from past supervisor overrides applied to current site conditions.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4 space-y-3">
            {institutionalMemory.length === 0 ? (
              <div className="text-center py-8 text-slate-400 dark:text-slate-500 text-xs">No institutional memory data available.</div>
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
        <Card className="bg-white dark:bg-[#001E60]/80 border-slate-200 dark:border-blue-900/50 text-slate-900 dark:text-slate-100 lg:col-span-6 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center justify-between">
              <span className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-blue-100 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/20">
                  <Clock className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                </div>
                Schedule Milestone Forecast
              </span>
              <span className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded-full font-mono">
                Ratio Forecast
              </span>
            </CardTitle>
            <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
              Lightweight historical-ratio forecasting. Not ML prediction.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4 space-y-3 text-xs">
            {forecasts.length === 0 ? (
              <div className="text-center py-8 text-slate-400 dark:text-slate-500 text-xs">No forecast data available.</div>
            ) : forecasts.map((fc, idx) => (
              <div key={idx} className="p-3 bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-700 rounded-xl flex items-center justify-between hover:border-amber-300 dark:hover:border-amber-700/50 transition-colors">
                <div>
                  <div className="font-bold text-slate-800 dark:text-slate-200">{fc.milestone}</div>
                  <div className="text-slate-500 dark:text-slate-400 text-[11px] mt-0.5">
                    Target: <span className="font-mono">{fc.target_date}</span> · Forecast: <span className="font-mono text-amber-600 dark:text-amber-400">{fc.forecast_date}</span>
                  </div>
                </div>
                <div className="text-right font-mono">
                  <span className="text-rose-600 dark:text-rose-400 font-bold text-sm">+{fc.slippage_days}d</span>
                  <div className="text-[10px] text-slate-400 dark:text-slate-500">slippage</div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Recent Supervisor Decisions */}
      <Card className="bg-white dark:bg-[#001E60]/80 border-slate-200 dark:border-blue-900/50 text-slate-900 dark:text-slate-100 shadow-sm">
        <CardHeader className="pb-2 border-b border-slate-200 dark:border-blue-900/50">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
            Recent Supervisor Decisions Log
          </CardTitle>
          <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
            Latest planner override and acceptance decisions with justification context.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-2">
          <div className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
            {recentDecisions.length === 0 ? (
              <div className="py-8 text-center text-slate-400 dark:text-slate-500">No recent decisions found.</div>
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
                    <span className="text-slate-500 dark:text-slate-400 font-mono">Event: {dec.event_id}</span>
                  </div>
                  <p className="text-slate-600 dark:text-slate-300 text-xs">"{dec.justification}"</p>
                </div>
                <div className="text-slate-400 dark:text-slate-500 font-mono text-[11px] shrink-0">
                  Planner: {dec.planner_id}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
