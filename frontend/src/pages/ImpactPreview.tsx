import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Activity,
  ArrowRight,
  GitBranch,
  Info,
  AlertTriangle,
  Calendar,
  TrendingUp,
  Loader2,
  ChevronRight,
} from 'lucide-react';
import { schedulesApi, ImpactPreviewResult } from '@/api';
import { cn } from '@/lib/utils';

export default function ImpactPreview() {
  const [activityId, setActivityId] = useState('ACT-201');
  const [delayDays, setDelayDays] = useState(5);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState<ImpactPreviewResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSimulate = async () => {
    setIsSimulating(true);
    setError(null);
    try {
      const res = await schedulesApi.getImpactPreview(activityId, delayDays);
      setSimulationResult(res);
    } catch (e: any) {
      setError('Failed to compute impact preview: ' + e.message);
    } finally {
      setIsSimulating(false);
    }
  };

  const slippageColor = (days: number) => {
    if (days <= 2) return 'text-amber-600 dark:text-amber-400';
    if (days <= 7) return 'text-orange-600 dark:text-orange-400';
    return 'text-rose-600 dark:text-rose-400';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-slate-200 dark:border-blue-900/50 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-violet-100 dark:bg-violet-500/10 border border-violet-200 dark:border-violet-500/20">
              <GitBranch className="w-5 h-5 text-violet-600 dark:text-violet-400" />
            </div>
            Precedence Ripple Impact Preview
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-xs mt-1">
            Simulate downstream successor start/finish date shifts before committing actual delays.
          </p>
        </div>
      </div>

      {/* Scope Disclaimer */}
      <div className="p-3.5 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700/50 text-blue-700 dark:text-blue-300 text-xs flex items-center gap-2.5">
        <Info className="w-4 h-4 text-blue-500 dark:text-blue-400 shrink-0" />
        <span>
          <strong>Preview Scope:</strong> Immediate Finish-to-Start (FS) successors only · Not a full CPM recalculation · For planning reference only
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Form Inputs */}
        <Card className="bg-white dark:bg-[#001E60]/80 border-slate-200 dark:border-blue-900/50 shadow-sm lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-900 dark:text-slate-200">
              <Activity className="w-4 h-4 text-violet-600 dark:text-violet-400" />
              Simulation Inputs
            </CardTitle>
            <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
              Enter a Primavera Activity ID and hypothetical delay duration to preview ripple impact.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5 text-xs">
            {error && (
              <div className="p-3 bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300 rounded-xl flex items-start gap-2">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                {error}
              </div>
            )}

            <div className="space-y-1.5">
              <Label className="text-xs text-slate-700 dark:text-slate-300 font-semibold">Primavera Activity ID</Label>
              <Input
                value={activityId}
                onChange={(e) => setActivityId(e.target.value)}
                placeholder="e.g. ACT-201"
                className="bg-slate-50 dark:bg-[#001438] border-slate-300 dark:border-blue-800 font-mono text-slate-900 dark:text-slate-200 focus:border-violet-500 dark:focus:border-violet-500"
              />
              <p className="text-[11px] text-slate-400 dark:text-slate-500">Enter the Primavera P6 activity identifier</p>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-slate-700 dark:text-slate-300 font-semibold">Hypothetical Delay (Days)</Label>
              <div className="relative">
                <Input
                  type="number"
                  min={1}
                  max={90}
                  value={delayDays}
                  onChange={(e) => setDelayDays(Number(e.target.value))}
                  className="bg-slate-50 dark:bg-[#001438] border-slate-300 dark:border-blue-800 text-slate-900 dark:text-slate-200 font-mono focus:border-violet-500 dark:focus:border-violet-500 pr-16"
                />
                <span className="absolute right-3 top-2.5 text-slate-400 dark:text-slate-500 text-xs font-mono">days</span>
              </div>
              <p className="text-[11px] text-slate-400 dark:text-slate-500">Range: 1–90 days</p>
            </div>

            {/* Visual delay severity indicator */}
            <div className="space-y-2">
              <div className="flex justify-between text-[10px] text-slate-400 dark:text-slate-500">
                <span>Low Impact</span>
                <span>High Impact</span>
              </div>
              <div className="h-2 rounded-full bg-gradient-to-r from-amber-400 via-orange-500 to-rose-600 relative">
                <div
                  className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-white border-2 border-slate-700 shadow transition-all"
                  style={{ left: `${Math.min(((delayDays - 1) / 89) * 100, 100)}%` }}
                />
              </div>
            </div>

            <Button
              onClick={handleSimulate}
              disabled={isSimulating || !activityId}
              className="w-full bg-violet-600 hover:bg-violet-500 dark:bg-violet-600 dark:hover:bg-violet-500 text-white font-medium shadow-md shadow-violet-600/20 h-10 gap-2"
            >
              {isSimulating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Computing Ripple Shift...
                </>
              ) : (
                <>
                  <TrendingUp className="w-4 h-4" />
                  Run Successor Impact Analysis
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Right Column: Results */}
        <div className="lg:col-span-2 space-y-6">
          {!simulationResult ? (
            <Card className="bg-white dark:bg-[#001E60]/80 border-slate-200 dark:border-blue-900/50 shadow-sm h-full min-h-[280px] flex items-center justify-center text-center p-8">
              <div className="space-y-3 max-w-sm">
                <div className="w-14 h-14 rounded-2xl bg-violet-100 dark:bg-violet-500/10 border border-violet-200 dark:border-violet-500/20 flex items-center justify-center mx-auto">
                  <GitBranch className="w-7 h-7 text-violet-500 dark:text-violet-400" />
                </div>
                <h3 className="text-slate-700 dark:text-slate-300 font-semibold text-sm">No Simulation Run Yet</h3>
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  Enter an Activity ID and delay duration on the left, then click{' '}
                  <strong className="text-violet-600 dark:text-violet-400">Run Successor Impact Analysis</strong> to preview immediate FS successor schedule shifts.
                </p>
              </div>
            </Card>
          ) : (
            <div className="space-y-5 animate-in fade-in duration-300">
              {/* Summary Banner */}
              <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-300 dark:border-amber-500/40 flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-bold text-amber-800 dark:text-amber-300">
                    Delay of +{simulationResult.delay_days} days on{' '}
                    <span className="font-mono">{simulationResult.activity_id}</span> will ripple to{' '}
                    {simulationResult.successors.length} immediate successor{simulationResult.successors.length !== 1 ? 's' : ''}.
                  </p>
                  <p className="text-xs text-amber-700 dark:text-amber-400/80 mt-0.5">
                    Commit this delay only after reviewing all shifted successor windows below.
                  </p>
                </div>
              </div>

              {/* Ripple Graph Card */}
              <Card className="bg-white dark:bg-[#001E60]/80 border-slate-200 dark:border-blue-900/50 shadow-sm">
                <CardHeader className="pb-3 border-b border-slate-200 dark:border-blue-900/50">
                  <CardTitle className="text-sm font-semibold flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <GitBranch className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                      Finish-to-Start Precedence Ripple Graph
                    </span>
                    <span className="text-[10px] bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-500/30 px-2 py-0.5 rounded-full font-mono font-bold">
                      +{simulationResult.delay_days}d shift
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-5">
                  {/* Visual Flow Layout */}
                  <div className="flex flex-col sm:flex-row items-start gap-4">
                    {/* Origin Node */}
                    <div className="relative p-4 rounded-xl bg-amber-50 dark:bg-amber-500/10 border-2 border-amber-400/60 dark:border-amber-500/50 text-center w-full sm:w-48 shrink-0">
                      <div className="text-[10px] font-bold text-amber-600 dark:text-amber-400 uppercase tracking-wider mb-1.5 flex items-center justify-center gap-1">
                        <Calendar className="w-3 h-3" /> Impact Origin
                      </div>
                      <div className="font-mono font-bold text-slate-900 dark:text-slate-100 text-base">{simulationResult.activity_id}</div>
                      <span className="absolute -top-3 -right-3 bg-rose-600 text-white text-xs px-2 py-0.5 rounded-full font-bold shadow-lg">
                        +{simulationResult.delay_days}d
                      </span>
                    </div>

                    {/* Arrow */}
                    <div className="hidden sm:flex flex-col items-center self-center w-12 shrink-0">
                      <div className="flex items-center gap-1 text-slate-400 dark:text-slate-500">
                        <div className="h-px w-4 bg-slate-300 dark:bg-slate-600" />
                        <ArrowRight className="w-4 h-4" />
                      </div>
                      <span className="text-[9px] font-mono text-slate-400 dark:text-slate-500 mt-1">FS</span>
                    </div>

                    {/* Successor Nodes */}
                    <div className="flex-1 space-y-3 w-full">
                      {simulationResult.successors.map((succ, idx) => (
                        <div
                          key={idx}
                          className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-700 hover:border-violet-300 dark:hover:border-violet-700/60 transition-colors space-y-2.5 text-xs"
                        >
                          <div className="flex items-center justify-between flex-wrap gap-2">
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-bold text-violet-700 dark:text-violet-300 bg-violet-100 dark:bg-violet-500/10 px-2 py-0.5 rounded-md border border-violet-200 dark:border-violet-500/20">
                                {succ.successor_activity_id}
                              </span>
                              <span className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded-full font-mono">
                                {succ.relationship_type}
                              </span>
                            </div>
                            <ChevronRight className="w-4 h-4 text-slate-400 dark:text-slate-500 hidden sm:block" />
                          </div>

                          <div className="font-medium text-slate-800 dark:text-slate-200">{succ.activity_name}</div>

                          <div className="grid grid-cols-2 gap-3 text-[11px] font-mono pt-2 border-t border-slate-200 dark:border-slate-700">
                            <div className="space-y-0.5">
                              <span className="text-slate-400 dark:text-slate-500 text-[10px] uppercase tracking-wide block">Original Start</span>
                              <span className="text-slate-700 dark:text-slate-300 font-semibold">{succ.original_start}</span>
                            </div>
                            <div className="space-y-0.5">
                              <span className="text-slate-400 dark:text-slate-500 text-[10px] uppercase tracking-wide block">Shifted Start</span>
                              <span className={cn('font-bold', slippageColor(simulationResult.delay_days))}>{succ.shifted_start}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
