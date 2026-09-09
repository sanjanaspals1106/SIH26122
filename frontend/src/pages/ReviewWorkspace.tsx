import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  claimsApi,
  decisionsApi,
  ExecutionEvent,
  CandidateMatch,
  ValidationIssue,
  ConflictRecord,
  DecisionAction,
} from '@/api';
import {
  FileText,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Sparkles,
  Check,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

export default function ReviewWorkspace() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const eventIdParam = searchParams.get('event_id');

  const [event, setEvent] = useState<ExecutionEvent | null>(null);
  const [candidates, setCandidates] = useState<CandidateMatch[]>([]);
  const [conflicts, setConflicts] = useState<ConflictRecord[]>([]);
  const [issues, setIssues] = useState<ValidationIssue[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Form State
  const [selectedActivityId, setSelectedActivityId] = useState<string>('');
  const [action, setAction] = useState<DecisionAction>('APPROVE');
  const [approvedPct, setApprovedPct] = useState<number | ''>('');
  const [approvedQty, setApprovedQty] = useState<number | ''>('');
  const [justification, setJustification] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [decisionSuccess, setDecisionSuccess] = useState<boolean>(false);

  const loadData = async (id: string) => {
    setIsLoading(true);
    setSubmitError(null);
    setDecisionSuccess(false);
    try {
      const [ev, cands, confs, valIssues] = await Promise.all([
        claimsApi.getEvent(id),
        claimsApi.getCandidates(id),
        claimsApi.getConflicts(id),
        claimsApi.getValidation(id),
      ]);
      setEvent(ev);
      setCandidates(cands);
      setConflicts(confs);
      setIssues(valIssues);

      const defaultActivity = cands[0]?.activity_id || ev.matched_activity_id || '';
      setSelectedActivityId(defaultActivity);
      setApprovedPct(ev.claimed_pct ?? 100);
      setApprovedQty(ev.claimed_quantity ?? '');
    } catch (err: any) {
      setSubmitError('Failed to load claim details: ' + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (eventIdParam) {
      loadData(eventIdParam);
    } else {
      setIsLoading(false);
    }
  }, [eventIdParam]);

  if (!eventIdParam) {
    return (
      <Card className="bg-white dark:bg-[#001E60] border-slate-200 dark:border-blue-900/60 text-center p-12 space-y-4">
        <CardTitle className="text-slate-900 dark:text-slate-100 text-lg font-bold">Select a Claim to Review</CardTitle>
        <p className="text-slate-500 dark:text-slate-400 text-xs max-w-md mx-auto">
          Please select a specific field progress claim from the Daily Digest or Intake Pipeline to inspect candidate matches and record supervisor approval decisions.
        </p>
        <Button onClick={() => navigate('/digest')} className="bg-[#FC4C02] hover:bg-[#e04302] text-white text-xs font-semibold">
          Go to Daily Digest & Claims Log
        </Button>
      </Card>
    );
  }

  const handleSubmitDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (!justification.trim()) {
      setSubmitError('Mandatory justification is required for all supervisor decisions.');
      return;
    }
    if (!selectedActivityId) {
      setSubmitError('Please select a Primavera/MSP schedule activity.');
      return;
    }

    setIsSubmitting(true);
    try {
      await decisionsApi.submit({
        event_id: eventIdParam,
        selected_activity_id: selectedActivityId,
        action,
        approved_pct: approvedPct !== '' ? Number(approvedPct) : null,
        approved_qty: approvedQty !== '' ? Number(approvedQty) : null,
        justification: justification.trim(),
      });
      setDecisionSuccess(true);
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to record supervisor decision');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-6xl mx-auto py-8">
        <div className="h-10 w-64 bg-slate-200 dark:bg-[#001E60] rounded-xl animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="h-96 bg-slate-200 dark:bg-[#001E60] rounded-2xl animate-pulse lg:col-span-2" />
          <div className="h-96 bg-slate-200 dark:bg-[#001E60] rounded-2xl animate-pulse" />
        </div>
      </div>
    );
  }

  if (!event) {
    return (
      <Card className="bg-white dark:bg-[#001E60] border-slate-200 dark:border-blue-900/60 text-center p-12">
        <CardTitle className="text-slate-900 dark:text-slate-100">Claim Event Not Found</CardTitle>
        <Button onClick={() => navigate('/digest')} className="mt-4 bg-[#FC4C02] text-white">Return to Daily Digest</Button>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-blue-900/50 pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-[#FC4C02] font-bold">
            <span>CLAIM ID: {event.event_id}</span>
            <span>·</span>
            <span>DATE: {event.event_date}</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight mt-0.5">
            Supervisor Review & Human Approval Workspace
          </h1>
        </div>

        <Button
          variant="outline"
          onClick={() => navigate('/digest')}
          className="bg-white dark:bg-[#001E60] border-slate-300 dark:border-blue-800 text-slate-700 dark:text-slate-200 text-xs h-9"
        >
          Back to Digest
        </Button>
      </div>

      {/* 4-Step Pipeline Flow Bar */}
      <div className="grid grid-cols-4 gap-2 text-center text-xs">
        <div className="p-3 rounded-xl bg-white dark:bg-[#001E60] border border-slate-200 dark:border-blue-800 text-slate-700 dark:text-slate-200 font-bold flex items-center justify-center gap-1.5 shadow-sm">
          <FileText className="w-4 h-4 text-blue-500" /> 1. Field Claim
        </div>
        <div className="p-3 rounded-xl bg-white dark:bg-[#001E60] border border-purple-500/40 text-purple-700 dark:text-purple-300 font-bold flex items-center justify-center gap-1.5 shadow-sm">
          <Sparkles className="w-4 h-4 text-purple-500" /> 2. AI Match Tier
        </div>
        <div className="p-3 rounded-xl bg-white dark:bg-[#001E60] border border-amber-500/40 text-amber-700 dark:text-amber-300 font-bold flex items-center justify-center gap-1.5 shadow-sm">
          <ShieldAlert className="w-4 h-4 text-amber-500" /> 3. Checks
        </div>
        <div className="p-3 rounded-xl bg-[#FC4C02] text-white font-bold flex items-center justify-center gap-1.5 shadow-md">
          <CheckCircle2 className="w-4 h-4" /> 4. Human Decision
        </div>
      </div>

      {decisionSuccess && (
        <div className="p-6 rounded-2xl bg-emerald-500/15 border border-emerald-500/40 text-emerald-900 dark:text-emerald-200 space-y-3">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-6 h-6 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <div>
              <h3 className="font-bold text-base">Supervisor Decision Committed</h3>
              <p className="text-xs text-emerald-800 dark:text-emerald-300">
                Claim <span className="font-mono font-bold text-emerald-950 dark:text-white">{event.event_id}</span> action <span className="font-mono font-bold uppercase text-emerald-950 dark:text-white">{action}</span> has been logged to the immutable audit trail.
              </p>
            </div>
          </div>
          <div className="flex gap-2 pt-2">
            <Button size="sm" onClick={() => navigate('/digest')} className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs">
              Return to Daily Digest
            </Button>
          </div>
        </div>
      )}

      {/* Main 3-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: Field Claim Provenance */}
        <div className="lg:col-span-4 space-y-6">
          <Card className="bg-white dark:bg-[#001E60] border-slate-200 dark:border-blue-900/60 shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-100 dark:border-blue-900/40">
              <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-900 dark:text-slate-100">
                <FileText className="w-4 h-4 text-blue-500" />
                Original Field Claim Provenance
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4 text-xs">
              <div className="p-3 bg-slate-50 dark:bg-[#001438] rounded-xl border border-slate-200 dark:border-blue-900/60 font-semibold text-slate-900 dark:text-slate-100 leading-relaxed">
                "{event.raw_claim_text}"
              </div>

              <div className="grid grid-cols-2 gap-3 text-slate-600 dark:text-slate-400">
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Discipline</span>
                  <span className="font-mono text-slate-900 dark:text-slate-100 font-bold">{event.discipline || 'UNASSIGNED'}</span>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Channel</span>
                  <span className="font-mono text-[#FC4C02] font-bold">{event.input_channel}</span>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Claim Mode</span>
                  <span className="font-mono text-slate-900 dark:text-slate-100">{event.claim_mode}</span>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Event Type</span>
                  <span className="font-mono text-slate-900 dark:text-slate-100">{event.event_type}</span>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Location</span>
                  <span className="text-slate-900 dark:text-slate-100">{event.location || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Asset Tag</span>
                  <span className="font-mono text-slate-900 dark:text-slate-100">{event.asset_tag || 'N/A'}</span>
                </div>
              </div>

              {event.delay_reason && (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-300 space-y-1">
                  <span className="font-bold text-[10px] uppercase block text-amber-600 dark:text-amber-400">Stated Delay Reason</span>
                  <p className="text-xs">{event.delay_reason}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Validation & Conflict Checks */}
          <Card className="bg-white dark:bg-[#001E60] border-slate-200 dark:border-blue-900/60 shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-100 dark:border-blue-900/40">
              <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-900 dark:text-slate-100">
                <ShieldAlert className="w-4 h-4 text-amber-500" />
                Automated Validation & Conflicts
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-3 text-xs">
              {issues.length === 0 && conflicts.length === 0 ? (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-800 dark:text-emerald-300 rounded-xl flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  <span>No automated rule warnings or quantity conflicts detected.</span>
                </div>
              ) : (
                <>
                  {issues.map((iss) => (
                    <div key={iss.issue_id} className="p-3 bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-300 rounded-xl space-y-1">
                      <div className="font-bold text-[10px] uppercase flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                        {iss.rule_code || 'RULE_WARNING'}
                      </div>
                      <p className="text-xs">{iss.description}</p>
                    </div>
                  ))}

                  {conflicts.map((cnf) => (
                    <div key={cnf.conflict_id} className="p-3 bg-rose-500/10 border border-rose-500/30 text-rose-800 dark:text-rose-300 rounded-xl space-y-1">
                      <div className="font-bold text-[10px] uppercase flex items-center gap-1.5 text-rose-600 dark:text-rose-400">
                        <ShieldAlert className="w-3.5 h-3.5" />
                        DUPLICATE CLAIM ({cnf.variance_pct}% variance)
                      </div>
                      <p className="text-xs">
                        Conflicting event <span className="font-mono font-bold">{cnf.event_id_b}</span> reported value {cnf.value_b} vs current claim {cnf.value_a}.
                      </p>
                    </div>
                  ))}
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* MIDDLE COLUMN: Top 3 AI Matches */}
        <div className="lg:col-span-4 space-y-6">
          <Card className="bg-white dark:bg-[#001E60] border-slate-200 dark:border-blue-900/60 shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-100 dark:border-blue-900/40">
              <CardTitle className="text-sm font-semibold flex items-center justify-between text-slate-900 dark:text-slate-100">
                <span className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-500" />
                  Top-3 AI Candidate Matches
                </span>
                <span className="text-[10px] bg-purple-500/10 text-purple-700 dark:text-purple-300 border border-purple-500/30 px-2 py-0.5 rounded-full font-mono font-bold">
                  FAISS Matching
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-3">
              {candidates.map((cand) => {
                const isSelected = selectedActivityId === cand.activity_id;
                const confidencePct = Math.round(cand.composite_confidence * 100);

                return (
                  <div
                    key={cand.candidate_id}
                    onClick={() => setSelectedActivityId(cand.activity_id)}
                    className={cn(
                      'p-4 rounded-xl border transition-all cursor-pointer relative space-y-2.5 shadow-sm',
                      isSelected
                        ? 'bg-purple-500/10 dark:bg-purple-950/40 border-purple-500 font-semibold'
                        : 'bg-slate-50 dark:bg-[#001438] border-slate-200 dark:border-blue-900/60 hover:border-purple-400'
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-bold bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-2 py-0.5 rounded-md font-mono">
                          #{cand.rank_order}
                        </span>
                        <span className="font-mono font-bold text-sm text-slate-900 dark:text-slate-100">{cand.activity_id}</span>
                        {cand.match_tier && (
                          <span className="text-[10px] font-bold bg-purple-500/10 text-purple-700 dark:text-purple-300 border border-purple-500/30 px-1.5 py-0.5 rounded font-mono uppercase">
                            {cand.match_tier}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-1.5">
                        <span className="text-[11px] font-bold font-mono text-purple-600 dark:text-purple-300">{confidencePct}% ({cand.composite_confidence.toFixed(2)})</span>
                        {isSelected && <Check className="w-4 h-4 text-purple-600 dark:text-purple-400" />}
                      </div>
                    </div>

                    <div className="grid grid-cols-4 gap-1 text-[10px] font-mono text-slate-500 dark:text-slate-400 pt-1 border-t border-slate-200 dark:border-blue-900/40">
                      <div>Sem: <span className="font-bold">{Math.round((cand.semantic_score || 0) * 100)}%</span></div>
                      <div>Fuz: <span className="font-bold">{Math.round((cand.fuzzy_score || 0) * 100)}%</span></div>
                      <div>Loc: <span className="font-bold">{Math.round((cand.location_score || 0) * 100)}%</span></div>
                      <div>Dis: <span className="font-bold">{Math.round((cand.discipline_score || 0) * 100)}%</span></div>
                    </div>

                    {cand.supporting_signals && (
                      <p className="text-[11px] text-emerald-600 dark:text-emerald-400 leading-tight">
                        ✓ {cand.supporting_signals}
                      </p>
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </div>

        {/* RIGHT COLUMN: Human Supervisor Action Form */}
        <div className="lg:col-span-4 space-y-6">
          <Card className="bg-white dark:bg-[#001E60] border-2 border-[#FC4C02]/60 shadow-lg">
            <CardHeader className="pb-3 border-b border-slate-100 dark:border-blue-900/50">
              <CardTitle className="text-sm font-bold flex items-center gap-2 text-slate-900 dark:text-white">
                <CheckCircle2 className="w-4 h-4 text-[#FC4C02]" />
                Human Supervisor Decision
              </CardTitle>
              <CardDescription className="text-slate-500 dark:text-blue-200/80 text-xs">
                Official approval requires mandatory planner justification.
              </CardDescription>
            </CardHeader>

            <CardContent className="pt-4 space-y-4">
              {submitError && (
                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs">
                  {submitError}
                </div>
              )}

              <form onSubmit={handleSubmitDecision} className="space-y-4 text-xs">
                <div className="space-y-1.5">
                  <Label className="text-xs text-slate-700 dark:text-slate-200 font-bold">Selected Primavera Activity</Label>
                  <Input
                    value={selectedActivityId}
                    onChange={(e) => setSelectedActivityId(e.target.value)}
                    className="bg-slate-50 dark:bg-[#001438] border-slate-300 dark:border-blue-800 font-mono text-[#FC4C02] font-bold text-sm h-9 rounded-xl"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs text-slate-700 dark:text-slate-200 font-bold">Action Type</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {(['APPROVE', 'EDIT', 'HOLD', 'REJECT'] as DecisionAction[]).map((act) => (
                      <button
                        key={act}
                        type="button"
                        onClick={() => setAction(act)}
                        className={cn(
                          'p-2.5 rounded-xl border text-xs font-bold transition-all text-center uppercase tracking-wider',
                          action === act
                            ? act === 'APPROVE'
                              ? 'bg-emerald-600 border-emerald-500 text-white shadow-md'
                              : act === 'EDIT'
                              ? 'bg-[#FC4C02] border-[#FC4C02] text-white shadow-md'
                              : act === 'HOLD'
                              ? 'bg-amber-600 border-amber-500 text-white shadow-md'
                              : 'bg-rose-600 border-rose-500 text-white shadow-md'
                            : 'bg-slate-50 dark:bg-[#001438] border-slate-200 dark:border-blue-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-blue-950'
                        )}
                      >
                        {act}
                      </button>
                    ))}
                  </div>
                </div>

                {action === 'EDIT' && (
                  <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 dark:bg-[#001438] rounded-xl border border-slate-200 dark:border-blue-800">
                    <div className="space-y-1">
                      <Label className="text-[11px] text-slate-600 dark:text-slate-400">Approved %</Label>
                      <Input
                        type="number"
                        value={approvedPct}
                        onChange={(e) => setApprovedPct(e.target.value !== '' ? Number(e.target.value) : '')}
                        className="bg-white dark:bg-[#001E60] border-slate-300 dark:border-blue-700 text-slate-900 dark:text-slate-100 font-mono h-8"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-[11px] text-slate-600 dark:text-slate-400">Approved Qty</Label>
                      <Input
                        type="number"
                        value={approvedQty}
                        onChange={(e) => setApprovedQty(e.target.value !== '' ? Number(e.target.value) : '')}
                        className="bg-white dark:bg-[#001E60] border-slate-300 dark:border-blue-700 text-slate-900 dark:text-slate-100 font-mono h-8"
                      />
                    </div>
                  </div>
                )}

                <div className="space-y-1.5">
                  <Label className="text-xs text-slate-700 dark:text-slate-200 font-bold flex items-center justify-between">
                    <span>Supervisor Justification</span>
                    <span className="text-[10px] text-rose-500 uppercase font-bold">Mandatory</span>
                  </Label>
                  <Textarea
                    rows={4}
                    placeholder="Enter reason for approval/edit/rejection..."
                    value={justification}
                    onChange={(e) => setJustification(e.target.value)}
                    className="bg-slate-50 dark:bg-[#001438] border-slate-300 dark:border-blue-800 text-slate-900 dark:text-slate-100 text-xs rounded-xl"
                  />
                </div>

                <Button
                  type="submit"
                  disabled={isSubmitting || decisionSuccess}
                  className="w-full bg-[#FC4C02] hover:bg-[#e04302] text-white font-bold h-10 shadow-lg shadow-[#FC4C02]/25 rounded-xl"
                >
                  {isSubmitting ? 'Recording Decision...' : 'Commit Official Decision'}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
