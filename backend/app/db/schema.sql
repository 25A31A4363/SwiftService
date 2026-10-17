-- ==============================================================================
-- R5 Operational Intelligence Platform - Database Schema
-- Multi-tier Retail Operations + Closed-Loop Incident Resolution Core
-- Secondary isolated Personal/Home schema included for future extensibility
-- ==============================================================================

PRAGMA foreign_keys = ON;

-- 1. Organizations
CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 2. Regions
CREATE TABLE IF NOT EXISTS regions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    description TEXT,
    lead_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 3. Stores
CREATE TABLE IF NOT EXISTS stores (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    region_id TEXT NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    store_number INTEGER UNIQUE NOT NULL,
    street TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    country TEXT,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    operating_status TEXT NOT NULL DEFAULT 'OPERATIONAL',
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 4. Departments
CREATE TABLE IF NOT EXISTS departments (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    store_id TEXT NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    floor_zone TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 5. Physical Assets
CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    store_id TEXT NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    department_id TEXT REFERENCES departments(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    asset_tag TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPERATIONAL',
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 6. Operational & Maintenance Teams
CREATE TABLE IF NOT EXISTS operational_teams (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    region_id TEXT REFERENCES regions(id) ON DELETE SET NULL,
    store_id TEXT REFERENCES stores(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    team_type TEXT NOT NULL,
    sla_tier TEXT NOT NULL DEFAULT 'STANDARD',
    contact_email TEXT,
    responsibility TEXT,
    specialization TEXT,
    escalation_contact TEXT,
    escalation_tier TEXT NOT NULL DEFAULT 'TIER_1',
    lead_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 7. Users
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    store_id TEXT REFERENCES stores(id) ON DELETE SET NULL,
    region_id TEXT REFERENCES regions(id) ON DELETE SET NULL,
    team_id TEXT REFERENCES operational_teams(id) ON DELETE SET NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    last_login_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 8. Feedback Ingestion (Phase 3 Multichannel Operational Feedback)
CREATE TABLE IF NOT EXISTS feedback_items (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    region_id TEXT REFERENCES regions(id) ON DELETE SET NULL,
    store_id TEXT NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    department_id TEXT REFERENCES departments(id) ON DELETE SET NULL,
    source_type TEXT NOT NULL,
    channel_type TEXT NOT NULL DEFAULT 'MANUAL_ENTRY',
    submitter_type TEXT NOT NULL DEFAULT 'CUSTOMER',
    privacy_classification TEXT NOT NULL DEFAULT 'INTERNAL',
    processing_status TEXT NOT NULL DEFAULT 'received',
    status TEXT NOT NULL DEFAULT 'NEW',
    raw_text TEXT NOT NULL,
    language_code TEXT NOT NULL DEFAULT 'en',
    normalized_text TEXT,
    content_hash TEXT,
    is_duplicate INTEGER NOT NULL DEFAULT 0,
    duplicate_of_id TEXT REFERENCES feedback_items(id) ON DELETE SET NULL,
    ai_interpretation TEXT,
    processing_error TEXT,
    sentiment_score REAL,
    is_ambiguous INTEGER NOT NULL DEFAULT 0,
    has_pii INTEGER NOT NULL DEFAULT 0,
    metadata TEXT,
    human_overrides TEXT,
    reviewed_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TEXT,
    review_notes TEXT,
    investigation_status TEXT NOT NULL DEFAULT 'NOT_NEEDED',
    enriched_text TEXT,
    submitted_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 9. Follow-up Clarification Exchanges & Dynamic Investigation (Phase 5)
CREATE TABLE IF NOT EXISTS follow_up_exchanges (
    id TEXT PRIMARY KEY,
    feedback_item_id TEXT NOT NULL REFERENCES feedback_items(id) ON DELETE CASCADE,
    turn_index INTEGER NOT NULL,
    question TEXT NOT NULL,
    response TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS investigation_questions (
    id TEXT PRIMARY KEY,
    feedback_item_id TEXT NOT NULL REFERENCES feedback_items(id) ON DELETE CASCADE,
    question_key TEXT NOT NULL,
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL DEFAULT 'text',
    options TEXT,
    reason TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'PENDING',
    answer TEXT,
    answered_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    answered_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 10. Issue Clusters (Phase 6: Cross-Source Semantic Clustering)
CREATE TABLE IF NOT EXISTS issue_clusters (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    store_id TEXT REFERENCES stores(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    confidence_score REAL NOT NULL DEFAULT 0.8,
    quality_score REAL NOT NULL DEFAULT 0.8,
    primary_entity TEXT,
    primary_location TEXT,
    earliest_feedback_at TEXT,
    latest_feedback_at TEXT,
    feedback_count INTEGER NOT NULL DEFAULT 0,
    source_diversity_count INTEGER NOT NULL DEFAULT 1,
    merged_into_cluster_id TEXT REFERENCES issue_clusters(id) ON DELETE SET NULL,
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cluster_feedback_links (
    cluster_id TEXT NOT NULL REFERENCES issue_clusters(id) ON DELETE CASCADE,
    feedback_item_id TEXT NOT NULL REFERENCES feedback_items(id) ON DELETE CASCADE,
    similarity_score REAL NOT NULL DEFAULT 1.0,
    correlation_type TEXT NOT NULL DEFAULT 'SAME_ISSUE',
    added_by TEXT DEFAULT 'SYSTEM_AI',
    created_at TEXT NOT NULL,
    PRIMARY KEY (cluster_id, feedback_item_id)
);

-- 11. Issues & Incidents (Phases 6, 8 Prioritization)
CREATE TABLE IF NOT EXISTS issues (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    store_id TEXT NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    department_id TEXT REFERENCES departments(id) ON DELETE SET NULL,
    asset_id TEXT REFERENCES assets(id) ON DELETE SET NULL,
    cluster_id TEXT REFERENCES issue_clusters(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DETECTED',
    priority_score INTEGER NOT NULL,
    priority_tier TEXT NOT NULL,
    severity_score REAL NOT NULL,
    urgency_score REAL NOT NULL,
    impact_scope_score REAL NOT NULL,
    confidence_score REAL NOT NULL,
    is_emerging_anomaly INTEGER NOT NULL DEFAULT 0,
    anomaly_velocity_zscore REAL DEFAULT 0.0,
    assigned_team_id TEXT REFERENCES operational_teams(id) ON DELETE SET NULL,
    root_cause_hypothesis TEXT,
    feedback_count INTEGER NOT NULL DEFAULT 1,
    recurrence_count INTEGER NOT NULL DEFAULT 0,
    geographic_spread_count INTEGER NOT NULL DEFAULT 1,
    factor_breakdown TEXT,
    prioritization_explanation TEXT,
    assigned_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    sla_minutes INTEGER DEFAULT 60,
    sla_deadline TEXT,
    routing_status TEXT DEFAULT 'ROUTED',
    routing_decision_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 11b. Intelligent Operational Routing Decisions (Phase 10)
CREATE TABLE IF NOT EXISTS routing_decisions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    issue_id TEXT NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    selected_team_id TEXT REFERENCES operational_teams(id) ON DELETE SET NULL,
    assigned_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    routing_tier TEXT NOT NULL,
    routing_strategy TEXT NOT NULL,
    reason TEXT NOT NULL,
    supporting_data TEXT,
    confidence REAL NOT NULL DEFAULT 0.85,
    is_ambiguous INTEGER NOT NULL DEFAULT 0,
    fallback_team_id TEXT REFERENCES operational_teams(id) ON DELETE SET NULL,
    is_human_override INTEGER NOT NULL DEFAULT 0,
    override_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    override_reason TEXT,
    sla_minutes INTEGER NOT NULL DEFAULT 60,
    sla_deadline TEXT NOT NULL,
    escalation_deadline TEXT,
    created_at TEXT NOT NULL
);

-- 12. Issue-to-Feedback Relationships (Clustering Evidence Graph)
CREATE TABLE IF NOT EXISTS issue_feedback_links (
    issue_id TEXT NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    feedback_item_id TEXT NOT NULL REFERENCES feedback_items(id) ON DELETE CASCADE,
    PRIMARY KEY (issue_id, feedback_item_id)
);

-- 13. Emerging Alerts (Phase 7)
CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    store_id TEXT NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    issue_id TEXT NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    urgency TEXT NOT NULL DEFAULT 'MEDIUM',
    confidence REAL NOT NULL DEFAULT 0.85,
    message TEXT NOT NULL,
    what TEXT,
    where_zone TEXT,
    observation_count INTEGER NOT NULL DEFAULT 1,
    sources_summary TEXT,
    baseline_diff REAL DEFAULT 0.0,
    velocity_zscore REAL DEFAULT 0.0,
    growth_rate REAL DEFAULT 0.0,
    baseline_status TEXT DEFAULT 'NORMAL',
    why_generated TEXT,
    uncertainties TEXT,
    status TEXT NOT NULL DEFAULT 'NEW',
    is_acknowledged INTEGER NOT NULL DEFAULT 0,
    acknowledged_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_at TEXT,
    escalated_to_team_id TEXT REFERENCES operational_teams(id) ON DELETE SET NULL,
    escalated_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    escalated_at TEXT,
    dismissed_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    dismissed_at TEXT,
    dismiss_reason TEXT,
    created_at TEXT NOT NULL
);

-- 14. Actions & Approvals
CREATE TABLE IF NOT EXISTS action_plans (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    issue_id TEXT NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    recommended_action TEXT NOT NULL,
    target_team_id TEXT NOT NULL REFERENCES operational_teams(id) ON DELETE CASCADE,
    requires_human_approval INTEGER NOT NULL DEFAULT 1,
    approval_status TEXT NOT NULL DEFAULT 'PENDING',
    approved_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    approved_at TEXT,
    override_reason TEXT,
    sla_deadline TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 15. Resolutions & Verification
CREATE TABLE IF NOT EXISTS resolutions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    issue_id TEXT NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    action_plan_id TEXT NOT NULL REFERENCES action_plans(id) ON DELETE CASCADE,
    technician_notes TEXT NOT NULL,
    resolved_by TEXT NOT NULL REFERENCES users(id),
    resolved_at TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'PENDING_VERIFICATION',
    verification_scorecard TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 16. Evidence Citations & Lineage (Phase 9)
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    issue_id TEXT NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    feedback_item_id TEXT NOT NULL REFERENCES feedback_items(id) ON DELETE CASCADE,
    verbatim_quote TEXT NOT NULL,
    source_metadata TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    lineage_stage TEXT DEFAULT 'EXTRACTION',
    claim_type TEXT DEFAULT 'FACT',
    uncertainty_note TEXT,
    created_at TEXT NOT NULL
);

-- 17. Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    previous_state TEXT,
    new_state TEXT,
    justification TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TEXT NOT NULL
);

-- 17. Segregated Personal / Home Mode Schema (Future Extensibility)
CREATE TABLE IF NOT EXISTS personal_home_appliances (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    appliance_type TEXT NOT NULL,
    brand TEXT NOT NULL,
    model_number TEXT,
    serial_number TEXT,
    purchase_date TEXT,
    warranty_until TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS personal_service_tickets (
    id TEXT PRIMARY KEY,
    appliance_id TEXT NOT NULL REFERENCES personal_home_appliances(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    complaint_description TEXT NOT NULL,
    classified_category TEXT NOT NULL,
    routed_service_channel TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'SUBMITTED',
    external_reference_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 18. Roles & Role Permissions Matrix
CREATE TABLE IF NOT EXISTS roles (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    is_system INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission TEXT NOT NULL,
    PRIMARY KEY (role_id, permission)
);

-- 19. Team Memberships (Multi-user assignment & team roles)
CREATE TABLE IF NOT EXISTS team_members (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES operational_teams(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_in_team TEXT NOT NULL DEFAULT 'MEMBER',
    is_primary INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE(team_id, user_id)
);

-- 20. Operational Ownership & Escalation Mapping
CREATE TABLE IF NOT EXISTS operational_ownership_mappings (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    region_id TEXT REFERENCES regions(id) ON DELETE CASCADE,
    store_id TEXT REFERENCES stores(id) ON DELETE CASCADE,
    department_id TEXT REFERENCES departments(id) ON DELETE SET NULL,
    operational_domain TEXT NOT NULL,
    primary_team_id TEXT NOT NULL REFERENCES operational_teams(id) ON DELETE CASCADE,
    secondary_team_id TEXT REFERENCES operational_teams(id) ON DELETE SET NULL,
    escalation_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    sla_minutes INTEGER NOT NULL DEFAULT 60,
    auto_escalate_hours REAL NOT NULL DEFAULT 4.0,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 21. Post-Intervention Outcome Measurements (Phase 12)
CREATE TABLE IF NOT EXISTS outcome_measurements (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    issue_id TEXT NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    resolution_id TEXT REFERENCES resolutions(id) ON DELETE SET NULL,
    action_plan_id TEXT REFERENCES action_plans(id) ON DELETE SET NULL,
    intervention_timestamp TEXT NOT NULL,
    baseline_window_start TEXT NOT NULL,
    baseline_window_end TEXT NOT NULL,
    baseline_window_hours REAL NOT NULL,
    baseline_complaint_volume INTEGER NOT NULL,
    baseline_issue_frequency_per_day REAL NOT NULL,
    baseline_avg_severity REAL NOT NULL,
    baseline_affected_locations_count INTEGER NOT NULL,
    observation_window_start TEXT NOT NULL,
    observation_window_end TEXT NOT NULL,
    observation_window_hours REAL NOT NULL,
    min_observation_hours_required REAL NOT NULL DEFAULT 12.0,
    is_window_sufficient INTEGER NOT NULL DEFAULT 0,
    post_complaint_volume INTEGER NOT NULL,
    post_issue_frequency_per_day REAL NOT NULL,
    post_recurrence_count INTEGER NOT NULL,
    post_avg_severity REAL NOT NULL,
    post_affected_locations_count INTEGER NOT NULL,
    response_time_minutes INTEGER,
    resolution_time_minutes INTEGER,
    sla_compliance INTEGER NOT NULL DEFAULT 1,
    outcome_status TEXT NOT NULL, -- 'Improved', 'No significant change', 'Worsened', 'Inconclusive'
    status_message TEXT,          -- e.g. "outcome cannot yet be determined."
    confidence REAL NOT NULL DEFAULT 0.5,
    comparison_data TEXT,         -- JSON breakdown of all metrics deltas
    baseline_snapshot TEXT,       -- JSON detailed snapshot
    post_snapshot TEXT,           -- JSON detailed post observation
    evidence TEXT,                -- JSON array of deterministic citations
    measured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 22. AI Operational Intelligence Briefs (Phase 14)
CREATE TABLE IF NOT EXISTS operational_briefs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    store_id TEXT REFERENCES stores(id) ON DELETE CASCADE,
    region_id TEXT REFERENCES regions(id) ON DELETE CASCADE,
    timeframe_type TEXT NOT NULL, -- 'DAILY', 'WEEKLY', 'CUSTOM'
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    title TEXT NOT NULL,
    executive_summary TEXT NOT NULL,
    what_changed TEXT,            -- JSON: telemetry deltas
    emerging_issues TEXT,         -- JSON: alerts & velocity anomalies
    highest_priority_issues TEXT, -- JSON: P1/P2 issues & explainability
    affected_locations TEXT,      -- JSON: store/dept concentration
    evidence TEXT,                -- JSON: verbatim citations
    hypotheses TEXT,              -- JSON: root cause explanations
    recommended_actions TEXT,     -- JSON: team dispatches & approvals
    uncertainties TEXT,           -- JSON: explicit unknowns & data gaps
    unresolved_issues TEXT,       -- JSON: active backlog
    intervention_outcomes TEXT,   -- JSON: Phase 12 verified outcomes
    labeled_claims TEXT,          -- JSON: claims with OBSERVATION/HYPOTHESIS/RECOMMENDATION/UNKNOWN
    deterministic_metrics TEXT,   -- JSON: verified counts from DB
    generated_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 20. Data Retention Policies (Phase 16)
CREATE TABLE IF NOT EXISTS data_retention_policies (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,          -- 'FEEDBACK_ITEMS', 'INVESTIGATION_QUESTIONS', 'ALERTS', 'ACTION_PLANS', 'AUDIT_LOGS'
    retention_days INTEGER NOT NULL,    -- 30, 90, 180, 365, 730
    action_on_expire TEXT NOT NULL DEFAULT 'PURGE', -- 'PURGE' | 'ANONYMIZE'
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, entity_type)
);

-- 21. AI Governance & Auditability Logs (Phase 16)
CREATE TABLE IF NOT EXISTS ai_governance_logs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    provider_name TEXT NOT NULL,        -- 'LOCAL_DETERMINISTIC', 'EXTERNAL_ENTERPRISE_LLM'
    model_name TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    pii_redacted INTEGER NOT NULL DEFAULT 0,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    latency_ms REAL NOT NULL DEFAULT 0.0,
    confidence REAL NOT NULL DEFAULT 1.0,
    uncertainty INTEGER NOT NULL DEFAULT 0,
    uncertainty_reason TEXT,
    is_overridden INTEGER NOT NULL DEFAULT 0,
    override_by TEXT,
    override_reason TEXT,
    created_at TEXT NOT NULL
);

-- 22. Security Audit Events (Phase 16)
CREATE TABLE IF NOT EXISTS security_audit_events (
    id TEXT PRIMARY KEY,
    organization_id TEXT REFERENCES organizations(id) ON DELETE CASCADE,
    user_id TEXT,
    event_type TEXT NOT NULL,          -- 'PROMPT_INJECTION_ATTEMPT', 'RATE_LIMIT_EXCEEDED', 'UNAUTHORIZED_ACCESS_ATTEMPT', 'UNSAFE_UPLOAD_ATTEMPT', 'RETENTION_PURGE'
    severity TEXT NOT NULL DEFAULT 'MEDIUM', -- 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
    source_ip TEXT,
    path TEXT,
    details TEXT,                      -- JSON
    created_at TEXT NOT NULL
);

-- 23. Idempotency Keys (Phase 19)
CREATE TABLE IF NOT EXISTS idempotency_keys (
    idempotency_key TEXT PRIMARY KEY,
    request_path TEXT NOT NULL,
    request_params_hash TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    response_headers TEXT,
    response_body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

-- 24. Background Jobs (Phase 19)
CREATE TABLE IF NOT EXISTS background_jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    backoff_seconds INTEGER NOT NULL DEFAULT 2,
    last_error TEXT,
    scheduled_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_retention_org ON data_retention_policies(organization_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_governance_org ON ai_governance_logs(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_events ON security_audit_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_briefs_org ON operational_briefs(organization_id);
CREATE INDEX IF NOT EXISTS idx_briefs_store ON operational_briefs(store_id);
CREATE INDEX IF NOT EXISTS idx_briefs_timeframe ON operational_briefs(timeframe_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcomes_org ON outcome_measurements(organization_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_issue ON outcome_measurements(issue_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_status ON outcome_measurements(outcome_status);
CREATE INDEX IF NOT EXISTS idx_regions_org ON regions(organization_id);
CREATE INDEX IF NOT EXISTS idx_stores_org_reg ON stores(organization_id, region_id);
CREATE INDEX IF NOT EXISTS idx_stores_status ON stores(operating_status);
CREATE INDEX IF NOT EXISTS idx_departments_store ON departments(store_id);
CREATE INDEX IF NOT EXISTS idx_assets_store ON assets(store_id);
CREATE INDEX IF NOT EXISTS idx_teams_store ON operational_teams(store_id);
CREATE INDEX IF NOT EXISTS idx_teams_region ON operational_teams(region_id);
CREATE INDEX IF NOT EXISTS idx_teams_spec ON operational_teams(specialization);
CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);
CREATE INDEX IF NOT EXISTS idx_users_org_email ON users(organization_id, email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_ownership_store_domain ON operational_ownership_mappings(store_id, operational_domain);
CREATE INDEX IF NOT EXISTS idx_ownership_org ON operational_ownership_mappings(organization_id);
CREATE INDEX IF NOT EXISTS idx_feedback_store_time ON feedback_items(store_id, created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_processing_status ON feedback_items(processing_status);
CREATE INDEX IF NOT EXISTS idx_feedback_content_hash ON feedback_items(content_hash);
CREATE INDEX IF NOT EXISTS idx_feedback_channel_type ON feedback_items(channel_type);
CREATE INDEX IF NOT EXISTS idx_feedback_submitter_type ON feedback_items(submitter_type);
CREATE INDEX IF NOT EXISTS idx_feedback_org_store ON feedback_items(organization_id, store_id);
CREATE INDEX IF NOT EXISTS idx_issues_store_status ON issues(store_id, status);
CREATE INDEX IF NOT EXISTS idx_issues_priority ON issues(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_issue ON alerts(issue_id);
CREATE INDEX IF NOT EXISTS idx_actions_issue ON action_plans(issue_id);
CREATE INDEX IF NOT EXISTS idx_resolutions_issue ON resolutions(issue_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_investigation_feedback ON investigation_questions(feedback_item_id);
CREATE INDEX IF NOT EXISTS idx_investigation_status ON investigation_questions(status);
CREATE INDEX IF NOT EXISTS idx_clusters_store ON issue_clusters(store_id);
CREATE INDEX IF NOT EXISTS idx_clusters_org ON issue_clusters(organization_id);
CREATE INDEX IF NOT EXISTS idx_clusters_status ON issue_clusters(status);
CREATE INDEX IF NOT EXISTS idx_cfl_feedback ON cluster_feedback_links(feedback_item_id);
CREATE INDEX IF NOT EXISTS idx_fb_org_created ON feedback_items(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_fb_status ON feedback_items(status, processing_status);
CREATE INDEX IF NOT EXISTS idx_fb_channel ON feedback_items(channel_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_issues_org_status ON issues(organization_id, status);
CREATE INDEX IF NOT EXISTS idx_issues_store_priority ON issues(store_id, priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_store_status ON alerts(store_id, status);
CREATE INDEX IF NOT EXISTS idx_alerts_org_time ON alerts(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status_sched ON background_jobs(status, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON background_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_idempotency_expires ON idempotency_keys(expires_at);
CREATE INDEX IF NOT EXISTS idx_ai_logs_req ON ai_governance_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_ai_logs_status ON ai_governance_logs(status, created_at DESC);

