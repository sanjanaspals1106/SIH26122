/**
 * Setu AI (SIH26122) — Typed API Client & PRD Contracts
 *
 * Fully compliant with PRD v5 specification.
 * VITE_USE_MOCKS=true → returns realistic mock data (explicit demo mode)
 * Any other value or omission → calls real FastAPI endpoints at VITE_API_BASE_URL
 */

// Never silently substitute fabricated records for a real backend response.
// Mock mode must be explicitly opted into by a demo build.
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true';
export const IS_MOCK_MODE = USE_MOCKS;
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

interface ApiFetchOptions extends RequestInit {
  responseType?: 'json' | 'blob' | 'text';
}

async function apiFetch<T>(path: string, options?: ApiFetchOptions): Promise<T> {
  const token = localStorage.getItem('supabase_access_token') || localStorage.getItem('auth_token');
  const headers: Record<string, string> = {
    ...(options?.responseType !== 'blob' ? { 'Content-Type': 'application/json' } : {}),
    ...(options?.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errorText = await res.text().catch(() => 'Unknown network error');
    throw new Error(`API ${res.status}: ${errorText}`);
  }

  if (options?.responseType === 'blob') {
    return (await res.blob()) as unknown as T;
  }
  if (options?.responseType === 'text') {
    return (await res.text()) as unknown as T;
  }
  return res.json();
}

// ─── Canonical PRD Enums & Types ──────────────────────────────────────────────

export type UserRole = 'SITE_ENGINEER' | 'SUPERVISOR';

export type InputChannel =
  | 'FILE_UPLOAD'
  | 'SCANNED_OCR'
  | 'TYPED_TEXT'
  | 'VOICE'
  | 'SCHEDULE_EXPORT';

export type EventType =
  | 'ACTUAL_START'
  | 'ACTUAL_FINISH'
  | 'PROGRESS_UPDATE'
  | 'DELAY'
  | 'BLOCKER';

export type ClaimMode = 'CUMULATIVE_PCT' | 'INCREMENTAL_QUANTITY';

export type DecisionAction = 'APPROVE' | 'EDIT' | 'REJECT' | 'HOLD';

export type ClaimStatus =
  | 'EXTRACTED'
  | 'MATCHED'
  | 'UNMATCHED'
  | 'VALIDATED'
  | 'REVIEW_REQUIRED'
  | 'APPROVED'
  | 'EDITED'
  | 'REJECTED'
  | 'HOLD';

export type Discipline =
  | 'CIVIL'
  | 'PIPING'
  | 'STATIC_ROTATING_EQUIPMENT'
  | 'ELECTRICAL'
  | 'INSTRUMENTATION'
  | 'HSE';

export const DISCIPLINES: Discipline[] = [
  'CIVIL',
  'PIPING',
  'STATIC_ROTATING_EQUIPMENT',
  'ELECTRICAL',
  'INSTRUMENTATION',
  'HSE',
];

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
}

export type ClarificationStatus = 'NONE' | 'PENDING' | 'ANSWERED' | 'RESOLVED';

export interface ExecutionEvent {
  event_id: string;
  document_id: string | null;
  schedule_id: string;
  event_date: string; // YYYY-MM-DD
  raw_claim_text: string;
  input_channel: InputChannel;
  language_detected: string | null;
  reported_activity_id: string | null;
  matched_activity_id: string | null;
  discipline: Discipline | null;
  action: string | null;
  event_type: EventType | null;
  claim_mode: ClaimMode;
  asset_tag: string | null;
  location: string | null;
  claimed_quantity: number | null;
  claimed_uom: string | null;
  claimed_pct: number | null;
  delay_reason: string | null;
  supervisor_id: string | null;
  photo_path: string | null;
  status: ClaimStatus;
  created_at: string;
  clarification_status?: ClarificationStatus | null;
  clarification_question?: string | null;
  clarification_answer?: string | null;
  priority_score?: number | null;
  priority_reasons?: string[] | null;
  is_escalated?: boolean | null;
  priority_rank?: number | null;
  field_provenance?: Record<string, FieldProvenance | FieldProvenanceSource> | null;
}

export interface SourceReference {
  reference_id: string;
  event_id: string;
  file_name: string | null;
  sheet_name: string | null;
  row_cell_ref: string | null;
  message_id: string | null;
  raw_snippet: string;
}

export interface CandidateMatch {
  candidate_id: string;
  event_id: string;
  schedule_id: string;
  activity_id: string;
  rank_order: 1 | 2 | 3;
  match_tier: 'EXACT' | 'SEMANTIC' | 'FUZZY' | 'DISCIPLINE_LOCATION' | string | null;
  composite_confidence: number;
  semantic_score: number | null;
  fuzzy_score: number | null;
  location_score: number | null;
  discipline_score: number | null;
  supporting_signals: string | null;
  disqualifying_signals: string | null;
}

export interface ConflictRecord {
  conflict_id: string;
  schedule_id: string;
  activity_id: string;
  reporting_period: string;
  event_id_a: string;
  event_id_b: string;
  value_a: number;
  value_b: number;
  variance_pct: number;
  status: 'OPEN' | 'RESOLVED';
}

export interface ValidationIssue {
  issue_id: string;
  event_id: string;
  rule_code: string | null;
  severity: 'WARNING' | 'ERROR' | null;
  description: string;
}

export interface PlannerDecision {
  decision_id: string;
  event_id: string;
  selected_activity_id: string;
  action: DecisionAction;
  approved_pct: number | null;
  approved_qty: number | null;
  planner_id: string;
  justification: string;
  decided_at: string;
}

export interface ScheduleActivity {
  activity_id: string;
  schedule_id: string;
  activity_name: string;
  wbs_code: string | null;
  discipline: Discipline;
  location: string;
  asset_tag: string | null;
  planned_start: string;
  planned_finish: string;
  planned_quantity: number | null;
  uom: string | null;
  baseline_pct_complete: number;
}

export interface ScheduleDependency {
  dependency_id: string;
  schedule_id: string;
  predecessor_activity_id: string;
  successor_activity_id: string;
  relationship_type: 'FS' | 'SS' | 'FF' | 'SF';
}

export interface ImpactConstraintItem {
  predecessor_activity_id: string;
  successor_activity_id: string;
  relationship_type: string;
  lag_days: number;
  constraint_dimension: string;
  required_successor_start: string | null;
  required_successor_finish: string | null;
  baseline_successor_start: string | null;
  gross_delay_days: number;
  is_controlling: boolean;
  uncertainty: boolean;
  uncertainty_reason: string | null;
}

export interface ImpactEvaluationItem {
  successor_activity_id: string;
  activity_name: string;
  dependency_type: string;
  original_earliest_start: string;
  shifted_earliest_start: string;
  original_planned_finish: string;
  shifted_earliest_finish: string;
  propagation_depth: number;
  target_path: string[];
  execution_state: string;
  gross_delay_days: number;
  total_float: number | null;
  float_status: 'KNOWN' | 'UNKNOWN';
  absorbed_delay_days: number | null;
  net_delay_days: number | null;
  controlling_predecessor: string | null;
  controlling_relationship: string | null;
  uncertainty: boolean;
  classification: string;
  constraints_evaluated?: ImpactConstraintItem[];
}

export interface ImpactPreviewResult {
  activity_id: string;
  activity_name?: string;
  planned_start?: string;
  planned_finish?: string;
  shifted_finish?: string;
  schedule_id?: string;
  delay_days: number;
  propagation_depth_limit?: number;
  disclaimer: string;
  impacts: ImpactEvaluationItem[];
  successors: {
    successor_activity_id: string;
    activity_name: string;
    relationship_type: string;
    original_start: string;
    original_finish: string;
    shifted_start: string;
    shifted_finish: string;
    lag_days: number;
    depth?: number;
    net_delay_days?: number | null;
    execution_state?: string;
  }[];
}

// ─── Feature 30A: WBS Activity Explorer (read-only) ──────────────────────────

export interface WBSGroupActivity {
  activity_id: string;
  planned_quantity: number | null;
}

export interface WBSGroup {
  wbs_code: string;
  activities: WBSGroupActivity[];
}

export interface WBSTreeResponse {
  schedule_id: string;
  wbs_groups: WBSGroup[];
}

// ─── Feature 30: WBS Granularity Bridge (Split Editor) ──────────────────────

export type SplitBasis = 'EQUAL' | 'WBS_WEIGHTED' | 'MANUAL';

export interface WBSSplitItem {
  split_id?: string;
  event_id: string;
  activity_id: string;
  split_basis: SplitBasis;
  split_pct: number;
  allocated_quantity?: number | null;
  uom?: string | null;
  rationale?: string | null;
  created_at?: string;
}

export interface WBSSplitAllocation {
  activity_id: string;
  split_basis?: SplitBasis;
  split_pct?: number;
  allocated_pct?: number | null;
  allocated_quantity?: number | null;
  uom?: string | null;
  rationale?: string | null;
}

export interface WBSSplitRequest {
  event_id: string;
  schedule_id: string;
  allocations: WBSSplitAllocation[];
  justification?: string;
}

export interface WBSSplitResponse {
  event_id: string;
  status: string;
  created_decisions?: PlannerDecision[];
  splits?: WBSSplitItem[];
  message?: string;
}

// ─── Feature 31: Evidence Fusion & Knowledge Graph ──────────────────────────

export type EvidenceRelation = 'CORROBORATES' | 'CONTRADICTS' | 'SUPPORTING' | 'NEUTRAL';

export interface EvidenceDocument {
  evidence_id: string;
  event_id: string;
  document_type: string; // 'DAILY_REPORT' | 'INSPECTION_PHOTO' | 'SURVEY_LOG' | 'CAD_DWG' | string
  relation?: EvidenceRelation | string | null; // CORROBORATES vs CONTRADICTS
  file_name: string;
  page_or_cell_ref?: string | null;
  snippet_text?: string | null;
  ocr_confidence?: number | null;
  gps_lat?: number | null;
  gps_lon?: number | null;
  timestamp?: string | null;
  source_url?: string | null;
}

export interface KnowledgeGraphNode {
  id: string;
  label: string;
  type: 'CLAIM' | 'ACTIVITY' | 'WBS' | 'DOCUMENT' | 'LOCATION' | 'DISCIPLINE' | string;
  properties?: Record<string, any>;
}

export interface KnowledgeGraphEdge {
  source: string;
  target: string;
  relationship: string; // 'MATCHED_TO' | 'PART_OF_WBS' | 'EVIDENCED_BY' | 'LOCATED_AT' | string
  confidence?: number | null;
}

export interface KnowledgeGraphData {
  event_id: string;
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
}

// ─── Feature 33: Fine-Grained Field Provenance ───────────────────────────────

export type FieldProvenanceSource =
  | 'AI_EXTRACTED'
  | 'SCHEDULE_AUTO_FILLED'
  | 'ENGINEER_ENTERED'
  | 'SUPERVISOR_EDITED';

export interface FieldProvenance {
  field_name: string;
  source: FieldProvenanceSource;
  source_detail?: string | null;
  confidence?: number | null;
  timestamp?: string | null;
  actor?: string | null;
}

// ─── Feature 34: Ask Why (Graph Traversal & Explanation) ─────────────────────

export interface AskWhyEntity {
  name: string;
  type: string;
  role: string;
}

export interface AskWhyRequest {
  event_id?: string;
  activity_id?: string;
  depth?: number;
  question?: string;
}

export interface AskWhyResponse {
  activity_id?: string;
  event_id?: string;
  explanation: string;
  traversal_depth?: number | null;
  reasoning_steps?: string[] | null;
  entities_involved?: AskWhyEntity[] | null;
  evidence_references?: string[] | null;
}

// ─── Feature 35: AI Execution Summary ────────────────────────────────────────

export interface ExecutionSummaryFilter {
  language?: string; // display language (en/hi/te); canonical stored summary stays English
  start?: string;
  end?: string;
  start_date?: string; // backwards compatibility alias
  end_date?: string;   // backwards compatibility alias
  discipline?: Discipline | string;
  schedule_id?: string;
}

export interface ExecutionSummaryMetrics {
  total_claims_processed?: number;
  approval_rate_pct?: number;
  open_conflicts_count?: number;
  high_priority_escalations?: number;
  top_delay_drivers?: { reason: string; count: number }[];
  disciplines_active?: string[];
}

export interface ExecutionSummaryAggregate {
  period: { type: string; start: string; end: string };
  discipline: string;
  claims: {
    total_claims: number;
    by_status: Record<string, number>;
    by_event_type: Record<string, number>;
  };
  approved_progress: {
    total_approved: number;
    activities_with_actuals: number;
    avg_approved_pct: number;
  };
  conflicts: {
    total_conflicts: number;
    by_status: Record<string, number>;
  };
  validation_issues: {
    total_issues: number;
    by_severity: Record<string, number>;
  };
  delays: {
    total_delay_events: number;
    reasons: Record<string, number>;
  };
  activities: {
    total: number;
    completed: number;
    in_progress: number;
    not_started: number;
  };
  forecast: {
    status: string;
    historical_ratio: number | null;
    note?: string;
  };
}

export interface ExecutionSummaryResponse {
  period: { type: string; start: string; end: string };
  discipline: string;
  aggregate: ExecutionSummaryAggregate;
  canonical_summary: string;
  summary: string;
  language: string;
  cached: boolean;
  generated_by: 'llm' | 'deterministic_fallback';
}

export interface ExecutionReportResponse {
  reporting_period: {
    start_date: string;
    end_date: string;
  };
  discipline?: Discipline | string | null;
  schedule_id?: string | null;
  summary_text: string;
  metrics?: ExecutionSummaryMetrics | null;
  key_highlights?: string[] | null;
  generated_at: string;
}

export interface AuditLogEntry {
  log_id: number;
  entity_type: string;
  entity_id: string;
  action: string;
  actor_id: string;
  before_state: string | null;
  after_state: string | null;
  payload_hash: string;
  previous_hash: string;
  current_hash: string;
  timestamp: string;
}

export interface DisciplineForecastItem {
  activity_id: string;
  discipline: string;
  planned_duration: number | null;
  historical_ratio: number | null;
  forecast_duration: number | null;
  slippage_days: number;
}

export interface DisciplineForecastData {
  discipline: string;
  historical_ratio: number | null;
  activities: DisciplineForecastItem[];
  total_activities: number;
}

// ─── Realistic Demo Dataset ──────────────────────────────────────────────────

const TODAY = new Date().toISOString().split('T')[0];

const MOCK_EVENTS: ExecutionEvent[] = [
  {
    event_id: 'evt-101',
    document_id: 'doc-001',
    schedule_id: 'sched-OIL-2026',
    event_date: TODAY,
    raw_claim_text: 'Completed foundation pour F-4 in Block-4 North, 50 cu.m poured today.',
    input_channel: 'TYPED_TEXT',
    language_detected: 'en',
    reported_activity_id: 'ACT-201',
    matched_activity_id: 'ACT-201',
    discipline: 'CIVIL',
    action: 'PROGRESS_UPDATE',
    event_type: 'PROGRESS_UPDATE',
    claim_mode: 'INCREMENTAL_QUANTITY',
    asset_tag: 'FND-B4',
    location: 'Block-4 North',
    claimed_quantity: 50,
    claimed_uom: 'cu.m',
    claimed_pct: 100,
    delay_reason: null,
    supervisor_id: null,
    photo_path: '/uploads/f4_pour.jpg',
    status: 'VALIDATED',
    created_at: new Date().toISOString(),
  },
  {
    event_id: 'evt-102',
    document_id: 'doc-002',
    schedule_id: 'sched-OIL-2026',
    event_date: TODAY,
    raw_claim_text: 'Rebar placement for column C4, level B2 finished. 75% total progress claimed.',
    input_channel: 'VOICE',
    language_detected: 'en',
    reported_activity_id: 'ACT-202',
    matched_activity_id: 'ACT-202',
    discipline: 'CIVIL',
    action: 'PROGRESS_UPDATE',
    event_type: 'PROGRESS_UPDATE',
    claim_mode: 'CUMULATIVE_PCT',
    asset_tag: 'COL-C4',
    location: 'Block-2',
    claimed_quantity: null,
    claimed_uom: null,
    claimed_pct: 75,
    delay_reason: null,
    supervisor_id: null,
    photo_path: null,
    status: 'REVIEW_REQUIRED',
    created_at: new Date().toISOString(),
    priority_score: 0.88,
    priority_reasons: ['Critical Path activity', 'High variance risk with previous shift log'],
    is_escalated: true,
    priority_rank: 1,
    field_provenance: {
      discipline: { field_name: 'discipline', source: 'AI_EXTRACTED', source_detail: 'Extracted from voice keyword "Rebar placement"', confidence: 0.96 },
      location: { field_name: 'location', source: 'ENGINEER_ENTERED', source_detail: 'Explicit site engineer voice report: "Block-2"' },
      asset_tag: { field_name: 'asset_tag', source: 'SCHEDULE_AUTO_FILLED', source_detail: 'Resolved from activity master ACT-202 tag COL-C4' },
      claimed_pct: { field_name: 'claimed_pct', source: 'ENGINEER_ENTERED', source_detail: 'Stated directly in voice log (75%)' },
      matched_activity_id: { field_name: 'matched_activity_id', source: 'AI_EXTRACTED', source_detail: 'FAISS match on Column C4 with 88% confidence', confidence: 0.88 },
    },
  },
  {
    event_id: 'evt-103',
    document_id: null,
    schedule_id: 'sched-OIL-2026',
    event_date: TODAY,
    raw_claim_text: 'Completed 8 weld joints on 6" crude pipeline near Pump Skid PS-02.',
    input_channel: 'TYPED_TEXT',
    language_detected: 'en',
    reported_activity_id: 'ACT-301',
    matched_activity_id: 'ACT-301',
    discipline: 'PIPING',
    action: 'PROGRESS_UPDATE',
    event_type: 'PROGRESS_UPDATE',
    claim_mode: 'INCREMENTAL_QUANTITY',
    asset_tag: 'PUMP-002',
    location: 'Pump Station 2',
    claimed_quantity: 8,
    claimed_uom: 'joints',
    claimed_pct: 40,
    delay_reason: null,
    supervisor_id: null,
    photo_path: null,
    status: 'VALIDATED',
    created_at: new Date().toISOString(),
  },
  {
    event_id: 'evt-104',
    document_id: 'doc-004',
    schedule_id: 'sched-OIL-2026',
    event_date: TODAY,
    raw_claim_text: 'SCADA Panel E3 installation complete and powered up in control room.',
    input_channel: 'FILE_UPLOAD',
    language_detected: 'en',
    reported_activity_id: 'ACT-401',
    matched_activity_id: 'ACT-401',
    discipline: 'ELECTRICAL',
    action: 'ACTUAL_FINISH',
    event_type: 'ACTUAL_FINISH',
    claim_mode: 'CUMULATIVE_PCT',
    asset_tag: 'PANEL-E3',
    location: 'Unit E3 Control Room',
    claimed_quantity: null,
    claimed_uom: null,
    claimed_pct: 100,
    delay_reason: null,
    supervisor_id: null,
    photo_path: '/uploads/panel_e3.jpg',
    status: 'APPROVED',
    created_at: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    event_id: 'evt-105',
    document_id: null,
    schedule_id: 'sched-OIL-2026',
    event_date: TODAY,
    raw_claim_text: 'Loop testing for pressure transmitter IT-201 delayed due to missing calibration cert.',
    input_channel: 'TYPED_TEXT',
    language_detected: 'en',
    reported_activity_id: 'ACT-501',
    matched_activity_id: 'ACT-501',
    discipline: 'INSTRUMENTATION',
    action: 'DELAY',
    event_type: 'DELAY',
    claim_mode: 'CUMULATIVE_PCT',
    asset_tag: 'IT-201',
    location: 'Main Process Area',
    claimed_quantity: null,
    claimed_uom: null,
    claimed_pct: 10,
    delay_reason: 'Vendor missing calibration certificates for test bench',
    supervisor_id: null,
    photo_path: null,
    status: 'HOLD',
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    event_id: 'evt-106',
    document_id: null,
    schedule_id: 'sched-OIL-2026',
    event_date: TODAY,
    raw_claim_text: 'HSE Safety Audit in Zone A completed. 3 housekeeping non-conformances cleared.',
    input_channel: 'TYPED_TEXT',
    language_detected: 'en',
    reported_activity_id: 'ACT-601',
    matched_activity_id: 'ACT-601',
    discipline: 'HSE',
    action: 'PROGRESS_UPDATE',
    event_type: 'PROGRESS_UPDATE',
    claim_mode: 'CUMULATIVE_PCT',
    asset_tag: null,
    location: 'Zone A',
    claimed_quantity: null,
    claimed_uom: null,
    claimed_pct: 100,
    delay_reason: null,
    supervisor_id: null,
    photo_path: null,
    status: 'APPROVED',
    created_at: new Date(Date.now() - 5400000).toISOString(),
  },
];

const MOCK_CANDIDATES: CandidateMatch[] = [
  {
    candidate_id: 'cand-101',
    event_id: 'evt-102',
    schedule_id: 'sched-OIL-2026',
    activity_id: 'ACT-202',
    rank_order: 1,
    match_tier: 'EXACT',
    composite_confidence: 0.88,
    semantic_score: 0.92,
    fuzzy_score: 0.84,
    location_score: 0.95,
    discipline_score: 1.0,
    supporting_signals: 'Exact match on activity tag "C4"; matched discipline CIVIL; matching location Block-2',
    disqualifying_signals: null,
  },
  {
    candidate_id: 'cand-102',
    event_id: 'evt-102',
    schedule_id: 'sched-OIL-2026',
    activity_id: 'ACT-203',
    rank_order: 2,
    match_tier: 'SEMANTIC',
    composite_confidence: 0.54,
    semantic_score: 0.61,
    fuzzy_score: 0.50,
    location_score: 0.40,
    discipline_score: 1.0,
    supporting_signals: 'Semantic overlap on rebar reinforcement tokens',
    disqualifying_signals: 'Location mismatch (Block-3 instead of Block-2)',
  },
  {
    candidate_id: 'cand-103',
    event_id: 'evt-102',
    schedule_id: 'sched-OIL-2026',
    activity_id: 'ACT-204',
    rank_order: 3,
    match_tier: 'FUZZY',
    composite_confidence: 0.32,
    semantic_score: 0.35,
    fuzzy_score: 0.42,
    location_score: 0.30,
    discipline_score: 0.8,
    supporting_signals: 'Partial token match on "column"',
    disqualifying_signals: 'Low composite score below threshold',
  },
];

const MOCK_FLAGS: ValidationIssue[] = [
  {
    issue_id: 'flag-101',
    event_id: 'evt-102',
    rule_code: 'CONFIDENCE_THRESHOLD_UNMET',
    severity: 'WARNING',
    description: 'Top candidate confidence (0.88) is below automated auto-approval threshold (0.90). Supervisor review required.',
  },
  {
    issue_id: 'flag-102',
    event_id: 'evt-102',
    rule_code: 'QUANTITY_VARIANCE',
    severity: 'WARNING',
    description: 'Claimed progress (+15%) exceeds baseline planned daily rate of 8% for Column C4.',
  },
];

const MOCK_DECISIONS: PlannerDecision[] = [
  {
    decision_id: 'dec-101',
    event_id: 'evt-104',
    selected_activity_id: 'ACT-401',
    action: 'APPROVE',
    approved_pct: 100,
    approved_qty: null,
    planner_id: 'usr-supervisor-01',
    justification: 'Verified physical installation and pre-commissioning signoff certificate.',
    decided_at: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    decision_id: 'dec-102',
    event_id: 'evt-106',
    selected_activity_id: 'ACT-601',
    action: 'APPROVE',
    approved_pct: 100,
    approved_qty: null,
    planner_id: 'usr-supervisor-01',
    justification: 'HSE walkthrough report attached and validated by Lead HSE Inspector.',
    decided_at: new Date(Date.now() - 5400000).toISOString(),
  },
];

const MOCK_ACTIVITIES: ScheduleActivity[] = [
  {
    activity_id: 'ACT-201',
    schedule_id: 'sched-OIL-2026',
    activity_name: 'Foundation Concrete Pouring — Block 4',
    wbs_code: 'WBS-1.1.2',
    discipline: 'CIVIL',
    location: 'Block-4 North',
    asset_tag: 'FND-B4',
    planned_start: '2026-09-01',
    planned_finish: '2026-09-10',
    planned_quantity: 200,
    uom: 'cu.m',
    baseline_pct_complete: 40,
  },
  {
    activity_id: 'ACT-202',
    schedule_id: 'sched-OIL-2026',
    activity_name: 'Rebar Placement — Column C4',
    wbs_code: 'WBS-1.1.3',
    discipline: 'CIVIL',
    location: 'Block-2',
    asset_tag: 'COL-C4',
    planned_start: '2026-09-05',
    planned_finish: '2026-09-12',
    planned_quantity: 12,
    uom: 'MT',
    baseline_pct_complete: 60,
  },
  {
    activity_id: 'ACT-301',
    schedule_id: 'sched-OIL-2026',
    activity_name: 'Field Welding — 6" Crude Line L-1',
    wbs_code: 'WBS-2.1.1',
    discipline: 'PIPING',
    location: 'Pump Station 2',
    asset_tag: 'PUMP-002',
    planned_start: '2026-09-02',
    planned_finish: '2026-09-15',
    planned_quantity: 60,
    uom: 'joints',
    baseline_pct_complete: 30,
  },
  {
    activity_id: 'ACT-401',
    schedule_id: 'sched-OIL-2026',
    activity_name: 'SCADA Panel E3 Installation & Power Up',
    wbs_code: 'WBS-3.2.1',
    discipline: 'ELECTRICAL',
    location: 'Unit E3 Control Room',
    asset_tag: 'PANEL-E3',
    planned_start: '2026-09-01',
    planned_finish: '2026-09-08',
    planned_quantity: 1,
    uom: 'unit',
    baseline_pct_complete: 100,
  },
  {
    activity_id: 'ACT-501',
    schedule_id: 'sched-OIL-2026',
    activity_name: 'Loop Testing — Transmitter IT-201',
    wbs_code: 'WBS-4.1.2',
    discipline: 'INSTRUMENTATION',
    location: 'Main Process Area',
    asset_tag: 'IT-201',
    planned_start: '2026-09-08',
    planned_finish: '2026-09-14',
    planned_quantity: 10,
    uom: 'loops',
    baseline_pct_complete: 10,
  },
  {
    activity_id: 'ACT-601',
    schedule_id: 'sched-OIL-2026',
    activity_name: 'HSE Field Safety Compliance Walkthrough',
    wbs_code: 'WBS-5.1.1',
    discipline: 'HSE',
    location: 'Zone A',
    asset_tag: null,
    planned_start: '2026-09-08',
    planned_finish: '2026-09-08',
    planned_quantity: 1,
    uom: 'report',
    baseline_pct_complete: 100,
  },
];

const MOCK_AUDIT_LOGS: AuditLogEntry[] = [
  {
    log_id: 102,
    entity_type: 'execution_event',
    entity_id: 'evt-104',
    action: 'DECISION_APPROVE',
    actor_id: 'usr-supervisor-01',
    before_state: '{"status":"VALIDATED","claimed_pct":100}',
    after_state: '{"status":"APPROVED","approved_pct":100}',
    payload_hash: 'e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7',
    previous_hash: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b',
    current_hash: 'f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8',
    timestamp: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    log_id: 101,
    entity_type: 'execution_event',
    entity_id: 'evt-106',
    action: 'DECISION_APPROVE',
    actor_id: 'usr-supervisor-01',
    before_state: '{"status":"VALIDATED","claimed_pct":100}',
    after_state: '{"status":"APPROVED","approved_pct":100}',
    payload_hash: 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2',
    previous_hash: '0000000000000000000000000000000000000000000000000000000000000000',
    current_hash: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b',
    timestamp: new Date(Date.now() - 5400000).toISOString(),
  },
];

// ─── API Methods ─────────────────────────────────────────────────────────────

export const authApi = {
  getMe: async (hintEmail?: string): Promise<UserProfile> => {
    if (USE_MOCKS) {
      await sleep(200);
      const rawUser = localStorage.getItem('user');
      if (rawUser) {
        try {
          const parsed = JSON.parse(rawUser);
          if (parsed && parsed.role && parsed.id) return parsed;
        } catch {
          // ignore corrupted JSON
        }
      }
      const devEmail = hintEmail || localStorage.getItem('setu_dev_email_v1') || '';
      const isEngineer =
        devEmail.toLowerCase().includes('engineer') ||
        devEmail.toLowerCase().includes('site');

      if (isEngineer) {
        return {
          id: '811a1e0f-976d-42ea-a37f-1096186daf36',
          email: devEmail || 'site.engineer@sih26122.internal',
          full_name: 'Site Engineer',
          role: 'SITE_ENGINEER',
        };
      }
      return {
        id: '4b8e6901-de81-490c-8bec-9761f62bee70',
        email: devEmail || 'supervisor@sih26122.internal',
        full_name: 'Supervisor',
        role: 'SUPERVISOR',
      };
    }
    const data: any = await apiFetch('/api/v1/auth/me');
    return { ...data, email: data.email || '' };
  },
};

const MOCK_DYNAMIC_EVENTS = new Map<string, ExecutionEvent>();

function extractMockClaimFields(text: string): {
  discipline: Discipline | null;
  event_type: EventType;
  claimed_pct: number | null;
  claimed_quantity: number | null;
  claimed_uom: string | null;
  clarification_status: ClarificationStatus;
  clarification_question: string | null;
} {
  const lower = text.toLowerCase();

  // Discipline detection
  let discipline: Discipline | null = null;
  if (lower.includes('civil') || lower.includes('foundation') || lower.includes('rebar') || lower.includes('concrete') || lower.includes('column') || lower.includes('pour')) {
    discipline = 'CIVIL';
  } else if (lower.includes('piping') || lower.includes('pipe') || lower.includes('weld') || lower.includes('valve') || lower.includes('hydrotest')) {
    discipline = 'PIPING';
  } else if (lower.includes('electrical') || lower.includes('cable') || lower.includes('transformer') || lower.includes('panel') || lower.includes('switchgear')) {
    discipline = 'ELECTRICAL';
  } else if (lower.includes('instrument') || lower.includes('scada') || lower.includes('plc') || lower.includes('transmitter') || lower.includes('sensor')) {
    discipline = 'INSTRUMENTATION';
  } else if (lower.includes('equipment') || lower.includes('pump') || lower.includes('compressor') || lower.includes('turbine') || lower.includes('vessel')) {
    discipline = 'STATIC_ROTATING_EQUIPMENT';
  } else if (lower.includes('hse') || lower.includes('safety') || lower.includes('audit') || lower.includes('permit') || lower.includes('incident')) {
    discipline = 'HSE';
  }

  // Event Type detection
  let event_type: EventType = 'PROGRESS_UPDATE';
  if (lower.includes('finish') || lower.includes('complete') || lower.includes('done') || lower.includes('handed over')) {
    event_type = 'ACTUAL_FINISH';
  } else if (lower.includes('start') || lower.includes('commenced') || lower.includes('initiated')) {
    event_type = 'ACTUAL_START';
  } else if (lower.includes('delay') || lower.includes('behind') || lower.includes('waiting')) {
    event_type = 'DELAY';
  } else if (lower.includes('block') || lower.includes('stopped') || lower.includes('hold')) {
    event_type = 'BLOCKER';
  }

  // Progress/Quantity detection
  let claimed_pct: number | null = null;
  let claimed_quantity: number | null = null;
  let claimed_uom: string | null = null;

  const pctMatch = text.match(/(\d+(?:\.\d+)?)\s*%/);
  if (pctMatch) {
    claimed_pct = Math.min(100, Math.max(0, parseFloat(pctMatch[1])));
  } else if (event_type === 'ACTUAL_FINISH' && !lower.includes('gfdn')) {
    claimed_pct = 100;
  }

  const qtyMatch = text.match(/(\d+(?:\.\d+)?)\s*(cu\.m|m3|m|meters|joints|nos|tons|kg|units)/i);
  if (qtyMatch) {
    claimed_quantity = parseFloat(qtyMatch[1]);
    claimed_uom = qtyMatch[2];
  }

  // Feature 29: Required fields are event_type, discipline, and at least one of (claimed_pct, claimed_quantity)
  const hasDiscipline = discipline !== null;
  const hasProgress = claimed_pct !== null || claimed_quantity !== null;

  let clarification_status: ClarificationStatus = 'NONE';
  let clarification_question: string | null = null;

  if (!hasDiscipline && !hasProgress) {
    clarification_status = 'PENDING';
    clarification_question = 'Please clarify the engineering discipline (e.g. Civil, Piping, Electrical) and progress percentage or quantity for this activity.';
  } else if (!hasDiscipline) {
    clarification_status = 'PENDING';
    clarification_question = 'Please specify the engineering discipline (e.g. Civil, Piping, Electrical, Instrumentation, HSE) for this claim.';
  } else if (!hasProgress) {
    clarification_status = 'PENDING';
    clarification_question = 'Please provide the claimed progress percentage (0-100%) or installed quantity for this update.';
  }

  return {
    discipline,
    event_type,
    claimed_pct,
    claimed_quantity,
    claimed_uom,
    clarification_status,
    clarification_question,
  };
}

// ─── Backend → UI shape normalisation ────────────────────────────────────────
// The backend stores priority_reasons as newline-separated "[Tag] explanation" lines
// and scores are unbounded points (routine ≈ 5, critical-path sequence error ≥ 200).
// The UI works with a list of reasons, a rank and an escalation flag.
const ESCALATION_SCORE_THRESHOLD = 100; // >= one critical-severity issue (base 100) or worse

function normalizeEvent(raw: any, rank?: number): ExecutionEvent {
  if (!raw || typeof raw !== 'object') return raw;
  const reasons =
    typeof raw.priority_reasons === 'string'
      ? raw.priority_reasons
          .split('\n')
          .map((l: string) => l.replace(/^\[[^\]]+\]\s*/, '').trim())
          .filter(Boolean)
      : raw.priority_reasons ?? null;
  const score = raw.priority_score == null ? null : Number(raw.priority_score);
  return {
    ...raw,
    priority_score: score,
    priority_reasons: reasons,
    is_escalated: raw.is_escalated ?? (score != null ? score >= ESCALATION_SCORE_THRESHOLD : null),
    priority_rank: rank ?? raw.priority_rank ?? null,
  } as ExecutionEvent;
}

export const claimsApi = {
  submitText: async (text: string): Promise<{ event: ExecutionEvent }> => {
    if (USE_MOCKS) {
      await sleep(1000);
      const extracted = extractMockClaimFields(text);
      const ev: ExecutionEvent = {
        event_id: `evt-${Date.now()}`,
        document_id: null,
        schedule_id: 'sched-OIL-2026',
        event_date: TODAY,
        raw_claim_text: text,
        input_channel: 'TYPED_TEXT',
        language_detected: 'en',
        reported_activity_id: extracted.discipline === 'CIVIL' ? 'ACT-201' : null,
        matched_activity_id: null,
        discipline: extracted.discipline,
        action: extracted.event_type,
        event_type: extracted.event_type,
        claim_mode: extracted.claimed_quantity ? 'INCREMENTAL_QUANTITY' : 'CUMULATIVE_PCT',
        asset_tag: null,
        location: null,
        claimed_quantity: extracted.claimed_quantity,
        claimed_uom: extracted.claimed_uom,
        claimed_pct: extracted.claimed_pct,
        delay_reason: null,
        supervisor_id: null,
        photo_path: null,
        status: 'EXTRACTED',
        created_at: new Date().toISOString(),
        clarification_status: extracted.clarification_status,
        clarification_question: extracted.clarification_question,
      };
      MOCK_DYNAMIC_EVENTS.set(ev.event_id, ev);
      return { event: ev };
    }
    // Do NOT send schedule_id — let the backend resolve the latest active schedule.
    // Sending 'sched-OIL-2026' (the old hardcoded default) causes M3 to load
    // 0 activities and produce 0 candidates because that schedule doesn't exist.
    const data = await apiFetch('/api/v1/claims/text', {
      method: 'POST',
      body: JSON.stringify({ raw_claim_text: text, input_channel: 'TYPED_TEXT' }),
    });
    return { event: data as any };
  },

  // A single uploaded file (a multi-row daily report, a multi-sheet
  // spreadsheet, a P6 export, a multi-section scanned diary) commonly
  // describes several distinct activity claims, not one -- POST
  // /api/v1/claims/file returns one ClaimResponse per activity actually
  // found, so this returns `events`, not a single `event`.
  submitFile: async (
    file: File,
    options?: { purpose?: 'EVIDENCE_PHOTO' | 'SCANNED_DIARY'; rawClaimText?: string },
    scheduleId: string = 'sched-OIL-2026'
  ): Promise<{ events: ExecutionEvent[] }> => {
    if (USE_MOCKS) {
      await sleep(1500);
      const ev: ExecutionEvent = {
        event_id: `evt-${Date.now()}`,
        document_id: `doc-${Date.now()}`,
        schedule_id: scheduleId,
        event_date: TODAY,
        raw_claim_text: options?.rawClaimText || `Ingested update from file: ${file.name}`,
        input_channel: 'FILE_UPLOAD',
        language_detected: 'en',
        reported_activity_id: 'ACT-201',
        matched_activity_id: null,
        discipline: 'CIVIL',
        action: 'PROGRESS_UPDATE',
        event_type: 'PROGRESS_UPDATE',
        claim_mode: 'CUMULATIVE_PCT',
        asset_tag: null,
        location: null,
        claimed_quantity: null,
        claimed_uom: null,
        claimed_pct: 60,
        delay_reason: null,
        supervisor_id: null,
        photo_path: null,
        status: 'EXTRACTED',
        created_at: new Date().toISOString(),
        clarification_status: 'NONE',
        clarification_question: null,
      };
      MOCK_DYNAMIC_EVENTS.set(ev.event_id, ev);
      return { events: [ev] };
    }
    const form = new FormData();
    form.append('file', file);
    if (options?.purpose) form.append('purpose', options.purpose);
    if (options?.rawClaimText) form.append('raw_claim_text', options.rawClaimText);
    const token = localStorage.getItem('supabase_access_token') || localStorage.getItem('auth_token');
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${BASE_URL}/api/v1/claims/file`, {
      method: 'POST',
      headers,
      body: form,
    });
    if (!res.ok) throw new Error(await res.text().catch(() => 'File submit failed'));
    const data = await res.json();
    return { events: data as ExecutionEvent[] };
  },

  match: async (eventId: string): Promise<{ status: ClaimStatus; matches: CandidateMatch[] }> => {
    if (USE_MOCKS) {
      await sleep(1000);
      return { status: 'MATCHED', matches: MOCK_CANDIDATES };
    }
    const data: any = await apiFetch(`/api/v1/claims/${eventId}/match`, { method: 'POST' });
    return { status: data.status, matches: data.candidates || [] };
  },

  check: async (eventId: string): Promise<{ status: ClaimStatus; issues: ValidationIssue[] }> => {
    if (USE_MOCKS) {
      await sleep(800);
      return { status: 'REVIEW_REQUIRED', issues: MOCK_FLAGS };
    }
    const data: any = await apiFetch(`/api/v1/claims/${eventId}/check`, { method: 'POST' });
    return { status: data.status, issues: data.validation_issues || [] };
  },

  clarify: async (eventId: string, answer: string): Promise<{ event: ExecutionEvent }> => {
    if (USE_MOCKS) {
      await sleep(500);
      const ev = MOCK_DYNAMIC_EVENTS.get(eventId) || MOCK_EVENTS.find((e) => e.event_id === eventId) || {
        event_id: eventId,
        document_id: null,
        schedule_id: 'sched-OIL-2026',
        event_date: TODAY,
        raw_claim_text: 'Clarified claim',
        input_channel: 'TYPED_TEXT' as const,
        language_detected: 'en',
        reported_activity_id: 'ACT-201',
        matched_activity_id: null,
        discipline: 'CIVIL' as const,
        action: 'PROGRESS_UPDATE',
        event_type: 'PROGRESS_UPDATE' as const,
        claim_mode: 'CUMULATIVE_PCT' as const,
        asset_tag: null,
        location: null,
        claimed_quantity: null,
        claimed_uom: null,
        claimed_pct: 100,
        delay_reason: null,
        supervisor_id: null,
        photo_path: null,
        status: 'EXTRACTED' as const,
        created_at: new Date().toISOString(),
      };
      ev.clarification_status = 'ANSWERED';
      ev.clarification_answer = answer;
      ev.discipline = ev.discipline || 'CIVIL';
      ev.claimed_pct = ev.claimed_pct || 100;
      ev.status = 'EXTRACTED';
      MOCK_DYNAMIC_EVENTS.set(eventId, ev);
      return { event: { ...ev } };
    }
    const data = await apiFetch(`/api/v1/claims/${eventId}/clarify`, {
      method: 'POST',
      body: JSON.stringify({ clarification_answer: answer }),
    });
    return { event: data as any };
  },

  getCandidates: async (eventId: string): Promise<CandidateMatch[]> => {
    if (USE_MOCKS) {
      await sleep(300);
      return MOCK_CANDIDATES.filter((c) => c.event_id === eventId || eventId === 'evt-102');
    }
    const data: any = await apiFetch(`/api/v1/claims/${eventId}/candidates`);
    return data.candidates || [];
  },

  getConflicts: async (eventId: string): Promise<ConflictRecord[]> => {
    if (USE_MOCKS) {
      await sleep(300);
      return [
        {
          conflict_id: 'cnf-001',
          schedule_id: 'sched-OIL-2026',
          activity_id: 'ACT-202',
          reporting_period: TODAY,
          event_id_a: eventId,
          event_id_b: 'evt-previous-09',
          value_a: 75,
          value_b: 60,
          variance_pct: 25,
          status: 'OPEN',
        },
      ];
    }
    const data: any = await apiFetch(`/api/v1/claims/${eventId}/conflicts`);
    return data.conflicts || [];
  },

  getValidation: async (eventId: string): Promise<ValidationIssue[]> => {
    if (USE_MOCKS) {
      await sleep(300);
      return MOCK_FLAGS;
    }
    const data: any = await apiFetch(`/api/v1/claims/${eventId}/validation`);
    return data.validation_issues || [];
  },

  getEvidence: async (eventId: string): Promise<EvidenceDocument[]> => {
    if (USE_MOCKS) {
      await sleep(300);
      return [
        {
          evidence_id: 'ev-01',
          event_id: eventId,
          document_type: 'DAILY_REPORT',
          relation: 'CORROBORATES',
          file_name: 'Civil_Shift_Report_20260919.pdf',
          page_or_cell_ref: 'Page 3, Line 14',
          snippet_text: 'Level B2 rebar placement completed for column C4. 75% bar ties certified by QC.',
          ocr_confidence: 0.94,
          gps_lat: 28.6139,
          gps_lon: 77.209,
          timestamp: new Date(Date.now() - 3600000).toISOString(),
        },
        {
          evidence_id: 'ev-02',
          event_id: eventId,
          document_type: 'INSPECTION_PHOTO',
          relation: 'CORROBORATES',
          file_name: 'IMG_C4_Rebar_QC.jpg',
          page_or_cell_ref: 'Attachment 1',
          snippet_text: 'Site photo verifying rebar cage alignment and cover spacer blocks.',
          ocr_confidence: 0.98,
          gps_lat: 28.6141,
          gps_lon: 77.2093,
          timestamp: new Date(Date.now() - 1800000).toISOString(),
        },
      ];
    }
    const data: any = await apiFetch(`/api/v1/claims/${eventId}/evidence`);
    return data.evidence || data || [];
  },

  getKnowledgeGraph: async (eventId: string): Promise<KnowledgeGraphData> => {
    if (USE_MOCKS) {
      await sleep(400);
      return {
        event_id: eventId,
        nodes: [
          { id: 'node-claim', label: `Claim ${eventId}`, type: 'CLAIM' },
          { id: 'node-act', label: 'ACT-202 Rebar Placement', type: 'ACTIVITY' },
          { id: 'node-wbs', label: 'WBS 1.2 Substructure', type: 'WBS' },
          { id: 'node-doc', label: 'Civil_Shift_Report.pdf', type: 'DOCUMENT' },
          { id: 'node-loc', label: 'Block-2 Level B2', type: 'LOCATION' },
        ],
        edges: [
          { source: 'node-claim', target: 'node-act', relationship: 'MATCHED_TO', confidence: 0.88 },
          { source: 'node-act', target: 'node-wbs', relationship: 'PART_OF_WBS' },
          { source: 'node-claim', target: 'node-doc', relationship: 'EVIDENCED_BY', confidence: 0.94 },
          { source: 'node-claim', target: 'node-loc', relationship: 'LOCATED_AT' },
        ],
      };
    }
    const data: any = await apiFetch(`/api/v1/claims/${eventId}/knowledge-graph`);
    return data;
  },

  askWhy: async (request: AskWhyRequest): Promise<AskWhyResponse> => {
    const activityId = request.activity_id || 'ACT-202';
    const depth = request.depth ?? 2;

    if (USE_MOCKS) {
      await sleep(600);
      return {
        activity_id: activityId,
        event_id: request.event_id,
        explanation:
          `Matched to activity ${activityId} (Rebar Placement — Column C4) with 88% confidence based on spatial alignment in Block-2 and prerequisite foundation pour F-4 having completed.`,
        traversal_depth: depth,
        reasoning_steps: [
          'Extracted entity "Column C4" and location "Block-2" from voice transcript.',
          'Traversed WBS hierarchy: Schedule -> Substructure -> Foundations -> Column C4.',
          'Verified prerequisite foundation pour (FND-B4) cleared QC on prior reporting cycle.',
        ],
        entities_involved: [
          { name: activityId, type: 'ACTIVITY', role: 'Matched Schedule Package' },
          { name: 'Block-2', type: 'LOCATION', role: 'Spatial Constraint' },
          { name: 'FND-B4', type: 'PREDECESSOR', role: 'Verified Dependency' },
        ],
        evidence_references: [
          'Civil_Shift_Report_20260919.pdf (Page 3)',
          'IMG_C4_Rebar_QC.jpg (Attachment 1)',
        ],
      };
    }
    // Deterministic Ask Why over the knowledge graph (GET /api/v1/graph/activity/{id}?depth=N
    // returns the raw nodes/edges; /graph/explain adds the causal explanation from stored records).
    const qs = new URLSearchParams({ depth: String(depth) });
    if (request.event_id) qs.set('event_id', request.event_id);
    const data = await apiFetch(`/api/v1/graph/explain/${encodeURIComponent(activityId)}?${qs.toString()}`);
    return data as AskWhyResponse;
  },

  getReviewQueue: async (sort: string = 'priority'): Promise<ExecutionEvent[]> => {
    if (USE_MOCKS) {
      await sleep(400);
      return MOCK_EVENTS.filter(
        (c) => c.status === 'REVIEW_REQUIRED' || c.status === 'VALIDATED' || c.status === 'HOLD'
      );
    }
    // PRD endpoint: GET /api/v1/review-queue?sort=priority
    const data: any = await apiFetch(`/api/v1/review-queue?sort=${sort}`);
    const items: any[] = Array.isArray(data)
      ? data
      : data.items || data.review_queue || data.queue || data.claims || [];
    return items.map((it, i) => normalizeEvent(it, i + 1));
  },

  getEvent: async (eventId: string): Promise<ExecutionEvent> => {
    if (USE_MOCKS) {
      await sleep(300);
      return MOCK_EVENTS.find((e) => e.event_id === eventId) || MOCK_EVENTS[1];
    }
    return normalizeEvent(await apiFetch(`/api/v1/claims/${eventId}`));
  },
};

export const digestApi = {
  getByDate: async (dateStr: string): Promise<ExecutionEvent[]> => {
    if (USE_MOCKS) {
      await sleep(500);
      return MOCK_EVENTS;
    }
    const rows: any[] = await apiFetch(`/api/v1/digest?date=${dateStr}`);
    return rows.map((r) => normalizeEvent(r));
  },

  // No `date` param -> GET /api/v1/digest returns every claim regardless of
  // event_date (see backend/routers/decisions.py's get_digest). Used only
  // to resolve which date to default the Daily Digest view to -- claims
  // carry the date reported in the source document/text, not the date they
  // were uploaded, so "today" (the real calendar date) can easily have zero
  // claims even when plenty exist on whatever date the data actually spans.
  getAll: async (): Promise<ExecutionEvent[]> => {
    if (USE_MOCKS) {
      await sleep(500);
      return MOCK_EVENTS;
    }
    const rows: any[] = await apiFetch('/api/v1/digest');
    return rows.map((r) => normalizeEvent(r));
  },

  bulkApprove: async (eventIds: string[]): Promise<{ approved: string[]; failed: string[] }> => {
    if (USE_MOCKS) {
      await sleep(900);
      return { approved: eventIds, failed: [] };
    }
    const data: any = await apiFetch('/api/v1/digest/bulk-approve', {
      method: 'POST',
      body: JSON.stringify({ event_ids: eventIds }),
    });
    return { approved: data.approved || [], failed: (data.failed || []).map((f: any) => typeof f === 'string' ? f : f.event_id) };
  },
};

export const decisionsApi = {
  submit: async (payload: {
    event_id: string;
    selected_activity_id: string;
    action: DecisionAction;
    approved_pct?: number | null;
    approved_qty?: number | null;
    justification: string;
  }): Promise<PlannerDecision> => {
    if (USE_MOCKS) {
      await sleep(800);
      return {
        decision_id: `dec-${Date.now()}`,
        event_id: payload.event_id,
        selected_activity_id: payload.selected_activity_id,
        action: payload.action,
        approved_pct: payload.approved_pct ?? null,
        approved_qty: payload.approved_qty ?? null,
        planner_id: 'usr-supervisor-01',
        justification: payload.justification,
        decided_at: new Date().toISOString(),
      };
    }
    const data: any = await apiFetch('/api/v1/decisions', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return {
      decision_id: data.decision_id,
      event_id: data.event_id,
      selected_activity_id: data.selected_activity_id,
      action: data.action as DecisionAction,
      approved_pct: payload.approved_pct ?? null,
      approved_qty: payload.approved_qty ?? null,
      planner_id: '',
      justification: payload.justification,
      decided_at: new Date().toISOString(),
    };
  },

  getRecent: async (): Promise<PlannerDecision[]> => {
    if (USE_MOCKS) {
      await sleep(300);
      return MOCK_DECISIONS;
    }
    return apiFetch('/api/v1/decisions?limit=10');
  },
};

export const dashboardApi = {
  getSummary: async (): Promise<{
    total_claims: number;
    pending_review: number;
    actuals: number;
    conflicts: number;
    discipline_breakdown: { discipline: string; name: string; count: number; value: number }[];
  }> => {
    if (USE_MOCKS) {
      await sleep(300);
      return {
        total_claims: 148,
        pending_review: 14,
        actuals: 124,
        conflicts: 2,
        discipline_breakdown: [
          { discipline: 'CIVIL', name: 'CIVIL', count: 42, value: 42 },
          { discipline: 'PIPING', name: 'PIPING', count: 28, value: 28 },
          { discipline: 'ELECTRICAL', name: 'ELECTRICAL', count: 18, value: 18 },
          { discipline: 'INSTRUMENTATION', name: 'INSTRUMENTATION', count: 12, value: 12 },
          { discipline: 'HSE', name: 'HSE', count: 8, value: 8 },
        ],
      };
    }
    return apiFetch('/api/v1/dashboard/summary');
  },

  getDelayReasons: async (): Promise<{ reason: string; count: number }[]> => {

    if (USE_MOCKS) {
      await sleep(400);
      return [
        { reason: 'Material / Equipment Delivery Delay', count: 14 },
        { reason: 'Adverse Weather / Rain Shutdown', count: 8 },
        { reason: 'Subcontractor Manpower Shortage', count: 6 },
        { reason: 'Missing Engineering Drawings / RFC', count: 4 },
        { reason: 'Inspection Clearance Bottleneck', count: 3 },
      ];
    }
    const data: any = await apiFetch('/api/v1/dashboard/delay-reasons');
    return (data.delay_reasons || []).map((d: any) => ({ reason: d.delay_reason, count: d.count }));
  },

  getInstitutionalMemory: async (): Promise<{ topic: string; resolution: string; count: number }[]> => {
    if (USE_MOCKS) {
      await sleep(400);
      return [
        { topic: 'Block-4 Concrete Curing Time', resolution: 'Accelerate with rapid-hardening admixture when temperature drops below 15°C', count: 12 },
        { topic: 'Pump Station Skid Alignment', resolution: 'Require dual-laser alignment signoff before line welding', count: 9 },
        { topic: 'SCADA Panel Power-Up Protocol', resolution: 'Perform secondary ground check prior to energization', count: 5 },
      ];
    }
    const data: any = await apiFetch('/api/v1/dashboard/institutional-memory');
    return (data.activities || []).map((a: any) => ({ topic: a.activity_id + ' (' + a.discipline + ')', resolution: a.variance_days !== null ? (a.variance_days > 0 ? a.variance_days + ' days delayed' : Math.abs(a.variance_days) + ' days ahead') : 'No actuals yet', count: a.planned_duration || 0 }));
  },

  getForecast: async (discipline: string = 'CIVIL'): Promise<DisciplineForecastData> => {
    if (USE_MOCKS) {
      await sleep(400);
      return {
        discipline,
        historical_ratio: 1.15,
        total_activities: 3,
        activities: [
          { activity_id: 'ACT-101 (Foundation Completion)', discipline, planned_duration: 20, historical_ratio: 1.15, forecast_duration: 23, slippage_days: 3 },
          { activity_id: 'ACT-102 (Piping Hydrotest)', discipline, planned_duration: 25, historical_ratio: 1.15, forecast_duration: 29, slippage_days: 4 },
          { activity_id: 'ACT-103 (Substation Energization)', discipline, planned_duration: 30, historical_ratio: 1.15, forecast_duration: 35, slippage_days: 5 },
        ],
      };
    }
    const data: any = await apiFetch(`/api/v1/dashboard/forecast?discipline=${encodeURIComponent(discipline)}`);
    const activities = (data.activities || (data.activity_id ? [data] : [])).map((a: any) => ({
      activity_id: a.activity_id || 'Unknown',
      discipline: a.discipline || discipline,
      planned_duration: a.planned_duration,
      historical_ratio: a.historical_ratio,
      forecast_duration: a.forecast_duration,
      slippage_days: (a.forecast_duration != null && a.planned_duration != null) ? a.forecast_duration - a.planned_duration : 0,
    }));
    return {
      discipline: data.discipline || discipline,
      historical_ratio: data.historical_ratio ?? null,
      total_activities: data.total_activities || activities.length,
      activities,
    };
  },

  getSilentActivities: async (): Promise<ScheduleActivity[]> => {
    if (USE_MOCKS) {
      await sleep(400);
      return [
        {
          activity_id: 'ACT-301',
          schedule_id: 'sched-OIL-2026',
          activity_name: 'Field Welding — 6" Crude Line L-1',
          wbs_code: 'WBS-2.1.1',
          discipline: 'PIPING',
          location: 'Pump Station 2',
          asset_tag: 'PUMP-002',
          planned_start: '2026-09-02',
          planned_finish: '2026-09-15',
          planned_quantity: 60,
          uom: 'joints',
          baseline_pct_complete: 30,
        },
      ];
    }
    const data: any = await apiFetch('/api/v1/alerts/silent-activities');
    return (data.silent_activities || []).map((a: any) => ({ ...a, asset_tag: a.asset_tag || null, uom: a.uom || null, baseline_pct_complete: a.baseline_pct_complete || 0 }));
  },

  getExportCsvUrl: (): string => {
    return `${BASE_URL}/api/v1/export/csv`;
  },

  exportCsv: async (): Promise<Blob> => {
    if (USE_MOCKS) {
      await sleep(400);
      const csvContent = [
        'activity_id,actual_start,actual_finish,actual_pct_complete,actual_quantity',
        'ACT-101,2026-09-01,2026-09-10,100,500',
        'ACT-102,2026-09-03,2026-09-12,85,120',
        'ACT-103,2026-09-05,,45,30',
      ].join('\n');
      return new Blob([csvContent], { type: 'text/csv; charset=utf-8' });
    }
    return apiFetch<Blob>('/api/v1/export/csv', { responseType: 'blob' });
  },
};

export interface ActivityTimelineItem {
  type: 'execution_event' | 'planner_decision' | 'approved_actual';
  timestamp: string | null;
  event_id?: string;
  schedule_id?: string | null;
  event_date?: string | null;
  raw_claim_text?: string;
  claim_mode?: string;
  claimed_pct?: number | null;
  claimed_quantity?: number | null;
  delay_reason?: string | null;
  status?: string | null;
  source_references?: {
    reference_id: string;
    file_name: string | null;
    sheet_name: string | null;
    row_cell_ref: string | null;
    message_id: string | null;
    raw_snippet: string;
  }[];
  decision_id?: string;
  selected_activity_id?: string;
  action?: string;
  approved_pct?: number | null;
  approved_qty?: number | null;
  planner_id?: string | null;
  justification?: string;
  actual_id?: string;
  activity_id?: string;
  actual_start?: string | null;
  actual_finish?: string | null;
  actual_pct_complete?: number | null;
  actual_quantity?: number | null;
}

export const activitiesApi = {
  getHistory: async (activityId: string): Promise<{
    activity: ScheduleActivity | null;
    timeline: ActivityTimelineItem[];
    history: {
      timestamp: string;
      raw_claim_text: string;
      input_channel: InputChannel;
      claimed_pct: number | null;
      claimed_qty: number | null;
      status: ClaimStatus;
      supervisor_action: string | null;
      actor: string;
    }[];
  }> => {
    if (USE_MOCKS) {
      await sleep(500);
      const activity = MOCK_ACTIVITIES.find((a) => a.activity_id === activityId) || MOCK_ACTIVITIES[1];
      const mockTimeline: ActivityTimelineItem[] = [
        {
          type: 'execution_event',
          event_id: 'evt-102',
          schedule_id: 'sched-OIL-2026',
          event_date: '2026-09-02',
          raw_claim_text: 'Rebar placement for column C4, level B2 finished. 75% total progress claimed.',
          claim_mode: 'CUMULATIVE_PCT',
          claimed_pct: 75,
          claimed_quantity: null,
          delay_reason: null,
          status: 'REVIEW_REQUIRED',
          timestamp: '2026-09-02T10:15:00Z',
          source_references: [
            {
              reference_id: 'REF-001',
              file_name: 'DPR_2026-09-02.xlsx',
              sheet_name: 'Civil Works',
              row_cell_ref: 'Row 14',
              message_id: null,
              raw_snippet: 'Col C4 rebar cage tying complete to B2 level, inspection requested.',
            },
          ],
        },
        {
          type: 'planner_decision',
          decision_id: 'dec-102',
          event_id: 'evt-102',
          selected_activity_id: activityId,
          action: 'APPROVE',
          approved_pct: 75,
          approved_qty: null,
          planner_id: 'sup-01',
          justification: 'Verified against QA/QC bar-bending inspection sign-off.',
          timestamp: '2026-09-02T14:30:00Z',
        },
        {
          type: 'approved_actual',
          actual_id: 'actl-102',
          decision_id: 'dec-102',
          event_id: 'evt-102',
          schedule_id: 'sched-OIL-2026',
          activity_id: activityId,
          actual_start: '2026-08-28',
          actual_finish: '2026-09-02',
          actual_pct_complete: 75,
          actual_quantity: null,
          timestamp: '2026-09-02T14:30:05Z',
        },
      ];
      return {
        activity,
        timeline: mockTimeline,
        history: [
          {
            timestamp: new Date(Date.now() - 7200000).toISOString(),
            raw_claim_text: 'Rebar placement for column C4 finished to level B2',
            input_channel: 'VOICE',
            claimed_pct: 75,
            claimed_qty: null,
            status: 'REVIEW_REQUIRED',
            supervisor_action: 'PENDING',
            actor: 'Site Engineer (Voice Log)',
          },
          {
            timestamp: new Date(Date.now() - 86400000).toISOString(),
            raw_claim_text: 'Column C4 shuttering and tieing completed 50%',
            input_channel: 'TYPED_TEXT',
            claimed_pct: 50,
            claimed_qty: null,
            status: 'APPROVED',
            supervisor_action: 'APPROVE',
            actor: 'Rajesh Kumar (Lead Planner)',
          },
        ],
      };
    }
    const data: any = await apiFetch(`/api/v1/activities/${activityId}/history`);
    const timeline: ActivityTimelineItem[] = data.timeline || [];
    const eventItems = timeline.filter((t: any) => t.type === 'execution_event');
    const decisionItem = timeline.find((t: any) => t.type === 'planner_decision');

    const scheduleId = eventItems.find((ev: any) => ev.schedule_id)?.schedule_id;
    let activity: ScheduleActivity | null = null;
    if (scheduleId) {
      try {
        activity = await apiFetch<ScheduleActivity>(`/api/v1/schedules/${scheduleId}/activities/${activityId}`);
      } catch {
        activity = null;
      }
    }

    return {
      activity,
      timeline,
      history: eventItems.map((ev: any) => ({
        timestamp: ev.timestamp || ev.event_date || '',
        raw_claim_text: ev.raw_claim_text || '',
        input_channel: 'TYPED_TEXT' as InputChannel,
        claimed_pct: ev.claimed_pct,
        claimed_qty: ev.claimed_quantity,
        status: ev.status || 'EXTRACTED',
        supervisor_action: decisionItem?.action || null,
        actor: decisionItem?.planner_id || 'System',
      })),
    };
  },
};

// The schedule new claims are matched against (most recently created). Cached for the
// session; real mode only -- mock mode keeps its fixed mock schedule id.
let activeScheduleIdPromise: Promise<string> | null = null;
export function getActiveScheduleId(): Promise<string> {
  if (USE_MOCKS) return Promise.resolve('sched-OIL-2026');
  if (!activeScheduleIdPromise) {
    activeScheduleIdPromise = apiFetch<{ schedule_id: string }>('/api/v1/schedules/active')
      .then((s) => s.schedule_id)
      .catch((err) => {
        activeScheduleIdPromise = null; // retry next call
        throw err;
      });
  }
  return activeScheduleIdPromise;
}

export const graphApi = {
  getActivityGraph: async (activityId: string, depth = 1, scheduleId?: string): Promise<{ nodes: any[]; edges: any[] }> => {
    if (USE_MOCKS) {
      await sleep(300);
      return { nodes: [], edges: [] };
    }
    const sid = scheduleId ?? (await getActiveScheduleId().catch(() => undefined));
    const query = sid ? `?depth=${depth}&schedule_id=${sid}` : `?depth=${depth}`;
    return apiFetch<{ nodes: any[]; edges: any[] }>(`/api/v1/graph/activity/${activityId}${query}`);
  },
};

export const schedulesApi = {
  getActivities: async (scheduleId?: string): Promise<ScheduleActivity[]> => {
    if (USE_MOCKS) {
      await sleep(300);
      return MOCK_ACTIVITIES;
    }
    const sid = scheduleId ?? (await getActiveScheduleId());
    return apiFetch(`/api/v1/schedules/${sid}/activities`);
  },

  getImpactPreview: async (activityId: string, delayDays: number, scheduleId?: string): Promise<ImpactPreviewResult> => {
    if (USE_MOCKS) {
      await sleep(500);
      const activity = MOCK_ACTIVITIES.find((a) => a.activity_id === activityId) || MOCK_ACTIVITIES[0];
      const mockImpacts: ImpactEvaluationItem[] = [
        {
          successor_activity_id: 'ACT-202',
          activity_name: 'Rebar Placement — Column C4',
          dependency_type: 'FS',
          original_earliest_start: '2026-09-05',
          shifted_earliest_start: '2026-09-10',
          original_planned_finish: '2026-09-12',
          shifted_earliest_finish: '2026-09-15',
          propagation_depth: 1,
          target_path: [activity.activity_id, 'ACT-202'],
          execution_state: 'IN_PROGRESS',
          gross_delay_days: delayDays,
          total_float: 2,
          float_status: 'KNOWN',
          absorbed_delay_days: 2,
          net_delay_days: Math.max(0, delayDays - 2),
          controlling_predecessor: activity.activity_id,
          controlling_relationship: 'FS',
          uncertainty: false,
          classification: delayDays > 2 ? 'CRITICAL_PATH_SLIP' : 'ABSORBED_BY_FLOAT',
        },
        {
          successor_activity_id: 'ACT-301',
          activity_name: 'Field Welding — 6" Crude Line L-1',
          dependency_type: 'FS',
          original_earliest_start: '2026-09-12',
          shifted_earliest_start: '2026-09-15',
          original_planned_finish: '2026-09-25',
          shifted_earliest_finish: '2026-09-28',
          propagation_depth: 2,
          target_path: [activity.activity_id, 'ACT-202', 'ACT-301'],
          execution_state: 'NOT_STARTED',
          gross_delay_days: Math.max(0, delayDays - 2),
          total_float: 0,
          float_status: 'KNOWN',
          absorbed_delay_days: 0,
          net_delay_days: Math.max(0, delayDays - 2),
          controlling_predecessor: 'ACT-202',
          controlling_relationship: 'FS',
          uncertainty: false,
          classification: delayDays > 2 ? 'CRITICAL_PATH_SLIP' : 'NO_IMPACT',
        },
      ];

      return {
        activity_id: activity.activity_id,
        activity_name: activity.activity_name,
        planned_start: activity.planned_start,
        planned_finish: activity.planned_finish,
        shifted_finish: '2026-09-15',
        delay_days: delayDays,
        propagation_depth_limit: 5,
        disclaimer: 'Preview only · Deterministic A1 CPM Evaluation · Full Multi-Hop Propagation',
        impacts: mockImpacts,
        successors: mockImpacts.map((imp) => ({
          successor_activity_id: imp.successor_activity_id,
          activity_name: imp.activity_name,
          relationship_type: imp.dependency_type,
          original_start: imp.original_earliest_start,
          original_finish: imp.original_planned_finish,
          shifted_start: imp.shifted_earliest_start,
          shifted_finish: imp.shifted_earliest_finish,
          lag_days: 0,
          depth: imp.propagation_depth,
          net_delay_days: imp.net_delay_days,
          execution_state: imp.execution_state,
        })),
      };
    }
    const queryParams = new URLSearchParams({ delay_days: String(delayDays) });
    const impactScheduleId = scheduleId ?? (await getActiveScheduleId().catch(() => undefined));
    if (impactScheduleId) queryParams.set('schedule_id', impactScheduleId);
    const data: any = await apiFetch(`/api/v1/schedule/${encodeURIComponent(activityId)}/impact-preview?${queryParams.toString()}`);
    const impacts: ImpactEvaluationItem[] = (data.impacts || []).map((imp: any) => ({
      successor_activity_id: imp.successor_activity_id,
      activity_name: imp.activity_name || imp.successor_activity_id,
      dependency_type: imp.dependency_type || 'FS',
      original_earliest_start: imp.original_earliest_start || '',
      shifted_earliest_start: imp.shifted_earliest_start || '',
      original_planned_finish: imp.original_planned_finish || '',
      shifted_earliest_finish: imp.shifted_earliest_finish || '',
      propagation_depth: imp.propagation_depth || 1,
      target_path: imp.target_path || [data.activity_id, imp.successor_activity_id],
      execution_state: imp.execution_state || 'NOT_STARTED',
      gross_delay_days: imp.gross_delay_days || 0,
      total_float: imp.total_float ?? null,
      float_status: imp.float_status || 'UNKNOWN',
      absorbed_delay_days: imp.absorbed_delay_days ?? null,
      net_delay_days: imp.net_delay_days ?? null,
      controlling_predecessor: imp.controlling_predecessor ?? null,
      controlling_relationship: imp.controlling_relationship ?? null,
      uncertainty: Boolean(imp.uncertainty),
      classification: imp.classification || 'NO_IMPACT',
      constraints_evaluated: imp.constraints_evaluated || [],
    }));

    return {
      activity_id: data.activity_id,
      activity_name: data.activity_name || data.activity_id,
      planned_start: data.planned_start || '',
      planned_finish: data.planned_finish || '',
      shifted_finish: data.shifted_finish || '',
      schedule_id: data.schedule_id,
      delay_days: data.delay_days,
      propagation_depth_limit: data.propagation_depth_limit || 5,
      disclaimer: 'Preview only · Deterministic A1 CPM Evaluation · Multi-hop bounded propagation',
      impacts,
      successors: impacts.map((imp) => ({
        successor_activity_id: imp.successor_activity_id,
        activity_name: imp.activity_name,
        relationship_type: imp.dependency_type,
        original_start: imp.original_earliest_start,
        original_finish: imp.original_planned_finish,
        shifted_start: imp.shifted_earliest_start,
        shifted_finish: imp.shifted_earliest_finish,
        lag_days: 0,
        depth: imp.propagation_depth,
        net_delay_days: imp.net_delay_days,
        execution_state: imp.execution_state,
      })),
    };
  },

  getWbsTree: async (scheduleIdArg?: string): Promise<WBSTreeResponse> => {
    const scheduleId = scheduleIdArg ?? (await getActiveScheduleId().catch(() => 'sched-OIL-2026'));
    if (USE_MOCKS) {
      await sleep(400);
      // Group existing mock activities by wbs_code to mirror backend shape
      const groupMap = new Map<string, WBSGroupActivity[]>();
      for (const a of MOCK_ACTIVITIES) {
        if (!a.wbs_code) continue;
        const list = groupMap.get(a.wbs_code) || [];
        list.push({ activity_id: a.activity_id, planned_quantity: a.planned_quantity });
        groupMap.set(a.wbs_code, list);
      }
      const wbs_groups: WBSGroup[] = Array.from(groupMap.entries()).map(
        ([wbs_code, activities]) => ({ wbs_code, activities })
      );
      return { schedule_id: scheduleId, wbs_groups };
    }
    return apiFetch(`/api/v1/schedules/${scheduleId}/wbs-tree`);
  },
};

export const wbsApi = {
  getSplits: async (eventId: string): Promise<WBSSplitItem[]> => {
    if (USE_MOCKS) {
      await sleep(300);
      return [
        {
          split_id: `spl-${eventId}-1`,
          event_id: eventId,
          activity_id: 'ACT-202',
          split_basis: 'WBS_WEIGHTED',
          split_pct: 0.6,
          allocated_quantity: 45,
          uom: 'cu.m',
          rationale: 'Primary work package',
          created_at: new Date().toISOString(),
        },
        {
          split_id: `spl-${eventId}-2`,
          event_id: eventId,
          activity_id: 'ACT-203',
          split_basis: 'MANUAL',
          split_pct: 0.4,
          allocated_quantity: 30,
          uom: 'cu.m',
          rationale: 'Secondary tie-in / handover scope',
          created_at: new Date().toISOString(),
        },
      ];
    }
    // PRD endpoint: GET /api/v1/claims/{event_id}/splits -> { splits: [...] }; split_pct is a fraction (0-1)
    const data: any = await apiFetch(`/api/v1/claims/${eventId}/splits`);
    return Array.isArray(data) ? data : data.splits || [];
  },

  updateSplits: async (eventId: string, splits: Partial<WBSSplitItem>[]): Promise<WBSSplitResponse> => {
    if (USE_MOCKS) {
      await sleep(600);
      return {
        event_id: eventId,
        status: 'SPLIT_APPROVED',
        message: `Successfully updated ${splits.length} WBS split allocations.`,
      };
    }
    // PRD endpoint: PATCH /api/v1/claims/{event_id}/splits (Supervisor only).
    // Body: { splits: [{ activity_id, split_pct }] } with split_pct as a fraction that must sum to 1.
    return apiFetch(`/api/v1/claims/${eventId}/splits`, {
      method: 'PATCH',
      body: JSON.stringify({
        splits: splits.map((s) => ({ activity_id: s.activity_id, split_pct: s.split_pct })),
      }),
    });
  },

  splitClaim: async (request: WBSSplitRequest): Promise<WBSSplitResponse> => {
    if (USE_MOCKS) {
      await sleep(600);
      return {
        event_id: request.event_id,
        status: 'SPLIT_APPROVED',
        message: `Successfully allocated claim across ${request.allocations.length} WBS activities.`,
      };
    }
    return wbsApi.updateSplits(request.event_id, request.allocations as any);
  },

  getTree: async (scheduleId: string = 'sched-OIL-2026'): Promise<WBSTreeResponse> => {
    return schedulesApi.getWbsTree(scheduleId);
  },
};

export const auditApi = {
  getLogs: async (): Promise<AuditLogEntry[]> => {
    if (USE_MOCKS) {
      await sleep(400);
      return MOCK_AUDIT_LOGS;
    }
    return apiFetch('/api/v1/audit');
  },
};

export const reportsApi = {
  getExecutionSummary: async (filter?: ExecutionSummaryFilter): Promise<ExecutionReportResponse> => {
    const startDate = filter?.start || filter?.start_date;
    const endDate = filter?.end || filter?.end_date;

    if (USE_MOCKS) {
      await sleep(700);
      const todayStr = new Date().toISOString().split('T')[0];
      const pastWeekStr = new Date(Date.now() - 7 * 86400000).toISOString().split('T')[0];
      return {
        reporting_period: {
          start_date: startDate || pastWeekStr,
          end_date: endDate || todayStr,
        },
        discipline: filter?.discipline || null,
        schedule_id: filter?.schedule_id || 'sched-OIL-2026',
        summary_text:
          'During the current reporting cycle, 148 claims were processed across Civil, Piping, and Electrical disciplines. Foundation pours and structural column rebars met 94% of planned targets with minor delays in Pump Skid 02 tie-ins due to calibration certificate clearances. Critical path progression remains steady at 85% overall baseline alignment.',
        metrics: {
          total_claims_processed: 148,
          approval_rate_pct: 92.4,
          open_conflicts_count: 2,
          high_priority_escalations: 1,
          top_delay_drivers: [
            { reason: 'Calibration Certificate Delay', count: 4 },
            { reason: 'Adverse Rain Weather', count: 3 },
          ],
          disciplines_active: ['CIVIL', 'PIPING', 'ELECTRICAL', 'HSE'],
        },
        key_highlights: [
          'Foundation Pour F-4 in Block-4 North completed (50 cu.m).',
          'SCADA Panel E3 energization verified by lead electrical supervisor.',
          'Zero HSE safety non-conformances across Zone A audit.',
        ],
        generated_at: new Date().toISOString(),
      };
    }
    // PRD contract: GET /api/v1/reports/execution-summary?start=YYYY-MM-DD&end=YYYY-MM-DD&discipline=...
    const params = new URLSearchParams();
    if (startDate) params.append('start', startDate);
    if (endDate) params.append('end', endDate);
    if (filter?.discipline) params.append('discipline', filter.discipline);
    if (filter?.language) params.append('language', filter.language);

    const qs = params.toString();
    return apiFetch(`/api/v1/reports/execution-summary${qs ? `?${qs}` : ''}`);
  },
};

export interface InvestigationContext {
  root_activity_id: string;
  depth: number;
  context: {
    activity: Record<string, any>;
    execution_events: any[];
    validations: any[];
    conflicts: any[];
    impacts: any[];
    evidence: any[];
    decisions: any[];
    approved_actuals: any[];
    dependencies: any[];
  };
  summary: {
    conflict_status: string;
    validation_status: string;
    impact_status: string;
    evidence_status: string;
    approved_actual_status: string;
    dependencies_count: number;
    execution_events_count: number;
    decisions_count: number;
  };
  graph: {
    nodes: any[];
    edges: any[];
  };
}

export const investigationApi = {
  getInvestigation: async (activityId: string, depth = 1): Promise<InvestigationContext> => {
    if (USE_MOCKS) {
      await sleep(300);
      return {
        root_activity_id: activityId,
        depth,
        context: {
          activity: { activity_id: activityId, activity_name: 'Piping Section WLD-024', discipline: 'PIPING' },
          execution_events: [{ event_id: 'EVT-DEMO-01', raw_claim_text: 'Completed welding joints 1-4', delay_reason: null }],
          validations: [],
          conflicts: [],
          impacts: [],
          evidence: [{ reference_id: 'REF-01', file_name: 'inspection_log.pdf', raw_snippet: 'Visual test accepted' }],
          decisions: [],
          approved_actuals: [],
          dependencies: [],
        },
        summary: {
          conflict_status: 'not_present',
          validation_status: 'not_present',
          impact_status: 'not_present',
          evidence_status: 'present',
          approved_actual_status: 'not_present',
          dependencies_count: 0,
          execution_events_count: 1,
          decisions_count: 0,
        },
        graph: { nodes: [], edges: [] },
      };
    }
    return apiFetch<InvestigationContext>(`/api/v1/investigation/activity/${activityId}?depth=${depth}`);
  },
};

// Runtime translation of generated text for display (canonical text is never changed).
// Falls back to the original strings on any failure or in mock mode.
export const translateApi = {
  translate: async (texts: string[], targetLanguage: string): Promise<string[]> => {
    const lang = (targetLanguage || 'en').slice(0, 2);
    if (USE_MOCKS || lang === 'en' || texts.length === 0) return texts;
    try {
      const res: any = await apiFetch('/api/v1/reports/translate', {
        method: 'POST',
        body: JSON.stringify({ texts, target_language: lang }),
      });
      return Array.isArray(res?.texts) && res.texts.length === texts.length ? res.texts : texts;
    } catch {
      return texts;
    }
  },
};

export const executionSummaryApi = {
  getSummary: async (params?: {
    period?: 'last_7_days' | 'this_month' | 'custom';
    start_date?: string;
    end_date?: string;
    discipline?: string;
    language?: 'en' | 'hi' | 'te';
  }): Promise<ExecutionSummaryResponse> => {
    const query = new URLSearchParams();
    if (params?.period) query.set('period', params.period);
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    if (params?.discipline) query.set('discipline', params.discipline);
    if (params?.language) query.set('language', params.language);

    if (USE_MOCKS) {
      await sleep(350);
      const isHindi = params?.language === 'hi';
      const isTelugu = params?.language === 'te';
      const lang = params?.language || 'en';

      const canonical =
        "Project Execution Summary (Last 7 Days) — Scope comprises 32 scheduled activities (8 Completed, 16 In Progress, 8 Not Started). Field engineers reported 24 progress claims with 18 approved by the Supervisor (68.4% average completion). Quality controls recorded 2 open conflicts and 3 validation warnings. Four delay events were logged primarily driven by adverse monsoon rains (2) and structural steel delivery lead times (2).";

      let summaryText = canonical;
      if (isHindi) {
        summaryText =
          "परियोजना निष्पादन सारांश (पिछले 7 दिन) — दायरे में 32 निर्धारित गतिविधियाँ शामिल हैं (8 पूर्ण, 16 प्रगति पर, 8 प्रारंभ नहीं)। फील्ड इंजीनियरों ने 24 प्रगति दावे प्रस्तुत किए जिनमें से 18 पर्यवेक्षक द्वारा स्वीकृत हैं (68.4% औसत पूर्णता)। 2 खुले संघर्ष और 3 सत्यापन चेतावनियाँ दर्ज की गईं। प्रतिकूल मानसून बारिश (2) और स्टील वितरण (2) के कारण 4 विलंब कार्यक्रम नोट किए गए।";
      } else if (isTelugu) {
        summaryText =
          "ప్రాజెక్ట్ ఎగ్జిక్యూషన్ సారాంశం (గత 7 రోజులు) — పరిధిలో 32 షెడ్యూల్డ్ కార్యకలాపాలు ఉన్నాయి (8 పూర్తయ్యాయి, 16 పురోగతిలో ఉన్నాయి, 8 ప్రారంభం కాలేదు). ఫీల్డ్ ఇంజనీర్లు 24 ప్రోగ్రెస్ క్లెయిమ్‌లను సమర్పించగా, పర్యవేక్షకుడు 18 ఆమోదించారు (68.4% సగటు పూర్తి). 2 ఓపెన్ వివాదాలు మరియు 3 ధృవీకరణ హెచ్చరికలు నమోదయ్యాయి. ప్రతికూల వర్షాలు (2) మరియు ఉక్కు డెలివరీ (2) కారణంగా 4 ఆలస్య సంఘటనలు జరిగాయి.";
      }

      return {
        period: {
          type: params?.period || 'last_7_days',
          start: params?.start_date || '2026-09-11',
          end: params?.end_date || '2026-09-18',
        },
        discipline: params?.discipline || 'ALL',
        aggregate: {
          period: { type: params?.period || 'last_7_days', start: '2026-09-11', end: '2026-09-18' },
          discipline: params?.discipline || 'ALL',
          claims: { total_claims: 24, by_status: { APPROVED: 18, REVIEW_REQUIRED: 4, EXTRACTED: 2 }, by_event_type: { PROGRESS_UPDATE: 20, DELAY: 4 } },
          approved_progress: { total_approved: 18, activities_with_actuals: 14, avg_approved_pct: 68.4 },
          conflicts: { total_conflicts: 2, by_status: { OPEN: 2 } },
          validation_issues: { total_issues: 3, by_severity: { WARNING: 2, ERROR: 1 } },
          delays: { total_delay_events: 4, reasons: { WEATHER: 2, MATERIAL: 2 } },
          activities: { total: 32, completed: 8, in_progress: 16, not_started: 8 },
          forecast: { status: 'available', historical_ratio: 1.12 },
        },
        canonical_summary: canonical,
        summary: summaryText,
        language: lang,
        cached: false,
        generated_by: 'llm',
      };
    }
    return apiFetch<ExecutionSummaryResponse>(`/api/v1/execution-summary?${query.toString()}`);
  },
};

export { MOCK_EVENTS, MOCK_ACTIVITIES, MOCK_DECISIONS };
