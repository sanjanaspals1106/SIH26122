import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { activitiesApi, auditApi, ScheduleActivity, AuditLogEntry } from '@/api';
import {
  Clock,
  Search,
  ShieldCheck,
  User,
  CalendarDays,
  GitCommit,
  Hash,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
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
  const [history, setHistory] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState<boolean>(false);

  // Pagination states
  const [timelinePage, setTimelinePage] = useState<number>(1);
  const [auditLogsPage, setAuditLogsPage] = useState<number>(1);

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
      setTimelinePage(1);
      setAuditLogsPage(1);
    } catch (e: any) {
      setError(t('history.failedToFetch', { message: e.message }));
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

  const totalTimelinePages = Math.max(1, Math.ceil(history.length / PAGE_SIZE));
  const paginatedHistory = history.slice((timelinePage - 1) * PAGE_SIZE, timelinePage * PAGE_SIZE);

  const totalAuditPages = Math.max(1, Math.ceil(auditLogs.length / PAGE_SIZE));
  const paginatedAuditLogs = auditLogs.slice((auditLogsPage - 1) * PAGE_SIZE, auditLogsPage * PAGE_SIZE);

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
              className="pl-9 font-mono text-xs h-9 w-64 focus-visible:ring-primary"
            />
          </div>
          <Button type="submit" size="sm" className="h-9">
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
                    <span className="text-xs text-muted-foreground font-mono">{t('history.wbs')}: {activity.wbs_code}</span>
                  </div>
                  <h2 className="text-lg font-bold text-foreground">{activity.activity_name}</h2>
                  <p className="text-xs text-muted-foreground">
                    {t('history.location')}: <strong className="text-foreground">{activity.location}</strong> · {t('history.plannedWindow')}:{' '}
                    <span className="font-mono text-primary font-semibold">{activity.planned_start}</span> {t('history.to')}{' '}
                    <span className="font-mono text-primary font-semibold">{activity.planned_finish}</span>
                  </p>
                </div>

                <div className="flex gap-6 border-t sm:border-t-0 sm:border-l border-border pt-3 sm:pt-0 sm:pl-6 text-xs font-mono">
                  <div>
                    <span className="text-[10px] uppercase text-muted-foreground block mb-0.5">{t('history.baselinePct')}</span>
                    <span className="text-foreground font-bold text-lg">{activity.baseline_pct_complete}<span className="text-sm text-muted-foreground">%</span></span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase text-muted-foreground block mb-0.5">{t('history.plannedQty')}</span>
                    <span className="text-foreground font-bold text-lg">
                      {activity.planned_quantity || t('review.notAvailable')} <span className="text-sm text-muted-foreground">{activity.uom || ''}</span>
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Chronological Timeline */}
          <Card>
            <CardHeader className="pb-3 border-b border-border">
              <CardTitle className="text-sm font-semibold flex items-center gap-2 text-foreground">
                <CalendarDays className="w-4 h-4 text-primary" />
                {t('history.timelineTitle')}
              </CardTitle>
              <CardDescription className="text-muted-foreground text-xs">
                {t('history.timelineDesc')}
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              {history.length === 0 ? (
                <EmptyState
                  icon={GitCommit}
                  title={t('history.noHistory')}
                  className="py-10"
                />
              ) : (
                <>
                  <div className="relative pl-6 border-l-2 border-border space-y-6">
                    {paginatedHistory.map((item, idx) => (
                      <div key={idx} className="relative group">
                        {/* Node Dot */}
                        <div className={cn(
                          'absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full border-4 border-card shadow-xs transition-transform group-hover:scale-125',
                          item.supervisor_action ? 'bg-status-approved' : 'bg-primary'
                        )} />

                        <div className="p-4 rounded-xl bg-card border border-border hover:border-primary/40 transition-colors space-y-2.5 text-xs shadow-xs">
                          <div className="flex items-center justify-between flex-wrap gap-2">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="inline-flex items-center gap-1.5 font-mono font-bold text-foreground">
                                <User className="w-3 h-3 text-muted-foreground" />
                                {item.actor}
                              </span>
                              <ProvenanceBadge channel={item.input_channel} size="sm" />
                              <StatusBadge status={item.status} size="sm" />
                            </div>
                            <span className="text-[11px] font-mono text-muted-foreground flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {new Date(item.timestamp).toLocaleString()}
                            </span>
                          </div>

                          <p className="text-foreground font-medium leading-relaxed bg-card-subtle rounded-lg p-3 border border-border italic">
                            "{item.raw_claim_text}"
                          </p>

                          <div className="flex items-center gap-4 text-muted-foreground text-[11px] flex-wrap">
                            {item.claimed_pct !== null && (
                              <div className="flex items-center gap-1">
                                {t('history.claimed')}:
                                <span className="font-mono text-primary font-bold ml-1">{item.claimed_pct}%</span>
                              </div>
                            )}
                            {item.supervisor_action && (
                              <div className="flex items-center gap-1">
                                {t('history.supervisor')}:
                                <span className="font-mono text-status-approved font-bold ml-1">{item.supervisor_action}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Timeline Pagination Controls */}
                  {history.length > PAGE_SIZE && (
                    <div className="flex items-center justify-between border-t border-border pt-4 mt-6 text-xs text-muted-foreground">
                      <span>
                        {t('history.timelineItemsCount', {
                          shown: `${(timelinePage - 1) * PAGE_SIZE + 1}–${Math.min(timelinePage * PAGE_SIZE, history.length)}`,
                          total: history.length,
                        })}
                      </span>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={timelinePage === 1}
                          onClick={() => setTimelinePage((p) => Math.max(1, p - 1))}
                          className="h-8 text-xs gap-1"
                        >
                          <ChevronLeft className="w-3.5 h-3.5" />
                          {t('common.previous')}
                        </Button>
                        <span className="font-mono px-2 font-medium text-foreground">
                          {t('common.pageOf', { current: timelinePage, total: totalTimelinePages })}
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={timelinePage === totalTimelinePages}
                          onClick={() => setTimelinePage((p) => Math.min(totalTimelinePages, p + 1))}
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
          <Card>
            <CardHeader className="pb-3 border-b border-border">
              <CardTitle className="text-sm font-semibold flex items-center gap-2 text-foreground">
                <ShieldCheck className="w-4 h-4 text-status-approved" />
                <span>{t('history.auditTrailTitle')}</span>
                <span className="text-[10px] bg-status-approved/10 text-status-approved border border-status-approved/20 px-2 py-0.5 rounded-full font-mono font-semibold">{t('history.hashChain')}</span>
              </CardTitle>
              <CardDescription className="text-muted-foreground text-xs">
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
                    <div key={log.log_id} className="p-3 bg-card border border-border rounded-xl space-y-2 hover:border-status-approved/50 transition-colors shadow-xs">
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
                          <span className="text-muted-foreground block mb-0.5">{t('history.prevHash')}</span>
                          <span className="text-muted-foreground">{log.previous_hash}</span>
                        </div>
                        <div className="truncate p-2 bg-card-subtle rounded-lg border border-border">
                          <span className="text-muted-foreground block mb-0.5">{t('history.currHash')}</span>
                          <span className="text-primary font-bold">{log.current_hash}</span>
                        </div>
                      </div>
                    </div>
                  ))}

                  {/* Audit Logs Pagination Controls */}
                  {auditLogs.length > PAGE_SIZE && (
                    <div className="flex items-center justify-between border-t border-border pt-4 mt-4 text-xs text-muted-foreground">
                      <span>
                        {t('history.auditLogsCount', {
                          shown: `${(auditLogsPage - 1) * PAGE_SIZE + 1}–${Math.min(auditLogsPage * PAGE_SIZE, auditLogs.length)}`,
                          total: auditLogs.length,
                        })}
                      </span>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={auditLogsPage === 1}
                          onClick={() => setAuditLogsPage((p) => Math.max(1, p - 1))}
                          className="h-8 text-xs gap-1"
                        >
                          <ChevronLeft className="w-3.5 h-3.5" />
                          {t('common.previous')}
                        </Button>
                        <span className="font-mono px-2 font-medium text-foreground">
                          {t('common.pageOf', { current: auditLogsPage, total: totalAuditPages })}
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={auditLogsPage === totalAuditPages}
                          onClick={() => setAuditLogsPage((p) => Math.min(totalAuditPages, p + 1))}
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
