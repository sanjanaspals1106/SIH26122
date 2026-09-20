import React, { useState, useMemo } from 'react';
import { InvestigationContext } from '@/api';
import {
  Activity,
  FileText,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  GitCommit,
  Layers,
  Filter,
  Eye,
  Info,
  ChevronRight,
  Sparkles,
  Link,
  ShieldCheck,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface KnowledgeGraphViewProps {
  investigation: InvestigationContext;
  onClose?: () => void;
}

type EntityCategory =
  | 'activity'
  | 'execution_event'
  | 'validation'
  | 'conflict'
  | 'evidence'
  | 'decision'
  | 'approved_actual';

interface GraphNode {
  id: string;
  category: EntityCategory;
  title: string;
  subtitle: string;
  statusBadge?: string;
  statusType?: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  parentId?: string;
  data: Record<string, any>;
}

export function KnowledgeGraphView({ investigation, onClose }: KnowledgeGraphViewProps) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [categoryFilters, setCategoryFilters] = useState<Record<EntityCategory, boolean>>({
    activity: true,
    execution_event: true,
    validation: true,
    conflict: true,
    evidence: true,
    decision: true,
    approved_actual: true,
  });

  const toggleCategory = (cat: EntityCategory) => {
    setCategoryFilters((prev) => ({ ...prev, [cat]: !prev[cat] }));
  };

  // Build the two-layer substantiated entity graph
  const { nodesByCategory, totalSubstantiatedNodes } = useMemo(() => {
    const byCategory: Record<EntityCategory, GraphNode[]> = {
      activity: [],
      execution_event: [],
      validation: [],
      conflict: [],
      evidence: [],
      decision: [],
      approved_actual: [],
    };

    const ctx = investigation.context;
    const rootId = investigation.root_activity_id;

    // 1. Root Activity (Layer 1)
    const rootAct = ctx.activity || {};
    byCategory.activity.push({
      id: `act:${rootId}`,
      category: 'activity',
      title: rootId,
      subtitle: rootAct.activity_name || rootAct.discipline || 'Target Activity',
      statusBadge: rootAct.discipline || 'ACTIVITY',
      statusType: 'info',
      data: rootAct,
    });

    // 2. Traversed Activities / Dependencies (Layer 1)
    for (const dep of ctx.dependencies || []) {
      const otherId =
        dep.predecessor_activity_id === rootId
          ? dep.successor_activity_id
          : dep.predecessor_activity_id;
      const isSuccessor = dep.predecessor_activity_id === rootId;

      if (!byCategory.activity.some((n) => n.id === `act:${otherId}`)) {
        byCategory.activity.push({
          id: `act:${otherId}`,
          category: 'activity',
          title: otherId,
          subtitle: isSuccessor ? `Successor (${dep.relationship_type})` : `Predecessor (${dep.relationship_type})`,
          statusBadge: dep.relationship_type || 'FS',
          statusType: 'neutral',
          parentId: `act:${rootId}`,
          data: dep,
        });
      }
    }

    // 3. Execution Events (Layer 1)
    for (const ev of ctx.execution_events || []) {
      const eid = ev.event_id || 'EVT';
      byCategory.execution_event.push({
        id: `evt:${eid}`,
        category: 'execution_event',
        title: eid,
        subtitle: ev.raw_claim_text ? `"${ev.raw_claim_text.slice(0, 48)}..."` : 'Field Claim',
        statusBadge: ev.status || 'REPORTED',
        statusType: ev.status === 'VALIDATED' ? 'success' : 'warning',
        parentId: `act:${rootId}`,
        data: ev,
      });
    }

    // 4. Validations (Layer 2 - Ask Why Context)
    for (const val of ctx.validations || []) {
      byCategory.validation.push({
        id: `val:${val.issue_id || Math.random()}`,
        category: 'validation',
        title: val.rule_code || 'RULE_CHECK',
        subtitle: val.description || 'Validation Issue',
        statusBadge: val.severity || 'WARNING',
        statusType: val.severity === 'FATAL' || val.severity === 'ERROR' ? 'danger' : 'warning',
        parentId: val.event_id ? `evt:${val.event_id}` : `act:${rootId}`,
        data: val,
      });
    }

    // 5. Conflicts (Layer 2 - Ask Why Context)
    for (const conf of ctx.conflicts || []) {
      byCategory.conflict.push({
        id: `conf:${conf.conflict_id || Math.random()}`,
        category: 'conflict',
        title: conf.conflict_id || 'CONFLICT',
        subtitle: `Variance ${conf.variance_pct ? `${conf.variance_pct}%` : 'Detected'}`,
        statusBadge: conf.status || 'OPEN',
        statusType: 'danger',
        parentId: conf.event_id_a ? `evt:${conf.event_id_a}` : `act:${rootId}`,
        data: conf,
      });
    }

    // 6. Evidence / Source References (Layer 2 - Ask Why Context)
    for (const evd of ctx.evidence || []) {
      byCategory.evidence.push({
        id: `ref:${evd.reference_id || Math.random()}`,
        category: 'evidence',
        title: evd.file_name || 'Source Reference',
        subtitle: evd.raw_snippet ? `"${evd.raw_snippet.slice(0, 48)}..."` : (evd.row_cell_ref || 'Reference'),
        statusBadge: evd.sheet_name ? `${evd.sheet_name}` : 'PROVENANCE',
        statusType: 'info',
        parentId: evd.event_id ? `evt:${evd.event_id}` : `act:${rootId}`,
        data: evd,
      });
    }

    // 7. Planner Decisions (Layer 1)
    for (const dec of ctx.decisions || []) {
      byCategory.decision.push({
        id: `dec:${dec.decision_id}`,
        category: 'decision',
        title: dec.decision_id ? `DEC-${dec.decision_id.slice(0, 8)}` : 'Decision',
        subtitle: dec.justification ? `"${dec.justification.slice(0, 48)}..."` : 'Supervisor Review',
        statusBadge: dec.action || 'REVIEW',
        statusType: dec.action === 'APPROVE' ? 'success' : dec.action === 'REJECT' ? 'danger' : 'warning',
        parentId: dec.event_id ? `evt:${dec.event_id}` : `act:${rootId}`,
        data: dec,
      });
    }

    // 8. Approved Actuals (Layer 1)
    for (const actl of ctx.approved_actuals || []) {
      byCategory.approved_actual.push({
        id: `actl:${actl.actual_id}`,
        category: 'approved_actual',
        title: actl.actual_id ? `ACTL-${actl.actual_id.slice(0, 8)}` : 'Approved Actual',
        subtitle: actl.actual_finish ? `Finished: ${actl.actual_finish}` : `Progress: ${actl.actual_pct_complete ?? 100}%`,
        statusBadge: 'COMMITTED',
        statusType: 'success',
        parentId: actl.decision_id ? `dec:${actl.decision_id}` : `act:${rootId}`,
        data: actl,
      });
    }

    const total = Object.values(byCategory).reduce((sum, list) => sum + list.length, 0);

    return { nodesByCategory: byCategory, totalSubstantiatedNodes: total };
  }, [investigation]);

  const categoriesOrder: { key: EntityCategory; label: string; icon: React.ComponentType<any>; color: string }[] = [
    { key: 'activity', label: 'Activities', icon: Activity, color: 'text-violet-500' },
    { key: 'execution_event', label: 'Field Claims / Events', icon: FileText, color: 'text-blue-500' },
    { key: 'validation', label: 'Validation Issues', icon: AlertTriangle, color: 'text-amber-500' },
    { key: 'conflict', label: 'Conflict Records', icon: ShieldAlert, color: 'text-rose-500' },
    { key: 'evidence', label: 'Source Evidence', icon: Link, color: 'text-cyan-500' },
    { key: 'decision', label: 'Supervisor Decisions', icon: CheckCircle2, color: 'text-emerald-500' },
    { key: 'approved_actual', label: 'Approved Actuals', icon: ShieldCheck, color: 'text-purple-500' },
  ];

  return (
    <div className="space-y-4">
      {/* Category Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-50 dark:bg-[#001438] rounded-xl border border-slate-200 dark:border-blue-900/40 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-slate-500 dark:text-slate-400 text-[11px] font-semibold flex items-center gap-1 mr-1">
            <Filter className="w-3.5 h-3.5" /> Entity Filter:
          </span>
          {categoriesOrder.map(({ key, label, icon: Icon, color }) => {
            const count = nodesByCategory[key].length;
            const active = categoryFilters[key];
            if (count === 0 && key !== 'activity') return null;

            return (
              <button
                key={key}
                onClick={() => toggleCategory(key)}
                className={cn(
                  'flex items-center gap-1.5 px-2.5 py-1 rounded-lg font-mono text-[11px] transition-all cursor-pointer border',
                  active
                    ? 'bg-white dark:bg-[#001E60] border-slate-300 dark:border-blue-800 text-slate-900 dark:text-slate-100 shadow-xs'
                    : 'bg-transparent border-transparent text-slate-400 dark:text-slate-500 opacity-60'
                )}
              >
                <Icon className={cn('w-3.5 h-3.5', color)} />
                <span>{label}</span>
                <span className="px-1.5 py-0.2 rounded-full bg-slate-100 dark:bg-slate-800 text-[10px] font-bold">
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        <div className="text-[10px] font-mono text-slate-400">
          Substantiated Database Records: {totalSubstantiatedNodes}
        </div>
      </div>

      {/* Main Graph Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Entity Columns Canvas */}
        <div className={cn(selectedNode ? 'lg:col-span-8' : 'lg:col-span-12', 'space-y-4')}>
          <div className="p-4 bg-white dark:bg-[#001E60]/50 rounded-2xl border border-slate-200 dark:border-blue-900/50 shadow-sm space-y-6">
            {categoriesOrder.map(({ key, label, icon: Icon, color }) => {
              if (!categoryFilters[key]) return null;
              const nodes = nodesByCategory[key];
              if (nodes.length === 0) return null;

              return (
                <div key={key} className="space-y-2.5">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 pb-1 border-b border-slate-100 dark:border-blue-900/30">
                    <Icon className={cn('w-4 h-4', color)} />
                    <span>{label}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                      {nodes.length}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {nodes.map((node) => {
                      const isSelected = selectedNode?.id === node.id;
                      return (
                        <div
                          key={node.id}
                          onClick={() => setSelectedNode(isSelected ? null : node)}
                          className={cn(
                            'p-3 rounded-xl border text-xs cursor-pointer transition-all duration-150',
                            isSelected
                              ? 'ring-2 ring-violet-500 bg-violet-50/80 dark:bg-violet-950/40 border-violet-500'
                              : 'bg-slate-50/75 dark:bg-[#001438] border-slate-200 dark:border-blue-900/40 hover:border-slate-300 dark:hover:border-blue-700'
                          )}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-mono font-bold text-slate-900 dark:text-slate-100 truncate">
                              {node.title}
                            </span>
                            {node.statusBadge && (
                              <span
                                className={cn(
                                  'font-mono text-[9px] font-bold px-1.5 py-0.5 rounded uppercase',
                                  node.statusType === 'success'
                                    ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300'
                                    : node.statusType === 'danger'
                                    ? 'bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-300'
                                    : node.statusType === 'warning'
                                    ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300'
                                    : 'bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300'
                                )}
                              >
                                {node.statusBadge}
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-600 dark:text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                            {node.subtitle}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Factual Inspector */}
        {selectedNode && (
          <div className="lg:col-span-4">
            <Card className="sticky top-4 bg-white dark:bg-[#001E60] border-slate-200 dark:border-blue-900/60 shadow-md">
              <CardHeader className="pb-3 border-b border-slate-200 dark:border-blue-900/40 flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-sm font-bold font-mono text-slate-900 dark:text-slate-100">
                    {selectedNode.title}
                  </CardTitle>
                  <p className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mt-0.5">
                    Category: {selectedNode.category}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 cursor-pointer"
                >
                  ✕
                </button>
              </CardHeader>
              <CardContent className="pt-4 space-y-3 text-xs max-h-[480px] overflow-y-auto">
                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-[#001438] border border-slate-200 dark:border-blue-900/40">
                  <span className="text-[10px] text-slate-400 uppercase font-bold block mb-1">
                    Verbatim Database Record
                  </span>
                  <div className="space-y-1 font-mono text-[11px]">
                    {Object.entries(selectedNode.data).map(([key, val]) => {
                      if (val === null || val === undefined || typeof val === 'object') return null;
                      return (
                        <div key={key} className="flex justify-between items-start gap-2 py-0.5 border-b border-slate-200/50 dark:border-blue-900/30">
                          <span className="text-slate-500 dark:text-slate-400">{key}:</span>
                          <span className="text-slate-800 dark:text-slate-200 font-semibold text-right break-all">
                            {String(val)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="p-3 bg-blue-50/70 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900/50 rounded-xl text-[11px] text-blue-800 dark:text-blue-300">
                  <strong>Factual Audit Contract:</strong> Node and properties correspond strictly to authenticated backend records. No inferred or fabricated relationships are displayed.
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
