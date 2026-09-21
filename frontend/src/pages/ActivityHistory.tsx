import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  activitiesApi,
  auditApi,
  ScheduleActivity,
  AuditLogEntry,
  ActivityTimelineItem,
} from '@/api';
import {
  Clock,
  Search,
  ShieldCheck,
  User,
  CalendarDays,
  GitCommit,
  Hash,
  FileText,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Link,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { StatusBadge } from '@/components/StatusBadge';
import { ProvenanceBadge } from '@/components/ProvenanceBadge';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorState } from '@/components/ui/error-state';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

const PAGE_SIZE = 5;

export default function ActivityHistory() {
  const { t } = useTranslation();

  const [selectedActivityId, setSelectedActivityId] = useState<string>('');
  const [searchInput, setSearchInput] = useState<string>('');

  const [activity, setActivity] = useState<ScheduleActivity | null>(null);
  const [timeline, setTimeline] = useState<ActivityTimelineItem[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState<boolean>(false);

  const [expandedEvidence, setExpandedEvidence] = useState<
    Record<string, boolean>
  >({});

  const [timelinePage, setTimelinePage] = useState<number>(1);
  const [auditLogsPage, setAuditLogsPage] = useState<number>(1);

  const toggleEvidence = (id: string) => {
    setExpandedEvidence((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const loadActivityData = async (actId: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const [actHist, logs] = await Promise.all([
        activitiesApi.getHistory(actId),
        auditApi.getLogs(),
      ]);

      setActivity(actHist.activity);
      setTimeline(actHist.timeline || []);
      setHistory(actHist.history || []);
      setAuditLogs(logs);

      setTimelinePage(1);
      setAuditLogsPage(1);
    } catch (e: any) {
      setError(
        t('history.failedToFetch', {
          message: e.message,
        })
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!selectedActivityId) return;

    setHasSearched(true);
    loadActivityData(selectedActivityId);
  }, [selectedActivityId]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (searchInput.trim()) {
      setSelectedActivityId(searchInput.trim());
    }
  };

  const hasSubstantiatedTimeline = timeline.length > 0;

  const totalTimelinePages = Math.max(
    1,
    Math.ceil(history.length / PAGE_SIZE)
  );

  const paginatedHistory = history.slice(
    (timelinePage - 1) * PAGE_SIZE,
    timelinePage * PAGE_SIZE
  );

  const totalAuditPages = Math.max(
    1,
    Math.ceil(auditLogs.length / PAGE_SIZE)
  );

  const paginatedAuditLogs = auditLogs.slice(
    (auditLogsPage - 1) * PAGE_SIZE,
    auditLogsPage * PAGE_SIZE
  );

  return (
    <div className="space-y-6">
      {/* Header & Activity Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-300 dark:border-[#214766]/60 pb-4">
        <div>
          <h1 className="text-2xl font-extrabold text-[#071A2D] dark:text-[#F5F7FA] tracking-tight flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-primary/10 border border-primary/20">
              <Clock className="w-5 h-5 text-primary" />
            </div>

            {t('history.title')}
          </h1>

          <p className="text-[#334155] dark:text-[#CBD5E1] text-xs font-semibold mt-1">
            {t('history.subtitle')}
          </p>
        </div>

        <form onSubmit={handleSearchSubmit} className="flex gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-muted-foreground" />

            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder={t('history.searchPlaceholder')}
              className="pl-9 bg-white dark:bg-[#001438] border-slate-300 dark:border-blue-800 text-slate-900 dark:text-slate-100 text-xs h-9 w-64 font-mono focus:border-[#FC4C02]"
            />
          </div>

          <Button
            type="submit"
            size="sm"
            className="bg-[#FC4C02] hover:bg-[#e04302] text-white text-xs h-9 font-semibold"
          >
            {t('history.lookup')}
          </Button>
        </form>
      </div>

      {!hasSearched ? (
        <EmptyState
          icon={Search}
          title={t('history.searchPlaceholder')}
          description={t('history.emptyPrompt')}
          className="py-16"
        />
      ) : isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-28 rounded-xl" />
          <Skeleton className="h-64 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
        </div>
      ) : error ? (
        <ErrorState
          message={error}
          onRetry={() => {
            if (selectedActivityId) {
              loadActivityData(selectedActivityId);
            }
          }}
        />
      ) : (
        <>
          {/* Activity Header Summary */}
          {activity && (
            <Card>
              <CardContent className="p-4 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="bg-primary text-primary-foreground font-mono text-xs px-2.5 py-0.5 rounded-md font-bold">
                      {activity.activity_id}
                    </span>

                    <span className="text-xs bg-secondary text-secondary-foreground border border-border px-2 py-0.5 rounded-full font-mono uppercase font-semibold">
                      {activity.discipline}
                    </span>

                    <span className="text-xs text-muted-foreground font-mono">
                      {t('history.wbs')}: {activity.wbs_code}
                    </span>
                  </div>

                  <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                    {activity.activity_name}
                  </h2>

                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {t('history.location')}:{' '}
                    <strong className="text-slate-700 dark:text-slate-200">
                      {activity.location}
                    </strong>{' '}
                    · {t('history.plannedWindow')}:{' '}
                    <span className="font-mono text-[#FC4C02] font-semibold">
                      {activity.planned_start}
                    </span>{' '}
                    {t('history.to')}{' '}
                    <span className="font-mono text-[#FC4C02] font-semibold">
                      {activity.planned_finish}
                    </span>
                  </p>
                </div>

                <div className="flex gap-6 border-t sm:border-t-0 sm:border-l border-border pt-3 sm:pt-0 sm:pl-6 text-xs font-mono">
                  <div>
                    <span className="text-[10px] uppercase text-muted-foreground block mb-0.5">
                      {t('history.baselinePct')}
                    </span>

                    <span className="text-foreground font-bold text-lg">
                      {activity.baseline_pct_complete}
                      <span className="text-sm text-muted-foreground">%</span>
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase text-muted-foreground block mb-0.5">
                      {t('history.plannedQty')}
                    </span>

                    <span className="text-foreground font-bold text-lg">
                      {activity.planned_quantity ||
                        t('review.notAvailable')}{' '}
                      <span className="text-sm text-muted-foreground">
                        {activity.uom || ''}
                      </span>
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Substantiated Vertical Lifecycle Timeline */}
          <Card className="bg-white dark:bg-[#001E60]/80 border-slate-200 dark:border-blue-900/50 shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-200 dark:border-blue-900/50">
              <CardTitle className="text-sm font-semibold flex items-center justify-between">
                <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
                  <CalendarDays className="w-4 h-4 text-[#FC4C02]" />
                  Substantiated Lifecycle Audit Timeline
                </span>

                <span className="text-[10px] font-mono text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-full">
                  Genuine DB Events Only
                </span>
              </CardTitle>

              <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
                Chronological execution claims, supervisor authority decisions,
                and approved schedule actuals.
              </CardDescription>
            </CardHeader>

            <CardContent className="pt-6">
              {!hasSubstantiatedTimeline && history.length === 0 ? (
                <div className="text-center py-10 text-slate-400 dark:text-slate-500 text-sm">
                  <GitCommit className="w-8 h-8 mx-auto mb-3 opacity-30" />
                  {t('history.noHistory')}
                </div>
              ) : (
                <>
                  <div className="relative pl-6 border-l-2 border-slate-200 dark:border-blue-900/50 space-y-6">
                    {hasSubstantiatedTimeline
                      ? timeline.map((item, idx) => {
                          const isEvent = item.type === 'execution_event';
                          const isDecision = item.type === 'planner_decision';
                          const isActual = item.type === 'approved_actual';

                          return (
                            <div key={idx} className="relative group">
                              <div
                                className={cn(
                                  'absolute -left-[31px] top-1.5 w-4 h-4 rounded-full border-4 border-white dark:border-[#001E60] shadow transition-transform group-hover:scale-125',
                                  isActual
                                    ? 'bg-purple-600'
                                    : isDecision
                                    ? item.action === 'APPROVE'
                                      ? 'bg-emerald-500'
                                      : item.action === 'REJECT'
                                      ? 'bg-rose-500'
                                      : 'bg-amber-500'
                                    : 'bg-blue-500'
                                )}
                              />

                              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 hover:border-[#FC4C02]/40 transition-colors space-y-2.5 text-xs">
                                <div className="flex items-center justify-between flex-wrap gap-2">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="inline-flex items-center gap-1.5 font-mono font-bold text-slate-900 dark:text-slate-200">
                                      {isEvent && (
                                        <>
                                          <FileText className="w-3.5 h-3.5 text-blue-500" />
                                          <span>
                                            Field Claim / Extraction (
                                            {item.event_id})
                                          </span>
                                        </>
                                      )}

                                      {isDecision && (
                                        <>
                                          <User className="w-3.5 h-3.5 text-emerald-500" />
                                          <span>
                                            Supervisor Decision (
                                            {item.decision_id
                                              ? item.decision_id.slice(0, 8)
                                              : 'DEC'}
                                            )
                                          </span>
                                        </>
                                      )}

                                      {isActual && (
                                        <>
                                          <CheckCircle2 className="w-3.5 h-3.5 text-purple-500" />
                                          <span>
                                            Approved Actual Committed (
                                            {item.actual_id
                                              ? item.actual_id.slice(0, 8)
                                              : 'ACTL'}
                                            )
                                          </span>
                                        </>
                                      )}
                                    </span>

                                    {isEvent && item.status && (
                                      <StatusBadge
                                        status={item.status}
                                        size="sm"
                                      />
                                    )}

                                    {isDecision && item.action && (
                                      <span
                                        className={cn(
                                          'px-2 py-0.5 rounded text-[10px] font-bold font-mono',
                                          item.action === 'APPROVE'
                                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300'
                                            : item.action === 'REJECT'
                                            ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300'
                                            : 'bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300'
                                        )}
                                      >
                                        ACTION: {item.action}
                                      </span>
                                    )}
                                  </div>

                                  <span className="text-[11px] font-mono text-slate-400 dark:text-slate-500 flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {item.timestamp
                                      ? new Date(
                                          item.timestamp
                                        ).toLocaleString()
                                      : 'Timestamp TBD'}
                                  </span>
                                </div>

                                {isEvent && item.raw_claim_text && (
                                  <p className="text-slate-700 dark:text-slate-200 font-medium leading-relaxed bg-slate-100 dark:bg-slate-900/60 rounded-lg p-3 border border-slate-200 dark:border-slate-800 italic">
                                    "{item.raw_claim_text}"
                                  </p>
                                )}

                                {isDecision && (
                                  <div className="p-3 bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/40 rounded-lg space-y-1">
                                    <div className="flex items-center justify-between text-[11px]">
                                      <span className="font-semibold text-emerald-900 dark:text-emerald-200">
                                        Supervisor Authority:{' '}
                                        {item.planner_id || 'Supervisor'}
                                      </span>

                                      <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                                        Approved:{' '}
                                        {item.approved_pct !== null
                                          ? `${item.approved_pct}%`
                                          : ''}{' '}
                                        {item.approved_qty
                                          ? `(${item.approved_qty} qty)`
                                          : ''}
                                      </span>
                                    </div>

                                    {item.justification && (
                                      <p className="text-slate-600 dark:text-slate-300 text-[11px] mt-1">
                                        <strong>Justification:</strong>{' '}
                                        {item.justification}
                                      </p>
                                    )}
                                  </div>
                                )}

                                {isActual && (
                                  <div className="p-3 bg-purple-50/60 dark:bg-purple-950/20 border border-purple-200 dark:border-purple-900/40 rounded-lg space-y-1 font-mono text-[11px]">
                                    <div className="flex justify-between items-center">
                                      <span className="text-slate-600 dark:text-slate-400">
                                        Actual Start:
                                      </span>

                                      <span className="font-bold text-slate-800 dark:text-slate-200">
                                        {item.actual_start || 'N/A'}
                                      </span>
                                    </div>

                                    <div className="flex justify-between items-center">
                                      <span className="text-slate-600 dark:text-slate-400">
                                        Actual Finish:
                                      </span>

                                      <span className="font-bold text-slate-800 dark:text-slate-200">
                                        {item.actual_finish || 'In Progress'}
                                      </span>
                                    </div>

                                    <div className="flex justify-between items-center pt-1 border-t border-purple-200/50 dark:border-purple-900/30">
                                      <span className="text-slate-600 dark:text-slate-400">
                                        Committed Actual %:
                                      </span>

                                      <span className="font-bold text-purple-700 dark:text-purple-300">
                                        {item.actual_pct_complete ?? 100}%
                                      </span>
                                    </div>
                                  </div>
                                )}

                                {isEvent &&
                                  item.source_references &&
                                  item.source_references.length > 0 && (
                                    <div className="pt-2">
                                      <button
                                        type="button"
                                        onClick={() =>
                                          toggleEvidence(
                                            item.event_id || String(idx)
                                          )
                                        }
                                        className="flex items-center gap-1 text-[11px] font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 cursor-pointer"
                                      >
                                        <Link className="w-3.5 h-3.5" />

                                        <span>
                                          {item.source_references.length}{' '}
                                          Traceable Source Reference
                                          {item.source_references.length !== 1
                                            ? 's'
                                            : ''}
                                        </span>

                                        {expandedEvidence[
                                          item.event_id || String(idx)
                                        ] ? (
                                          <ChevronUp className="w-3.5 h-3.5" />
                                        ) : (
                                          <ChevronDown className="w-3.5 h-3.5" />
                                        )}
                                      </button>

                                      {expandedEvidence[
                                        item.event_id || String(idx)
                                      ] && (
                                        <div className="mt-2 space-y-2 p-2.5 rounded-lg bg-blue-50/50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900/40 text-[11px]">
                                          {item.source_references.map(
                                            (ref, rIdx) => (
                                              <div
                                                key={rIdx}
                                                className="space-y-0.5 border-b border-blue-200/40 last:border-0 pb-1.5 last:pb-0"
                                              >
                                                <div className="flex items-center justify-between text-[10px] font-mono font-semibold text-slate-700 dark:text-slate-300">
                                                  <span>
                                                    {ref.file_name}
                                                  </span>

                                                  <span>
                                                    {ref.sheet_name
                                                      ? `${ref.sheet_name} · ${ref.row_cell_ref}`
                                                      : ref.row_cell_ref}
                                                  </span>
                                                </div>

                                                {ref.raw_snippet && (
                                                  <p className="text-slate-600 dark:text-slate-400 italic font-mono text-[10px]">
                                                    "{ref.raw_snippet}"
                                                  </p>
                                                )}
                                              </div>
                                            )
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  )}
                              </div>
                            </div>
                          );
                        })
                      : paginatedHistory.map((item, idx) => (
                          <div key={idx} className="relative group">
                            <div
                              className={cn(
                                'absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full border-4 border-white dark:border-[#001E60] shadow transition-transform group-hover:scale-125',
                                item.supervisor_action
                                  ? 'bg-emerald-500'
                                  : 'bg-[#FC4C02]'
                              )}
                            />

                            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-700 hover:border-[#FC4C02]/40 transition-colors space-y-2.5 text-xs">
                              <div className="flex items-center justify-between flex-wrap gap-2">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="inline-flex items-center gap-1.5 font-mono font-bold text-slate-900 dark:text-slate-200">
                                    <User className="w-3 h-3 text-slate-400" />
                                    {item.actor}
                                  </span>

                                  <ProvenanceBadge
                                    channel={item.input_channel}
                                    size="sm"
                                  />

                                  <StatusBadge
                                    status={item.status}
                                    size="sm"
                                  />
                                </div>

                                <span className="text-[11px] font-mono text-slate-400 dark:text-slate-500 flex items-center gap-1">
                                  <Clock className="w-3 h-3" />
                                  {item.timestamp
                                    ? new Date(
                                        item.timestamp
                                      ).toLocaleString()
                                    : ''}
                                </span>
                              </div>

                              <p className="text-slate-700 dark:text-slate-200 font-medium leading-relaxed bg-slate-100 dark:bg-slate-900/60 rounded-lg p-3 border border-slate-200 dark:border-slate-700 italic">
                                "{item.raw_claim_text}"
                              </p>
                            </div>
                          </div>
                        ))}
                  </div>

                  {/* Legacy History Pagination */}
                  {!hasSubstantiatedTimeline && history.length > PAGE_SIZE && (
                    <div className="flex items-center justify-between border-t border-border pt-4 mt-6 text-xs text-muted-foreground">
                      <span>
                        {t('history.timelineItemsCount', {
                          shown: `${(timelinePage - 1) * PAGE_SIZE + 1}–${Math.min(
                            timelinePage * PAGE_SIZE,
                            history.length
                          )}`,
                          total: history.length,
                        })}
                      </span>

                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={timelinePage === 1}
                          onClick={() =>
                            setTimelinePage((p) => Math.max(1, p - 1))
                          }
                          className="h-8 text-xs gap-1"
                        >
                          <ChevronLeft className="w-3.5 h-3.5" />
                          {t('common.previous')}
                        </Button>

                        <span className="font-mono px-2 font-medium text-foreground">
                          {t('common.pageOf', {
                            current: timelinePage,
                            total: totalTimelinePages,
                          })}
                        </span>

                        <Button
                          variant="outline"
                          size="sm"
                          disabled={timelinePage === totalTimelinePages}
                          onClick={() =>
                            setTimelinePage((p) =>
                              Math.min(totalTimelinePages, p + 1)
                            )
                          }
                          className="h-8 text-xs gap-1"
                        >
                          {t('common.next')}
                          <ChevronRight className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          {/* Cryptographic Audit Trail */}
          <Card className="bg-white dark:bg-[#001E60]/80 border-slate-200 dark:border-blue-900/50 shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-200 dark:border-blue-900/50">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-500" />
                <span>{t('history.auditTrailTitle')}</span>

                <span className="text-[10px] bg-status-approved/10 text-status-approved border border-status-approved/20 px-2 py-0.5 rounded-full font-mono font-semibold">
                  {t('history.hashChain')}
                </span>
              </CardTitle>

              <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
                {t('history.auditTrailDesc')}
              </CardDescription>
            </CardHeader>

            <CardContent className="pt-4 space-y-3 font-mono text-[11px]">
              {auditLogs.length === 0 ? (
                <EmptyState
                  icon={Hash}
                  title={t('history.noAuditLogs')}
                  className="py-8"
                />
              ) : (
                <>
                  {paginatedAuditLogs.map((log) => (
                    <div
                      key={log.log_id}
                      className="p-3 bg-card border border-border rounded-xl space-y-2 hover:border-status-approved/50 transition-colors shadow-xs"
                    >
                      <div className="flex items-center justify-between text-muted-foreground flex-wrap gap-1">
                        <span className="font-bold text-foreground flex items-center gap-1.5">
                          <Hash className="w-3 h-3 text-status-approved" />
                          {t('history.log')} {log.log_id} · {log.action}
                        </span>

                        <span className="text-muted-foreground text-[10px]">
                          {new Date(log.timestamp).toLocaleString()}
                        </span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[10px]">
                        <div className="truncate p-2 bg-card-subtle rounded-lg border border-border">
                          <span className="text-muted-foreground block mb-0.5">
                            {t('history.prevHash')}
                          </span>

                          <span className="text-muted-foreground">
                            {log.previous_hash}
                          </span>
                        </div>

                        <div className="truncate p-2 bg-card-subtle rounded-lg border border-border">
                          <span className="text-muted-foreground block mb-0.5">
                            {t('history.currHash')}
                          </span>

                          <span className="text-primary font-bold">
                            {log.current_hash}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}

                  {auditLogs.length > PAGE_SIZE && (
                    <div className="flex items-center justify-between border-t border-border pt-4 mt-4 text-xs text-muted-foreground">
                      <span>
                        {t('history.auditLogsCount', {
                          shown: `${(auditLogsPage - 1) * PAGE_SIZE + 1}–${Math.min(
                            auditLogsPage * PAGE_SIZE,
                            auditLogs.length
                          )}`,
                          total: auditLogs.length,
                        })}
                      </span>

                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={auditLogsPage === 1}
                          onClick={() =>
                            setAuditLogsPage((p) => Math.max(1, p - 1))
                          }
                          className="h-8 text-xs gap-1"
                        >
                          <ChevronLeft className="w-3.5 h-3.5" />
                          {t('common.previous')}
                        </Button>

                        <span className="font-mono px-2 font-medium text-foreground">
                          {t('common.pageOf', {
                            current: auditLogsPage,
                            total: totalAuditPages,
                          })}
                        </span>

                        <Button
                          variant="outline"
                          size="sm"
                          disabled={auditLogsPage === totalAuditPages}
                          onClick={() =>
                            setAuditLogsPage((p) =>
                              Math.min(totalAuditPages, p + 1)
                            )
                          }
                          className="h-8 text-xs gap-1"
                        >
                          {t('common.next')}
                          <ChevronRight className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}