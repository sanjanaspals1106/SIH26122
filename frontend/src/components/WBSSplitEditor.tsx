import React, { useState } from 'react';
import {
  Plus,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  Layers,
  ArrowRight,
  Scale,
  Sparkles,
} from 'lucide-react';
import {
  ExecutionEvent,
  ScheduleActivity,
  SplitBasis,
  WBSSplitAllocation,
  WBSSplitRequest,
  wbsApi,
} from '../api';

interface WBSSplitEditorProps {
  claim: ExecutionEvent;
  activities: ScheduleActivity[];
  onSuccess: () => void;
  onCancel: () => void;
}

export const WBSSplitEditor: React.FC<WBSSplitEditorProps> = ({
  claim,
  activities,
  onSuccess,
  onCancel,
}) => {
  const isPctMode = claim.claim_mode === 'CUMULATIVE_PCT' || claim.claimed_pct != null;
  const targetTotal = isPctMode
    ? claim.claimed_pct ?? 100
    : claim.claimed_quantity ?? 100;

  // Initial allocations: start with top matched activity or first available activity
  const [allocations, setAllocations] = useState<
    {
      activity_id: string;
      split_basis: SplitBasis;
      allocated_pct: number;
      allocated_quantity: number;
      rationale: string;
    }[]
  >(() => [
    {
      activity_id: claim.matched_activity_id || activities[0]?.activity_id || '',
      split_basis: 'WBS_WEIGHTED',
      allocated_pct: isPctMode ? Math.round(targetTotal * 0.6) : 0,
      allocated_quantity: !isPctMode ? Math.round(targetTotal * 0.6) : 0,
      rationale: 'Primary work package',
    },
    {
      activity_id: activities[1]?.activity_id || '',
      split_basis: 'MANUAL',
      allocated_pct: isPctMode ? Math.round(targetTotal * 0.4) : 0,
      allocated_quantity: !isPctMode ? Math.round(targetTotal * 0.4) : 0,
      rationale: 'Secondary tie-in / handover scope',
    },
  ]);

  const [justification, setJustification] = useState(
    'Claim granularity spans multiple distinct WBS deliverables.'
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentSum = allocations.reduce((sum, a) => {
    return sum + (isPctMode ? Number(a.allocated_pct) || 0 : Number(a.allocated_quantity) || 0);
  }, 0);

  const remaining = Number((targetTotal - currentSum).toFixed(2));
  const isBalanced = Math.abs(remaining) < 0.001;

  const handleAddRow = () => {
    // Choose next activity not yet selected if possible
    const selectedIds = new Set(allocations.map((a) => a.activity_id));
    const nextActivity = activities.find((a) => !selectedIds.has(a.activity_id)) || activities[0];

    const autoFill = Math.max(0, remaining);
    setAllocations((prev) => [
      ...prev,
      {
        activity_id: nextActivity ? nextActivity.activity_id : '',
        split_basis: 'MANUAL',
        allocated_pct: isPctMode ? autoFill : 0,
        allocated_quantity: !isPctMode ? autoFill : 0,
        rationale: '',
      },
    ]);
  };

  const handleRemoveRow = (index: number) => {
    if (allocations.length <= 1) return;
    setAllocations((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpdateRow = (
    index: number,
    field: 'activity_id' | 'split_basis' | 'allocated_pct' | 'allocated_quantity' | 'rationale',
    value: any
  ) => {
    setAllocations((prev) => {
      const next = [...prev];
      const updatedRow = { ...next[index], [field]: value };
      // If user directly edits the allocated numbers, transition basis to MANUAL
      if (field === 'allocated_pct' || field === 'allocated_quantity') {
        updatedRow.split_basis = 'MANUAL';
      }
      next[index] = updatedRow;
      return next;
    });
  };

  const handleAutoDistribute = () => {
    if (allocations.length === 0) return;
    const share = Number((targetTotal / allocations.length).toFixed(2));
    setAllocations((prev) =>
      prev.map((item, i) => ({
        ...item,
        split_basis: 'EQUAL',
        allocated_pct: isPctMode
          ? i === prev.length - 1
            ? Number((targetTotal - share * (prev.length - 1)).toFixed(2))
            : share
          : item.allocated_pct,
        allocated_quantity: !isPctMode
          ? i === prev.length - 1
            ? Number((targetTotal - share * (prev.length - 1)).toFixed(2))
            : share
          : item.allocated_quantity,
      }))
    );
  };

  const handleSubmit = async () => {
    if (!isBalanced) {
      setError(`Allocations must sum exactly to ${targetTotal}${isPctMode ? '%' : ` ${claim.claimed_uom || 'units'}`}. Currently: ${currentSum}`);
      return;
    }

    // Check for empty activity selections or duplicates
    const actIds = allocations.map((a) => a.activity_id.trim());
    if (actIds.some((id) => !id)) {
      setError('Every split allocation row must have a valid activity selected.');
      return;
    }
    const uniqueIds = new Set(actIds);
    if (uniqueIds.size !== actIds.length) {
      setError('Duplicate activities selected in split allocation. Each activity must be unique.');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const splitAllocations: WBSSplitAllocation[] = allocations.map((a) => ({
        activity_id: a.activity_id,
        split_basis: a.split_basis || 'MANUAL',
        split_pct: isPctMode
          ? Number(a.allocated_pct)
          : targetTotal > 0
          ? Number(((Number(a.allocated_quantity) / targetTotal) * 100).toFixed(2))
          : 0,
        allocated_pct: isPctMode ? Number(a.allocated_pct) : null,
        allocated_quantity: !isPctMode ? Number(a.allocated_quantity) : null,
        uom: claim.claimed_uom || null,
        rationale: a.rationale || null,
      }));

      const req: WBSSplitRequest = {
        event_id: claim.event_id,
        schedule_id: claim.schedule_id || 'sched-OIL-2026',
        allocations: splitAllocations,
        justification,
      };

      await wbsApi.splitClaim(req);
      onSuccess();
    } catch (err: any) {
      setError(err?.message || 'Failed to submit WBS split allocation.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-[#1565C0] dark:text-blue-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
              WBS Split Allocation
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/60 text-blue-800 dark:text-blue-300">
                Granularity Bridge
              </span>
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Split this claim across multiple schedule WBS activities when work spans several work packages.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleAutoDistribute}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg text-foreground bg-card-subtle hover:bg-muted border border-border transition-colors"
            title="Evenly distribute remaining target across rows"
          >
            <Scale className="w-3.5 h-3.5" />
            Distribute Evenly
          </button>
        </div>
      </div>

      {/* Target Claim Summary */}
      <div className="mt-4 p-3 rounded-lg bg-card-subtle border border-border flex flex-wrap items-center justify-between gap-3 text-xs">
        <div>
          <span className="text-muted-foreground">Claim ID: </span>
          <span className="font-mono font-semibold text-foreground">{claim.event_id}</span>
          <span className="mx-2 text-border">•</span>
          <span className="text-muted-foreground">Mode: </span>
          <span className="font-medium text-foreground">
            {isPctMode ? 'Cumulative Percentage' : 'Incremental Quantity'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Target to Allocate:</span>
          <span className="font-bold text-sm text-[#FF7A18]">
            {targetTotal} {isPctMode ? '%' : (claim.claimed_uom || 'units')}
          </span>
        </div>
      </div>

      {/* Split Allocation Rows */}
      <div className="mt-4 space-y-3">
        {allocations.map((alloc, idx) => {
          const selectedAct = activities.find((a) => a.activity_id === alloc.activity_id);

          return (
            <div
              key={idx}
              className="p-3.5 rounded-lg border border-border bg-card-subtle hover:border-primary/50 transition-colors"
            >
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground w-8">
                  #{idx + 1}
                </div>

                {/* Activity Picker */}
                <div className="flex-1 min-w-[220px] w-full sm:w-auto">
                  <label className="block text-[11px] font-semibold text-muted-foreground mb-1">
                    Target Activity
                  </label>
                  <select
                    value={alloc.activity_id}
                    onChange={(e) => handleUpdateRow(idx, 'activity_id', e.target.value)}
                    className="w-full text-xs rounded-lg border border-slate-300 dark:border-[#1E3A5F] bg-white dark:bg-[#0A2340] text-slate-900 dark:text-[#F5F7FA] px-3 py-2 focus:ring-2 focus:ring-[#FF7A18] focus:outline-hidden"
                  >
                    <option value="" disabled>Select Activity</option>
                    {activities.map((a) => (
                      <option key={a.activity_id} value={a.activity_id}>
                        {a.activity_id} — {a.activity_name} ({a.discipline} | WBS: {a.wbs_code || 'N/A'})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Allocation Input */}
                <div className="w-full sm:w-32">
                  <label className="block text-[11px] font-semibold text-muted-foreground mb-1">
                    {isPctMode ? 'Share (%)' : `Quantity (${claim.claimed_uom || 'qty'})`}
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      step="any"
                      min="0"
                      max={isPctMode ? 100 : undefined}
                      value={isPctMode ? alloc.allocated_pct : alloc.allocated_quantity}
                      onChange={(e) =>
                        handleUpdateRow(
                          idx,
                          isPctMode ? 'allocated_pct' : 'allocated_quantity',
                          parseFloat(e.target.value) || 0
                        )
                      }
                      className="w-full text-xs rounded-lg border border-slate-300 dark:border-[#1E3A5F] bg-white dark:bg-[#0A2340] text-slate-900 dark:text-[#F5F7FA] px-3 py-2 pr-8 focus:ring-2 focus:ring-[#FF7A18] focus:outline-hidden font-mono"
                    />
                    <span className="absolute right-2.5 top-2 text-xs text-muted-foreground font-medium">
                      {isPctMode ? '%' : (claim.claimed_uom || '')}
                    </span>
                  </div>
                </div>

                {/* Basis Picker */}
                <div className="w-full sm:w-28">
                  <label className="block text-[11px] font-semibold text-muted-foreground mb-1">
                    Basis
                  </label>
                  <select
                    value={alloc.split_basis || 'MANUAL'}
                    onChange={(e) => handleUpdateRow(idx, 'split_basis', e.target.value as SplitBasis)}
                    className="w-full text-xs rounded-lg border border-slate-300 dark:border-[#1E3A5F] bg-white dark:bg-[#0A2340] text-slate-900 dark:text-[#F5F7FA] px-2 py-2 focus:ring-2 focus:ring-[#FF7A18] focus:outline-hidden font-mono text-[11px]"
                  >
                    <option value="MANUAL">MANUAL</option>
                    <option value="EQUAL">EQUAL</option>
                    <option value="WBS_WEIGHTED">WEIGHTED</option>
                  </select>
                </div>

                {/* Rationale Input */}
                <div className="flex-1 min-w-[180px] w-full sm:w-auto">
                  <label className="block text-[11px] font-semibold text-muted-foreground mb-1">
                    Scope Rationale
                  </label>
                  <input
                    type="text"
                    placeholder="e.g., South wing portion"
                    value={alloc.rationale}
                    onChange={(e) => handleUpdateRow(idx, 'rationale', e.target.value)}
                    className="w-full text-xs rounded-lg border border-slate-300 dark:border-[#1E3A5F] bg-white dark:bg-[#0A2340] text-slate-900 dark:text-[#F5F7FA] px-3 py-2 focus:ring-2 focus:ring-[#FF7A18] focus:outline-hidden"
                  />
                </div>

                {/* Delete button */}
                <div className="sm:pt-5">
                  <button
                    type="button"
                    onClick={() => handleRemoveRow(idx)}
                    disabled={allocations.length <= 1}
                    className="p-2 text-muted-foreground hover:text-red-500 disabled:opacity-30 disabled:hover:text-muted-foreground transition-colors rounded-lg hover:bg-card"
                    title="Remove split line"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {selectedAct && (
                <div className="mt-2 pt-2 border-t border-border flex items-center gap-3 text-[11px] text-muted-foreground">
                  <span>WBS: <strong className="text-foreground">{selectedAct.wbs_code || 'Root'}</strong></span>
                  <span>Discipline: <strong className="text-foreground">{selectedAct.discipline}</strong></span>
                  <span>Location: <strong className="text-foreground">{selectedAct.location || 'N/A'}</strong></span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Add Row Button */}
      <div className="mt-3">
        <button
          type="button"
          onClick={handleAddRow}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#FF7A18] hover:text-[#E06810] hover:underline"
        >
          <Plus className="w-4 h-4" />
          Add Activity Allocation
        </button>
      </div>

      {/* Total & Balance Summary */}
      <div className="mt-4 p-3.5 rounded-xl bg-card-subtle border border-border flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {isBalanced ? (
            <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 text-xs font-medium">
              <CheckCircle2 className="w-4 h-4" />
              <span>Balanced (Total: {currentSum}{isPctMode ? '%' : ` ${claim.claimed_uom || ''}`})</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400 text-xs font-medium">
              <AlertTriangle className="w-4 h-4" />
              <span>
                Unbalanced: Sum is {currentSum} / {targetTotal} (
                {remaining > 0 ? `${remaining} remaining` : `${Math.abs(remaining)} excess`}
                )
              </span>
            </div>
          )}
        </div>

        <div className="text-xs text-muted-foreground">
          Target: <strong className="text-foreground">{targetTotal}{isPctMode ? '%' : ''}</strong> | Allocated: <strong className={isBalanced ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}>{currentSum}{isPctMode ? '%' : ''}</strong>
        </div>
      </div>

      {/* Split Justification */}
      <div className="mt-4">
        <label className="block text-xs font-semibold text-foreground mb-1.5">
          Planner Justification for Split
        </label>
        <textarea
          rows={2}
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          placeholder="State the engineering rationale for splitting this claim across the above WBS items..."
          className="w-full text-xs rounded-lg border border-slate-300 dark:border-[#1E3A5F] bg-white dark:bg-[#0A2340] text-slate-900 dark:text-[#F5F7FA] px-3 py-2 focus:ring-2 focus:ring-[#FF7A18] focus:outline-hidden"
        />
      </div>

      {error && (
        <div className="mt-3 p-3 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-xs text-red-600 dark:text-red-400 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="mt-5 flex items-center justify-end gap-3 pt-4 border-t border-border">
        <button
          type="button"
          onClick={onCancel}
          disabled={submitting}
          className="px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-card-subtle rounded-lg transition-colors"
        >
          Cancel Split
        </button>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!isBalanced || submitting}
          className="inline-flex items-center gap-2 px-5 py-2 text-xs font-semibold text-white bg-gradient-to-r from-[#FF7A18] to-[#FF941F] hover:from-[#E06810] hover:to-[#FF7A18] disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow-sm shadow-orange-500/25 transition-all cursor-pointer"
        >
          {submitting ? (
            'Submitting Split...'
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Submit Split Allocation
              <ArrowRight className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};
