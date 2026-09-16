import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { digestApi, ExecutionEvent, Discipline, ClaimStatus } from '@/api';
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  Clock,
  RefreshCw,
  ArrowRight,
  PauseCircle,
  XCircle,
  Sparkles,
  CheckSquare,
  ClipboardList,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

const DISCIPLINES: Discipline[] = [
  'CIVIL',
  'PIPING',
  'STATIC_ROTATING_EQUIPMENT',
  'ELECTRICAL',
  'INSTRUMENTATION',
  'HSE',
];

export default function DailyDigest() {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [currentMonth, setCurrentMonth] = useState<Date>(new Date());
  const [showCalendar, setShowCalendar] = useState<boolean>(false);
  const [hasResolvedInitialDate, setHasResolvedInitialDate] = useState<boolean>(false);

  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [isBulking, setIsBulking] = useState<boolean>(false);
  const [bulkResult, setBulkResult] = useState<{ approved: string[]; failed: string[] } | null>(null);

  const loadDigest = async (dateStr: string) => {
    setIsLoading(true);
    setError(null);
    setBulkResult(null);
    try {
      const data = await digestApi.getByDate(dateStr);
      setEvents(data);
    } catch (err: any) {
      setError(err.message || t('digest.failedToLoad'));
    } finally {
      setIsLoading(false);
    }
  };

  // On first load, jump to the event_date of the MOST RECENTLY CREATED
  // claim, instead of blindly defaulting to today's real calendar date.
  // Two things this deliberately does NOT use, because both fail here:
  //   - max(event_date): a claim's event_date is whatever date its source
  //     report/text reported, not its upload date. Since untyped/undated
  //     submissions fall back to today's real date, "today" ends up WITH
  //     the max event_date too (it's not empty) even when it's full of
  //     stale test claims and the real newly-ingested ones are dated
  //     elsewhere (e.g. this project's sample data all sits in Aug 2026).
  //   - most claims / most actionable claims per date: today can easily
  //     have MORE accumulated claims than the date someone just uploaded
  //     to, for the same reason.
  // Sorting by created_at (when the claim actually entered the system)
  // instead directly answers "where did what I just ingested land" --
  // exactly what "newly extracted claims aren't visible in the digest"
  // means. Runs once; the Today/prev/next/calendar controls below still
  // navigate normally afterward, including to the real today if wanted.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const all = await digestApi.getAll();
        if (!cancelled && all.length > 0) {
          const mostRecentlyCreated = all.reduce((latest, e) =>
            e.created_at > latest.created_at ? e : latest
          );
          const latestDate = mostRecentlyCreated.event_date;
          if (latestDate !== selectedDate) {
            setSelectedDate(latestDate);
            setCurrentMonth(new Date(latestDate));
            setHasResolvedInitialDate(true);
            return;
          }
        }
      } catch {
        // Fall through -- load whatever selectedDate already is (today).
      }
      if (!cancelled) setHasResolvedInitialDate(true);
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!hasResolvedInitialDate) return;
    loadDigest(selectedDate);
  }, [selectedDate, hasResolvedInitialDate]);

  const handleDateChange = (newDateStr: string) => {
    setSelectedDate(newDateStr);
    setShowCalendar(false);
  };

  const handlePrevDay = () => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() - 1);
    setSelectedDate(d.toISOString().split('T')[0]);
  };

  const handleNextDay = () => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + 1);
    setSelectedDate(d.toISOString().split('T')[0]);
  };

  const handleToday = () => {
    const today = new Date().toISOString().split('T')[0];
    setSelectedDate(today);
    setCurrentMonth(new Date());
  };

  const handleBulkApprove = async () => {
    const reviewableIds = events
      .filter((e) => e.status === 'REVIEW_REQUIRED' || e.status === 'VALIDATED')
      .map((e) => e.event_id);

    if (reviewableIds.length === 0) return;

    setIsBulking(true);
    try {
      const res = await digestApi.bulkApprove(reviewableIds);
      setBulkResult(res);
      loadDigest(selectedDate);
    } catch (err: any) {
      setError(t('digest.bulkApproveFailed', { message: err.message }));
    } finally {
      setIsBulking(false);
    }
  };

  const totalClaims = events.length;
  const reviewRequired = events.filter((e) => e.status === 'REVIEW_REQUIRED').length;
  const validated = events.filter((e) => e.status === 'VALIDATED').length;
  const approved = events.filter((e) => e.status === 'APPROVED').length;
  const hold = events.filter((e) => e.status === 'HOLD').length;

  const getStatusBadge = (status: ClaimStatus) => {
    switch (status) {
      case 'APPROVED':
        return <span className="bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 text-xs px-2.5 py-0.5 rounded-full font-semibold flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> {t('digest.statusApproved')}</span>;
      case 'REVIEW_REQUIRED':
        return <span className="bg-amber-500/10 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400 border border-amber-500/30 text-xs px-2.5 py-0.5 rounded-full font-semibold flex items-center gap-1"><AlertTriangle className="w-3.5 h-3.5" /> {t('digest.statusReviewRequired')}</span>;
      case 'VALIDATED':
        return <span className="bg-blue-500/10 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 border border-blue-500/30 text-xs px-2.5 py-0.5 rounded-full font-semibold flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> {t('digest.statusMachineValidated')}</span>;
      case 'HOLD':
        return <span className="bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-400 border border-slate-300 dark:border-slate-700 text-xs px-2.5 py-0.5 rounded-full font-semibold flex items-center gap-1"><PauseCircle className="w-3.5 h-3.5" /> {t('digest.statusOnHold')}</span>;
      case 'REJECTED':
        return <span className="bg-rose-500/10 dark:bg-rose-500/20 text-rose-700 dark:text-rose-400 border border-rose-500/30 text-xs px-2.5 py-0.5 rounded-full font-semibold flex items-center gap-1"><XCircle className="w-3.5 h-3.5" /> {t('digest.statusRejected')}</span>;
      default:
        return <span className="bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-300 text-xs px-2.5 py-0.5 rounded-full font-semibold">{status}</span>;
    }
  };

  const renderCalendar = () => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();

    const firstDayOfMonth = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const days = [];
    for (let i = 0; i < firstDayOfMonth; i++) {
      days.push(<div key={`empty-${i}`} className="h-8 w-8" />);
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const dateString = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      const isSelected = dateString === selectedDate;
      const isTodayStr = dateString === new Date().toISOString().split('T')[0];

      days.push(
        <button
          key={d}
          type="button"
          onClick={() => handleDateChange(dateString)}
          className={cn(
            'h-8 w-8 rounded-lg text-xs font-semibold flex items-center justify-center transition-all',
            isSelected
              ? 'bg-[#FC4C02] text-white shadow-md font-bold scale-105'
              : isTodayStr
              ? 'border border-[#FC4C02] text-[#FC4C02] hover:bg-slate-100 dark:hover:bg-blue-900/50'
              : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-blue-900/40'
          )}
        >
          {d}
        </button>
      );
    }

    const monthNames = t('digest.months', { returnObjects: true }) as unknown as string[];

    return (
      <div className="p-4 bg-white dark:bg-[#001E60] border border-slate-200 dark:border-blue-800 rounded-2xl shadow-xl w-72 space-y-3 z-50">
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-blue-800 pb-2">
          <span className="text-xs font-bold text-slate-900 dark:text-white">
            {monthNames[month]} {year}
          </span>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-blue-900/60"
              onClick={() => setCurrentMonth(new Date(year, month - 1, 1))}
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-blue-900/60"
              onClick={() => setCurrentMonth(new Date(year, month + 1, 1))}
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
        <div className="grid grid-cols-7 gap-1 text-center text-[10px] font-bold text-slate-400 uppercase">
          <span>{t('digest.sunday')}</span><span>{t('digest.monday')}</span><span>{t('digest.tuesday')}</span><span>{t('digest.wednesday')}</span><span>{t('digest.thursday')}</span><span>{t('digest.friday')}</span><span>{t('digest.saturday')}</span>
        </div>
        <div className="grid grid-cols-7 gap-1">{days}</div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Top Header Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-blue-900/50 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight flex items-center gap-2">
            <ClipboardList className="w-6 h-6 text-[#FC4C02]" />
            {t('digest.title')}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-xs mt-1">
            {t('digest.subtitle')}
          </p>
        </div>

        {/* Date Selector */}
        <div className="flex items-center gap-2 relative">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePrevDay}
            className="bg-white dark:bg-[#001E60] border-slate-300 dark:border-blue-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-blue-900/50 h-9"
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowCalendar(!showCalendar)}
            className="bg-white dark:bg-[#001E60] border-slate-300 dark:border-blue-800 text-slate-900 dark:text-slate-100 hover:border-[#FC4C02] font-mono text-xs h-9 px-3 gap-2 shadow-sm"
          >
            <CalendarIcon className="w-4 h-4 text-[#FC4C02]" />
            <span>{selectedDate}</span>
          </Button>

          {showCalendar && (
            <div className="absolute right-0 top-11">
              {renderCalendar()}
            </div>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={handleNextDay}
            className="bg-white dark:bg-[#001E60] border-slate-300 dark:border-blue-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-blue-900/50 h-9"
          >
            <ChevronRight className="w-4 h-4" />
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleToday}
            className="text-xs text-[#FC4C02] hover:text-[#e04302] hover:bg-[#FC4C02]/10 h-9 font-semibold"
          >
            {t('digest.today')}
          </Button>
        </div>
      </div>

      {/* Summary KPI Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="p-4 rounded-xl bg-white dark:bg-[#001E60] border border-slate-200 dark:border-blue-900/60 shadow-sm">
          <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase">{t('digest.totalClaims')}</span>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1 font-mono">{totalClaims}</div>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-[#001E60] border border-amber-500/40 bg-amber-500/5 shadow-sm">
          <span className="text-[11px] font-bold text-amber-700 dark:text-amber-400 uppercase">{t('digest.reviewRequired')}</span>
          <div className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1 font-mono">{reviewRequired}</div>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-[#001E60] border border-blue-500/40 bg-blue-500/5 shadow-sm">
          <span className="text-[11px] font-bold text-blue-700 dark:text-blue-400 uppercase font-mono">{t('digest.validated')}</span>
          <div className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1 font-mono">{validated}</div>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-[#001E60] border border-emerald-500/40 bg-emerald-500/5 shadow-sm">
          <span className="text-[11px] font-bold text-emerald-700 dark:text-emerald-400 uppercase font-mono">{t('digest.approved')}</span>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1 font-mono">{approved}</div>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-[#001E60] border border-slate-200 dark:border-blue-900/60 shadow-sm col-span-2 sm:col-span-1">
          <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase">{t('digest.onHold')}</span>
          <div className="text-2xl font-bold text-slate-700 dark:text-slate-400 mt-1 font-mono">{hold}</div>
        </div>
      </div>

      {/* Bulk Action Toolbar */}
      <div className="p-4 rounded-xl bg-white dark:bg-[#001E60] border border-slate-200 dark:border-blue-900/60 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-sm">
        <div className="text-xs text-slate-700 dark:text-slate-300 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#FC4C02] shrink-0" />
          <span>
            {t('digest.claimsReadyForSignoff', { count: reviewRequired + validated, date: selectedDate })}
          </span>
        </div>

        <Button
          onClick={handleBulkApprove}
          disabled={isBulking || (reviewRequired + validated === 0)}
          className="bg-[#FC4C02] hover:bg-[#e04302] text-white text-xs font-semibold h-9 px-4 shadow-md shadow-[#FC4C02]/20 w-full sm:w-auto rounded-xl"
        >
          {isBulking ? (
            <span>{t('digest.processingBulkApproval')}</span>
          ) : (
            <>
              <CheckSquare className="w-4 h-4 mr-1.5" />
              {t('digest.bulkApprove')}
            </>
          )}
        </Button>
      </div>

      {bulkResult && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300 text-xs flex items-center justify-between">
          <span>{t('digest.bulkApprovalComplete', { count: bulkResult.approved.length })}</span>
          <Button variant="ghost" size="sm" onClick={() => setBulkResult(null)} className="h-6 text-xs">{t('common.dismiss')}</Button>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs flex items-center justify-between">
          <span>{error}</span>
          <Button variant="outline" size="sm" onClick={() => loadDigest(selectedDate)} className="border-rose-500/40 text-xs">
            {t('common.retry')}
          </Button>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-28 rounded-2xl bg-white dark:bg-[#001E60] border border-slate-200 dark:border-blue-900/60 animate-pulse" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <Card className="bg-white dark:bg-[#001E60] border-slate-200 dark:border-blue-900/60 p-12 text-center shadow-sm">
          <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-blue-900/60 flex items-center justify-center mx-auto text-slate-400 mb-3">
            <Clock className="w-6 h-6" />
          </div>
          <h3 className="text-slate-900 dark:text-slate-100 font-bold text-base">{t('digest.noClaimsForDate', { date: selectedDate })}</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
            {t('digest.noClaimsDesc')}
          </p>
        </Card>
      ) : (
        <div className="space-y-6">
          {['CIVIL', 'PIPING', 'STATIC_ROTATING_EQUIPMENT', 'ELECTRICAL', 'INSTRUMENTATION', 'HSE', 'UNASSIGNED'].map((disc) => {
            const discEvents = events.filter((e) =>
              disc === 'UNASSIGNED' ? !e.discipline || e.discipline === 'UNASSIGNED' : e.discipline === disc
            );
            if (discEvents.length === 0) return null;

            return (
              <div key={disc} className="space-y-3">
                <div className="flex items-center gap-2 border-b border-slate-200 dark:border-blue-900/50 pb-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-[#FC4C02] font-mono">
                    {disc.replace('_', ' ')}
                  </span>
                  <span className="text-[10px] bg-slate-100 dark:bg-blue-900/60 text-slate-700 dark:text-blue-200 px-2 py-0.5 rounded-full font-mono font-semibold">
                    {t('digest.claimsCount', { count: discEvents.length })}
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-3">
                  {discEvents.map((ev) => (
                    <div
                      key={ev.event_id}
                      onClick={() => navigate(`/review?event_id=${ev.event_id}`)}
                      className={cn(
                        'p-4 rounded-xl bg-white dark:bg-[#001E60] border transition-all cursor-pointer hover:border-[#FC4C02] shadow-sm group relative',
                        ev.status === 'REVIEW_REQUIRED'
                          ? 'border-amber-500/50 bg-amber-500/[0.02]'
                          : 'border-slate-200 dark:border-blue-900/60'
                      )}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          {getStatusBadge(ev.status)}
                          <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">{t('digest.idLabel')}: {ev.event_id}</span>
                          <span className="text-[11px] text-slate-400 font-mono">· {t('digest.channelLabel')}: {ev.input_channel}</span>
                        </div>

                        <div className="text-xs text-slate-500 dark:text-slate-400 font-mono flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          {ev.event_date}
                        </div>
                      </div>

                      <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 leading-relaxed mb-3 group-hover:text-[#FC4C02]">
                        "{ev.raw_claim_text}"
                      </p>

                      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 dark:border-blue-900/40 text-xs">
                        <div className="flex items-center gap-4 text-slate-600 dark:text-slate-300">
                          <div>
                            {t('digest.matchedActivity')}:{' '}
                            <span className="font-mono text-slate-900 dark:text-white font-bold">
                              {ev.matched_activity_id || t('digest.awaitingMatch')}
                            </span>
                          </div>
                          {ev.claimed_pct !== null && (
                            <div>
                              {t('digest.progress')}:{' '}
                              <span className="font-mono text-[#FC4C02] font-bold">{ev.claimed_pct}%</span>
                            </div>
                          )}
                        </div>

                        <div className="text-[#FC4C02] font-semibold flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                          <span>{t('digest.inspectClaim')}</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
