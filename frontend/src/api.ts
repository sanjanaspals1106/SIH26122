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

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('supabase_access_token') || localStorage.getItem('auth_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
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

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
}

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

export interface ImpactPreviewResult {
  activity_id: string;
  delay_days: number;
  disclaimer: string;
  successors: {
    successor_activity_id: string;
    activity_name: string;
    relationship_type: string;
    original_start: string;
    original_finish: string;
    shifted_start: string;
    shifted_finish: string;
    lag_days: number;
  }[];
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
  getMe: async (): Promise<UserProfile> => {
    if (USE_MOCKS) {
      await sleep(200);
      const rawUser = localStorage.getItem('user');
      if (rawUser) return JSON.parse(rawUser);
      return {
        id: 'usr-supervisor-01',
        email: 'planner@setu.ai',
        full_name: 'Rajesh Kumar (Lead Planner)',
        role: 'SUPERVISOR',
      };
    }
    const data: any = await apiFetch('/api/v1/auth/me');
    return { ...data, email: data.email || '' };
  },
};

export const claimsApi = {
  submitText: async (text: string): Promise<{ event: ExecutionEvent }> => {
    if (USE_MOCKS) {
      await sleep(1000);
      const ev: ExecutionEvent = {
        event_id: `evt-${Date.now()}`,
        document_id: null,
        schedule_id: 'sched-MOCK',
        event_date: TODAY,
        raw_claim_text: text,
        input_channel: 'TYPED_TEXT',
        language_detected: 'en',
        reported_activity_id: null,
        matched_activity_id: null,
        discipline: null,
        action: 'PROGRESS_UPDATE',
        event_type: 'PROGRESS_UPDATE',
        claim_mode: 'CUMULATIVE_PCT',
        asset_tag: null,
        location: null,
        claimed_quantity: null,
        claimed_uom: null,
        claimed_pct: 50,
        delay_reason: null,
        supervisor_id: null,
        photo_path: null,
        status: 'EXTRACTED',
        created_at: new Date().toISOString(),
      };
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
        raw_claim_text: `Ingested update from file: ${file.name}`,
        input_channel: 'FILE_UPLOAD',
        language_detected: 'en',
        reported_activity_id: null,
        matched_activity_id: null,
        discipline: null,
        action: 'PROGRESS_UPDATE',
        event_type: 'PROGRESS_UPDATE',
        claim_mode: 'CUMULATIVE_PCT',
        asset_tag: null,
        location: null,
        claimed_quantity: null,
        claimed_uom: null,
        claimed_pct: null,
        delay_reason: null,
        supervisor_id: null,
        photo_path: null,
        status: 'EXTRACTED',
        created_at: new Date().toISOString(),
      };
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

  getEvent: async (eventId: string): Promise<ExecutionEvent> => {
    if (USE_MOCKS) {
      await sleep(300);
      return MOCK_EVENTS.find((e) => e.event_id === eventId) || MOCK_EVENTS[1];
    }
    return apiFetch(`/api/v1/claims/${eventId}`);
  },
};

export const digestApi = {
  getByDate: async (dateStr: string): Promise<ExecutionEvent[]> => {
    if (USE_MOCKS) {
      await sleep(500);
      return MOCK_EVENTS;
    }
    return apiFetch(`/api/v1/digest?date=${dateStr}`);
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
    return apiFetch('/api/v1/digest');
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

  getForecast: async (): Promise<{ milestone: string; target_date: string; forecast_date: string; slippage_days: number }[]> => {
    if (USE_MOCKS) {
      await sleep(400);
      return [
        { milestone: 'MS-02 Foundation Completion', target_date: '2026-09-15', forecast_date: '2026-09-18', slippage_days: 3 },
        { milestone: 'MS-03 Piping Hydrotest Clearance', target_date: '2026-10-01', forecast_date: '2026-10-05', slippage_days: 4 },
        { milestone: 'MS-04 Overall Substation Energization', target_date: '2026-11-15', forecast_date: '2026-11-20', slippage_days: 5 },
      ];
    }
    const data: any = await apiFetch('/api/v1/dashboard/forecast?discipline=CIVIL');
    return (data.activities || [data]).map((a: any) => ({ milestone: a.activity_id || a.discipline || 'Unknown', target_date: a.planned_duration ? a.planned_duration + ' days planned' : 'N/A', forecast_date: a.forecast_duration ? a.forecast_duration + ' days forecast' : 'N/A', slippage_days: a.forecast_duration && a.planned_duration ? a.forecast_duration - a.planned_duration : 0 }));
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
};

export const activitiesApi = {
  getHistory: async (activityId: string): Promise<{
    activity: ScheduleActivity | null;
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
      return {
        activity,
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
    const timeline = data.timeline || [];
    const eventItems = timeline.filter((t: any) => t.type === 'execution_event');
    const decisionItem = timeline.find((t: any) => t.type === 'planner_decision');

    // Reuse the existing schedule-activity lookup (schedulesApi.getActivities
    // hits the same endpoint) for real metadata instead of fabricating it.
    // The schedule_id needed to address that endpoint comes from the
    // activity's own linked execution events.
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
      history: eventItems.map((ev: any) => ({
        timestamp: ev.timestamp || ev.event_date || '',
        raw_claim_text: ev.raw_claim_text || '',
        input_channel: 'TYPED_TEXT' as InputChannel,
        claimed_pct: ev.claimed_pct,
        claimed_qty: ev.claimed_quantity,
        status: ev.status || 'EXTRACTED',
        supervisor_action: decisionItem?.action || null,
        actor: 'System',
      })),
    };
  },
};

export const schedulesApi = {
  getActivities: async (scheduleId: string = 'sched-OIL-2026'): Promise<ScheduleActivity[]> => {
    if (USE_MOCKS) {
      await sleep(300);
      return MOCK_ACTIVITIES;
    }
    return apiFetch(`/api/v1/schedules/${scheduleId}/activities`);
  },

  getImpactPreview: async (activityId: string, delayDays: number): Promise<ImpactPreviewResult> => {
    if (USE_MOCKS) {
      await sleep(500);
      const activity = MOCK_ACTIVITIES.find((a) => a.activity_id === activityId) || MOCK_ACTIVITIES[0];
      return {
        activity_id: activity.activity_id,
        delay_days: delayDays,
        disclaimer: 'Preview only · Immediate FS successors · Not full CPM recalculation',
        successors: [
          {
            successor_activity_id: 'ACT-202',
            activity_name: 'Rebar Placement — Column C4',
            relationship_type: 'FS',
            original_start: '2026-09-05',
            original_finish: '2026-09-12',
            shifted_start: '2026-09-10',
            shifted_finish: '2026-09-17',
            lag_days: 0,
          },
          {
            successor_activity_id: 'ACT-301',
            activity_name: 'Field Welding — 6" Crude Line L-1',
            relationship_type: 'FS',
            original_start: '2026-09-12',
            original_finish: '2026-09-25',
            shifted_start: '2026-09-17',
            shifted_finish: '2026-09-30',
            lag_days: 0,
          },
        ],
      };
    }
    const data: any = await apiFetch(`/api/v1/schedule/${activityId}/impact-preview?delay_days=${delayDays}`);
    return {
      activity_id: data.activity_id,
      delay_days: data.delay_days,
      disclaimer: 'Preview only · Immediate FS successors · Not full CPM recalculation',
      successors: (data.impacts || []).map((imp: any) => ({
        successor_activity_id: imp.successor_activity_id,
        activity_name: imp.successor_activity_id,
        relationship_type: imp.dependency_type || 'FS',
        original_start: imp.original_earliest_start || '',
        original_finish: '',
        shifted_start: imp.shifted_earliest_start || '',
        shifted_finish: '',
        lag_days: 0,
      })),
    };
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

