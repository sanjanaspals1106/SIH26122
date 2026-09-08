import React, { useEffect, useState } from 'react';
import { activitiesApi, auditApi, ScheduleActivity, AuditLogEntry } from '@/api';
import {
  Clock,
  Search,
  ShieldCheck,
  Activity,
  User,
  ArrowRight,
  CalendarDays,
  AlertCircle,
  GitCommit,
  Hash,
  FileText,
  CheckCircle2,
  XCircle,
  RotateCcw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { cn } from '@/lib/utils';

function StatusBadge({ status }: { status: string }) {
  const s = status?.toUpperCase() || '';
  if (s === 'APPROVED' || s === 'COMMITTED')
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30 uppercase">
        <CheckCircle2 className="w-3 h-3" /> {status}
      </span>
    );
  if (s === 'REJECTED' || s === 'CONFLICT')
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-500/30 uppercase">
        <XCircle className="w-3 h-3" /> {status}
      </span>
    );
  if (s === 'PENDING' || s === 'UNDER_REVIEW')
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-500/30 uppercase">
        <RotateCcw className="w-3 h-3" /> {status}
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-500/30 uppercase">
      {status}
    </span>
  );
}

export default function ActivityHistory() {
  const [selectedActivityId, setSelectedActivityId] = useState<string>('ACT-202');
  const [searchInput, setSearchInput] = useState<string>('ACT-202');

  const [activity, setActivity] = useState<ScheduleActivity | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadActivityData = async (actId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const [actHist, logs] = await Promise.all([
        activitiesApi.getHistory(actId),
        auditApi.getLogs(),
      ]);
      setActivity(actHist.activity);
      setHistory(actHist.history);
      setAuditLogs(logs);
    } catch (e: any) {
      setError('Failed to fetch activity history: ' + e.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadActivityData(selectedActivityId);
  }, [selectedActivityId]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      setSelectedActivityId(searchInput.trim());
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Activity Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-blue-900/50 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-[#FC4C02]/10 border border-[#FC4C02]/20">
              <Clock className="w-5 h-5 text-[#FC4C02]" />
            </div>
            Activity History & Change Timeline
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-xs mt-1">
            Complete lifecycle timeline for specific scheduled Primavera activities with cryptographic audit trail.
          </p>
        </div>

        <form onSubmit={handleSearchSubmit} className="flex gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Activity ID (e.g. ACT-202)..."
              className="pl-9 bg-white dark:bg-[#001438] border-slate-300 dark:border-blue-800 text-slate-900 dark:text-slate-100 text-xs h-9 w-64 font-mono focus:border-[#FC4C02] dark:focus:border-[#FC4C02]"
            />
          </div>
          <Button type="submit" size="sm" className="bg-[#FC4C02] hover:bg-[#e04302] text-white text-xs h-9">
            Lookup
          </Button>
        </form>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <div className="h-28 bg-slate-100 dark:bg-[#001E60]/50 rounded-2xl animate-pulse" />
          <div className="h-64 bg-slate-100 dark:bg-[#001E60]/50 rounded-2xl animate-pulse" />
          <div className="h-48 bg-slate-100 dark:bg-[#001E60]/50 rounded-2xl animate-pulse" />
        </div>
      ) : error ? (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs flex items-start gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          {error}
        </div>
      ) : (
        <>
          {/* Activity Header Summary */}
          {activity && (
            <Card className="bg-white dark:bg-[#001E60]/80 border-slate-200 dark:border-blue-900/50 shadow-sm">
              <CardContent className="p-4 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="bg-[#001E60] dark:bg-[#FC4C02] text-white font-mono text-xs px-2.5 py-0.5 rounded-md font-bold">
                      {activity.activity_id}
                    </span>
                    <span className="text-xs bg-slate-100 dark:bg-blue-900/80 text-slate-700 dark:text-blue-200 border border-slate-200 dark:border-blue-700/50 px-2 py-0.5 rounded-full font-mono uppercase">
                      {activity.discipline}
                    </span>
                    <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">WBS: {activity.wbs_code}</span>
                  </div>
                  <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">{activity.activity_name}</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Location: <strong className="text-slate-700 dark:text-slate-200">{activity.location}</strong> · Planned Window:{' '}
                    <span className="font-mono text-[#FC4C02]">{activity.planned_start}</span> to{' '}
                    <span className="font-mono text-[#FC4C02]">{activity.planned_finish}</span>
                  </p>
                </div>

                <div className="flex gap-6 border-t sm:border-t-0 sm:border-l border-slate-200 dark:border-blue-900/50 pt-3 sm:pt-0 sm:pl-6 text-xs font-mono">
                  <div>
                    <span className="text-[10px] uppercase text-slate-400 dark:text-slate-500 block mb-0.5">Baseline Pct</span>
                    <span className="text-slate-900 dark:text-slate-100 font-bold text-lg">{activity.baseline_pct_complete}<span className="text-sm text-slate-400">%</span></span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase text-slate-400 dark:text-slate-500 block mb-0.5">Planned Qty</span>
                    <span className="text-slate-900 dark:text-slate-100 font-bold text-lg">
                      {activity.planned_quantity || 'N/A'} <span className="text-sm text-slate-400">{activity.uom || ''}</span>
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Chronological Timeline */}
          <Card className="bg-white dark:bg-[#001E60]/80 border-slate-200 dark:border-blue-900/50 shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-200 dark:border-blue-900/50">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <CalendarDays className="w-4 h-4 text-[#FC4C02]" />
                Chronological Claim & Decision History
              </CardTitle>
              <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
                All field claims and supervisor actions in sequence for this activity.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              {history.length === 0 ? (
                <div className="text-center py-10 text-slate-400 dark:text-slate-500 text-sm">
                  <GitCommit className="w-8 h-8 mx-auto mb-3 opacity-30" />
                  No history records found for this activity.
                </div>
              ) : (
                <div className="relative pl-6 border-l-2 border-slate-200 dark:border-blue-900/50 space-y-6">
                  {history.map((item, idx) => (
                    <div key={idx} className="relative group">
                      {/* Node Dot */}
                      <div className={cn(
                        'absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full border-4 border-white dark:border-[#001E60] shadow transition-transform group-hover:scale-125',
                        item.supervisor_action ? 'bg-emerald-500' : 'bg-[#FC4C02]'
                      )} />

                      <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-700 hover:border-[#FC4C02]/40 transition-colors space-y-2.5 text-xs">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="inline-flex items-center gap-1.5 font-mono font-bold text-slate-900 dark:text-slate-200">
                              <User className="w-3 h-3 text-slate-400" />
                              {item.actor}
                            </span>
                            <span className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-[10px] font-mono px-2 py-0.5 rounded-md">
                              {item.input_channel}
                            </span>
                            <StatusBadge status={item.status} />
                          </div>
                          <span className="text-[11px] font-mono text-slate-400 dark:text-slate-500 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {new Date(item.timestamp).toLocaleString()}
                          </span>
                        </div>

                        <p className="text-slate-700 dark:text-slate-200 font-medium leading-relaxed bg-slate-100 dark:bg-slate-900/60 rounded-lg p-3 border border-slate-200 dark:border-slate-700 italic">
                          "{item.raw_claim_text}"
                        </p>

                        <div className="flex items-center gap-4 text-slate-500 dark:text-slate-400 text-[11px] flex-wrap">
                          {item.claimed_pct !== null && (
                            <div className="flex items-center gap-1">
                              Claimed:
                              <span className="font-mono text-slate-900 dark:text-slate-100 font-bold ml-1">{item.claimed_pct}%</span>
                            </div>
                          )}
                          {item.supervisor_action && (
                            <div className="flex items-center gap-1">
                              Supervisor:
                              <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold ml-1">{item.supervisor_action}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Cryptographic Audit Trail */}
          <Card className="bg-white dark:bg-[#001E60]/80 border-slate-200 dark:border-blue-900/50 shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-200 dark:border-blue-900/50">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <span className="text-slate-900 dark:text-slate-200">Immutable Cryptographic Audit Trail</span>
                <span className="text-[10px] bg-emerald-100 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20 px-2 py-0.5 rounded-full font-mono">SHA-256 Hash Chain</span>
              </CardTitle>
              <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
                Tamper-evident system log guaranteeing non-repudiation of field claims and planner decisions.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4 space-y-3 font-mono text-[11px]">
              {auditLogs.length === 0 ? (
                <div className="text-center py-8 text-slate-400 dark:text-slate-500">No audit log entries found.</div>
              ) : auditLogs.map((log) => (
                <div key={log.log_id} className="p-3 bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-700 rounded-xl space-y-2 hover:border-emerald-300 dark:hover:border-emerald-700/50 transition-colors">
                  <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 flex-wrap gap-1">
                    <span className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                      <Hash className="w-3 h-3 text-emerald-500" />
                      LOG {log.log_id} · {log.action}
                    </span>
                    <span className="text-slate-400 dark:text-slate-500 text-[10px]">
                      {new Date(log.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[10px]">
                    <div className="truncate p-2 bg-slate-100 dark:bg-slate-900/60 rounded-lg">
                      <span className="text-slate-400 dark:text-slate-500 block mb-0.5">Prev Hash:</span>
                      <span className="text-slate-500 dark:text-slate-500">{log.previous_hash}</span>
                    </div>
                    <div className="truncate p-2 bg-slate-100 dark:bg-slate-900/60 rounded-lg">
                      <span className="text-slate-400 dark:text-slate-500 block mb-0.5">Curr Hash:</span>
                      <span className="text-[#FC4C02] dark:text-indigo-400">{log.current_hash}</span>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
