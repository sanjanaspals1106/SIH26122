/**
 * WBSActivityExplorer — Read-only WBS Activity Grouping Display
 *
 * Feature 30A (Stage 7). Displays the flat WBS grouping returned by
 * GET /api/v1/schedules/{schedule_id}/wbs-tree. Client-side joins
 * activity_id → activity_name via schedulesApi.getActivities().
 *
 * Strictly read-only: no editing, no splitting, no drag-drop.
 */
import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  FolderTree,
  ChevronDown,
  ChevronRight,
  Package,
  Hash,
  Loader2,
  AlertCircle,
  Search,
} from 'lucide-react';
import {
  schedulesApi,
  type WBSTreeResponse,
  type WBSGroup,
  type ScheduleActivity,
} from '@/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

// ── Enriched activity with joined name ──────────────────────────────────────

interface EnrichedActivity {
  activity_id: string;
  activity_name: string;
  planned_quantity: number | null;
  discipline: string | null;
  location: string | null;
}

interface EnrichedGroup {
  wbs_code: string;
  activities: EnrichedActivity[];
  totalQuantity: number | null;
}

// ── WBSGroupCard — collapsible group row ────────────────────────────────────

function WBSGroupCard({ group }: { group: EnrichedGroup }) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="border border-slate-200 dark:border-[#214766] rounded-xl overflow-hidden transition-all shadow-2xs hover:border-[#FF7A18]/50">
      {/* Group Header */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left bg-slate-50/90 dark:bg-[#0A2238] hover:bg-slate-100 dark:hover:bg-[#0D2942] transition-colors"
      >
        {isOpen ? (
          <ChevronDown className="w-4 h-4 text-[#475569] dark:text-[#CBD5E1] shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-[#475569] dark:text-[#CBD5E1] shrink-0" />
        )}
        <FolderTree className="w-4 h-4 text-[#FF7A18] dark:text-[#FF941F] shrink-0" />
        <span className="font-mono text-sm font-bold text-[#071A2D] dark:text-[#F5F7FA]">
          {group.wbs_code}
        </span>
        <span className="ml-auto flex items-center gap-3 text-xs text-[#475569] dark:text-[#CBD5E1] font-semibold">
          <span className="flex items-center gap-1">
            <Package className="w-3.5 h-3.5" />
            {t('wbs.activityCount', { count: group.activities.length })}
          </span>
          {group.totalQuantity !== null && (
            <span className="flex items-center gap-1 font-mono">
              <Hash className="w-3.5 h-3.5" />
              {t('wbs.totalQty', { qty: group.totalQuantity.toLocaleString() })}
            </span>
          )}
        </span>
      </button>

      {/* Expanded Activities */}
      {isOpen && (
        <div className="divide-y divide-slate-200/70 dark:divide-[#214766]/60 bg-white/70 dark:bg-[#071A2D]/80">
          {group.activities.map((a) => (
            <div
              key={a.activity_id}
              className="px-4 py-2.5 pl-12 flex items-center gap-3 text-sm hover:bg-slate-50 dark:hover:bg-[#0D2942] transition-colors"
            >
              <span className="font-mono text-xs font-bold text-[#0284C7] dark:text-[#38BDF8] w-24 shrink-0 truncate" title={a.activity_id}>
                {a.activity_id}
              </span>
              <span className="flex-1 truncate font-medium text-[#071A2D] dark:text-[#F5F7FA]">
                {a.activity_name}
              </span>
              {a.discipline && (
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-orange-50 dark:bg-orange-950/60 text-[#FF7A18] dark:text-[#FF941F] border border-orange-300 dark:border-orange-800/60 font-semibold shrink-0">
                  {a.discipline}
                </span>
              )}
              {a.planned_quantity !== null && (
                <span className="text-xs text-[#475569] dark:text-[#CBD5E1] font-mono font-semibold shrink-0">
                  {t('wbs.qty', { qty: a.planned_quantity })}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Explorer Component ─────────────────────────────────────────────────

interface WBSActivityExplorerProps {
  scheduleId?: string;
  className?: string;
}

export default function WBSActivityExplorer({
  scheduleId,
  className,
}: WBSActivityExplorerProps) {
  const { t } = useTranslation();
  const [wbsData, setWbsData] = useState<WBSTreeResponse | null>(null);
  const [activities, setActivities] = useState<ScheduleActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [tree, acts] = await Promise.all([
          schedulesApi.getWbsTree(scheduleId),
          schedulesApi.getActivities(scheduleId),
        ]);
        if (!cancelled) {
          setWbsData(tree);
          setActivities(acts);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load WBS data');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [scheduleId]);

  // Build lookup map: activity_id → ScheduleActivity
  const activityMap = useMemo(() => {
    const map = new Map<string, ScheduleActivity>();
    for (const a of activities) {
      map.set(a.activity_id, a);
    }
    return map;
  }, [activities]);

  // Enrich WBS groups with joined activity names
  const enrichedGroups: EnrichedGroup[] = useMemo(() => {
    if (!wbsData) return [];
    return wbsData.wbs_groups.map((g: WBSGroup) => {
      const enrichedActivities: EnrichedActivity[] = g.activities.map((wa) => {
        const full = activityMap.get(wa.activity_id);
        return {
          activity_id: wa.activity_id,
          activity_name: full?.activity_name ?? wa.activity_id,
          planned_quantity: wa.planned_quantity,
          discipline: full?.discipline ?? null,
          location: full?.location ?? null,
        };
      });

      const quantities = enrichedActivities
        .map((a) => a.planned_quantity)
        .filter((q): q is number => q !== null);
      const totalQuantity = quantities.length > 0
        ? quantities.reduce((sum, q) => sum + q, 0)
        : null;

      return {
        wbs_code: g.wbs_code,
        activities: enrichedActivities,
        totalQuantity,
      };
    });
  }, [wbsData, activityMap]);

  // Filter groups by search term
  const filteredGroups = useMemo(() => {
    if (!searchTerm.trim()) return enrichedGroups;
    const lc = searchTerm.toLowerCase();
    return enrichedGroups.filter(
      (g) =>
        g.wbs_code.toLowerCase().includes(lc) ||
        g.activities.some(
          (a) =>
            a.activity_id.toLowerCase().includes(lc) ||
            a.activity_name.toLowerCase().includes(lc)
        )
    );
  }, [enrichedGroups, searchTerm]);

  // ── Loading state ─────────────────────────────────────────────────────────
  if (loading) {
    return (
      <Card className={cn('animate-pulse', className)}>
        <CardContent className="flex items-center justify-center py-12 gap-3 text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">{t('wbs.loading')}</span>
        </CardContent>
      </Card>
    );
  }

  // ── Error state ───────────────────────────────────────────────────────────
  if (error) {
    return (
      <Card className={cn('border-destructive/40', className)}>
        <CardContent className="flex items-center gap-3 py-8 text-destructive">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span className="text-sm">{error}</span>
        </CardContent>
      </Card>
    );
  }

  // ── Empty state ───────────────────────────────────────────────────────────
  if (enrichedGroups.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-2 text-muted-foreground">
          <FolderTree className="w-8 h-8 opacity-40" />
          <p className="text-sm">{t('wbs.empty')}</p>
        </CardContent>
      </Card>
    );
  }

  // ── Main render ───────────────────────────────────────────────────────────
  const totalActivities = enrichedGroups.reduce((s, g) => s + g.activities.length, 0);

  return (
    <Card className={cn('border-slate-200/80 dark:border-[#214766] bg-white/95 dark:bg-[#071A2D]/95 shadow-xl rounded-2xl', className)}>
      <CardHeader className="pb-4 border-b border-slate-300 dark:border-[#214766]/60">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <FolderTree className="w-5 h-5 text-[#FF7A18] dark:text-[#FF941F]" />
            <CardTitle className="text-base font-extrabold text-[#071A2D] dark:text-[#F5F7FA]">{t('wbs.title')}</CardTitle>
          </div>
          <div className="flex items-center gap-3 text-xs text-[#475569] dark:text-[#CBD5E1] font-semibold">
            <span>{t('wbs.groupCount', { count: enrichedGroups.length })}</span>
            <span>·</span>
            <span>{t('wbs.activityTotal', { count: totalActivities })}</span>
          </div>
        </div>
        <p className="text-xs text-[#334155] dark:text-[#CBD5E1] font-medium mt-1">{t('wbs.subtitle')}</p>

        {/* Search */}
        <div className="relative mt-3">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 dark:text-[#8FA6BA]" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={t('wbs.searchPlaceholder')}
            className="w-full pl-9 pr-3 py-2 text-xs font-medium rounded-xl border border-slate-300 dark:border-[#214766] bg-white dark:bg-[#0B2742] text-[#071A2D] dark:text-[#F5F7FA] placeholder:text-slate-500 dark:placeholder:text-[#8FA6BA] focus:outline-hidden focus:ring-2 focus:ring-[#FF7A18]/30 focus:border-[#FF7A18]"
          />
        </div>
      </CardHeader>

      <CardContent className="space-y-2.5 pt-4">
        {filteredGroups.length === 0 ? (
          <p className="text-xs font-semibold text-[#475569] dark:text-[#CBD5E1] text-center py-6">
            {t('wbs.noResults')}
          </p>
        ) : (
          filteredGroups.map((group) => (
            <WBSGroupCard key={group.wbs_code} group={group} />
          ))
        )}
      </CardContent>
    </Card>
  );
}
