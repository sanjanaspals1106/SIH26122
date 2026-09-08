-- SIH26122 shared schema — PostgreSQL/Supabase (PRD v5). Shared file; any
-- change needs a heads-up in team chat before pushing (doc Section 5).
--
-- Changed from the SQLite version per PRD v5:
--   - New `profiles` table (Supabase Auth identity + role)
--   - TIMESTAMP -> TIMESTAMPTZ, DEFAULT CURRENT_TIMESTAMP -> DEFAULT now()
--   - uploader_id / supervisor_id / planner_id / actor_id are now UUID,
--     referencing profiles.id, not free-text names
--   - log_id uses SERIAL (Postgres identity) instead of SQLite's AUTOINCREMENT

CREATE TABLE IF NOT EXISTS profiles(
  id UUID PRIMARY KEY,              -- = auth.users.id, NOT app-generated
  full_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('SITE_ENGINEER', 'SUPERVISOR')),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS schedules(
  schedule_id TEXT PRIMARY KEY,
  project_name TEXT NOT NULL,
  data_date DATE,
  source_format TEXT, -- P6_CSV, MSP_XML, EXCEL
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS schedule_activities(
  activity_id TEXT NOT NULL,       -- EXTERNAL id from P6/MSP, e.g. "A1000". NEVER generated.
  schedule_id TEXT NOT NULL,
  activity_name TEXT NOT NULL,
  wbs_code TEXT,
  discipline TEXT NOT NULL,
  location TEXT NOT NULL,
  asset_tag TEXT,
  planned_start DATE NOT NULL,
  planned_finish DATE NOT NULL,
  planned_quantity REAL,
  uom TEXT,
  baseline_pct_complete REAL DEFAULT 0.0,
  PRIMARY KEY (schedule_id, activity_id)
);

CREATE TABLE IF NOT EXISTS schedule_dependencies(
  dependency_id TEXT PRIMARY KEY,
  schedule_id TEXT NOT NULL,
  predecessor_activity_id TEXT NOT NULL,
  successor_activity_id TEXT NOT NULL,
  relationship_type TEXT DEFAULT 'FS' -- FS, SS, FF, SF
);

-- ===== M2 owns everything below down to source_references =====

CREATE TABLE IF NOT EXISTS source_documents(
  document_id TEXT PRIMARY KEY,
  file_name TEXT NOT NULL,
  document_type TEXT, -- DPR, MBOOK, CHAT_LOG, QC_INSPECTION, SUPERVISOR_NOTE,
                       -- SCANNED_DIARY, SCHEDULE_EXPORT_PROGRESS
  uploader_id UUID,    -- references profiles.id — the Site Engineer who uploaded it
  file_hash TEXT NOT NULL,
  uploaded_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS execution_events(
  event_id TEXT PRIMARY KEY,
  document_id TEXT,
  schedule_id TEXT NOT NULL,
  event_date DATE NOT NULL,
  raw_claim_text TEXT NOT NULL,
  input_channel TEXT NOT NULL, -- FILE_UPLOAD, SCANNED_OCR, TYPED_TEXT, VOICE, SCHEDULE_EXPORT
  language_detected TEXT,
  reported_activity_id TEXT,
  matched_activity_id TEXT,
  discipline TEXT, -- CIVIL, PIPING, STATIC_ROTATING_EQUIPMENT, ELECTRICAL, INSTRUMENTATION, HSE
  action TEXT,
  event_type TEXT, -- ACTUAL_START, ACTUAL_FINISH, PROGRESS_UPDATE, DELAY, BLOCKER
  claim_mode TEXT DEFAULT 'CUMULATIVE_PCT', -- CUMULATIVE_PCT | INCREMENTAL_QUANTITY
  asset_tag TEXT,
  location TEXT,
  claimed_quantity REAL,
  claimed_uom TEXT,
  claimed_pct REAL,
  delay_reason TEXT, -- MATERIAL, EQUIPMENT, LABOUR, ACCESS, WEATHER, REWORK, OTHER
  supervisor_id UUID,  -- references profiles.id — legacy name; the Site Engineer
                       -- who reported it, NOT related to the SUPERVISOR role
  photo_path TEXT,
  status TEXT DEFAULT 'EXTRACTED',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS source_references(
  reference_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  file_name TEXT,
  sheet_name TEXT,
  row_cell_ref TEXT,
  message_id TEXT,
  raw_snippet TEXT NOT NULL
);

-- ===== Owned by M3/M4/M5/M6 respectively — included so the DB migration is
-- complete in one file; each member's router only ever touches its own tables. =====

CREATE TABLE IF NOT EXISTS candidate_matches(
  candidate_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  schedule_id TEXT NOT NULL,
  activity_id TEXT NOT NULL,
  rank_order INTEGER CHECK (rank_order BETWEEN 1 AND 3),
  match_tier TEXT,
  composite_confidence REAL CHECK (composite_confidence BETWEEN 0.0 AND 1.0),
  semantic_score REAL,
  fuzzy_score REAL,
  location_score REAL,
  discipline_score REAL,
  supporting_signals TEXT,
  disqualifying_signals TEXT,
  UNIQUE (event_id, rank_order)
);

CREATE TABLE IF NOT EXISTS conflict_records(
  conflict_id TEXT PRIMARY KEY,
  schedule_id TEXT NOT NULL,
  activity_id TEXT NOT NULL,
  reporting_period DATE NOT NULL,
  event_id_a TEXT NOT NULL,
  event_id_b TEXT NOT NULL,
  value_a REAL NOT NULL,
  value_b REAL NOT NULL,
  variance_pct REAL NOT NULL,
  status TEXT DEFAULT 'OPEN'
);

CREATE TABLE IF NOT EXISTS validation_issues(
  issue_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  rule_code TEXT,
  severity TEXT, -- WARNING, ERROR
  description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS planner_decisions(
  decision_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  selected_activity_id TEXT NOT NULL,
  action TEXT, -- APPROVE, EDIT, REJECT, HOLD
  approved_pct REAL,
  approved_qty REAL,
  planner_id UUID NOT NULL,   -- references profiles.id (SUPERVISOR)
  justification TEXT NOT NULL,
  decided_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS approved_actuals(
  actual_id TEXT PRIMARY KEY,
  decision_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  schedule_id TEXT NOT NULL,
  activity_id TEXT NOT NULL,
  actual_start DATE,
  actual_finish DATE,
  actual_pct_complete REAL CHECK (actual_pct_complete BETWEEN 0.0 AND 100.0),
  actual_quantity REAL,
  exported_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (schedule_id, activity_id)
);

CREATE TABLE IF NOT EXISTS audit_logs(
  log_id SERIAL PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  actor_id TEXT NOT NULL,  -- profiles.id as text, OR a SYSTEM:Mx constant
  before_state TEXT,
  after_state TEXT,
  payload_hash TEXT NOT NULL,
  previous_hash TEXT NOT NULL,
  current_hash TEXT NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT now()
);
