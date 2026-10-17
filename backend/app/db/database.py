import sqlite3
import os
from pathlib import Path
from typing import Generator
from backend.app.core.config import settings
from backend.app.core.logger import logger

def get_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with foreign keys and WAL mode enabled."""
    db_path = str(settings.DATABASE_PATH)
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def run_schema_migrations(conn: sqlite3.Connection) -> None:
    """Safely apply column additions for Phase 2 operational intelligence if upgrading existing db."""
    cur = conn.cursor()
    
    def get_columns(table_name: str) -> set:
        cur.execute(f"PRAGMA table_info({table_name});")
        return {row[1] for row in cur.fetchall()}

    # Stores table migrations
    store_cols = get_columns("stores")
    if "operating_status" not in store_cols:
        conn.execute("ALTER TABLE stores ADD COLUMN operating_status TEXT NOT NULL DEFAULT 'OPERATIONAL';")
    if "metadata" not in store_cols:
        conn.execute("ALTER TABLE stores ADD COLUMN metadata TEXT;")

    # Operational Teams table migrations
    team_cols = get_columns("operational_teams")
    if "region_id" not in team_cols:
        conn.execute("ALTER TABLE operational_teams ADD COLUMN region_id TEXT REFERENCES regions(id) ON DELETE SET NULL;")
    if "responsibility" not in team_cols:
        conn.execute("ALTER TABLE operational_teams ADD COLUMN responsibility TEXT;")
    if "specialization" not in team_cols:
        conn.execute("ALTER TABLE operational_teams ADD COLUMN specialization TEXT;")
    if "escalation_contact" not in team_cols:
        conn.execute("ALTER TABLE operational_teams ADD COLUMN escalation_contact TEXT;")
    if "escalation_tier" not in team_cols:
        conn.execute("ALTER TABLE operational_teams ADD COLUMN escalation_tier TEXT NOT NULL DEFAULT 'TIER_1';")
    if "lead_user_id" not in team_cols:
        conn.execute("ALTER TABLE operational_teams ADD COLUMN lead_user_id TEXT REFERENCES users(id) ON DELETE SET NULL;")
    if "status" not in team_cols:
        conn.execute("ALTER TABLE operational_teams ADD COLUMN status TEXT NOT NULL DEFAULT 'ACTIVE';")

    # Organizations table migrations
    org_cols = get_columns("organizations")
    if "description" not in org_cols:
        conn.execute("ALTER TABLE organizations ADD COLUMN description TEXT;")
    if "status" not in org_cols:
        conn.execute("ALTER TABLE organizations ADD COLUMN status TEXT NOT NULL DEFAULT 'ACTIVE';")

    # Regions table migrations
    reg_cols = get_columns("regions")
    if "description" not in reg_cols:
        conn.execute("ALTER TABLE regions ADD COLUMN description TEXT;")
    if "lead_user_id" not in reg_cols:
        conn.execute("ALTER TABLE regions ADD COLUMN lead_user_id TEXT REFERENCES users(id) ON DELETE SET NULL;")

    # Feedback Items table migrations (Phase 3)
    fb_cols = get_columns("feedback_items")
    if fb_cols:
        if "region_id" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN region_id TEXT REFERENCES regions(id) ON DELETE SET NULL;")
        if "channel_type" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN channel_type TEXT NOT NULL DEFAULT 'MANUAL_ENTRY';")
        if "submitter_type" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN submitter_type TEXT NOT NULL DEFAULT 'CUSTOMER';")
        if "privacy_classification" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN privacy_classification TEXT NOT NULL DEFAULT 'INTERNAL';")
        if "processing_status" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN processing_status TEXT NOT NULL DEFAULT 'received';")
        if "status" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN status TEXT NOT NULL DEFAULT 'NEW';")
        if "content_hash" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN content_hash TEXT;")
        if "is_duplicate" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN is_duplicate INTEGER NOT NULL DEFAULT 0;")
        if "duplicate_of_id" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN duplicate_of_id TEXT REFERENCES feedback_items(id) ON DELETE SET NULL;")
        if "ai_interpretation" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN ai_interpretation TEXT;")
        if "processing_error" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN processing_error TEXT;")
        if "submitted_at" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN submitted_at TEXT;")
        if "human_overrides" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN human_overrides TEXT;")
        if "reviewed_by" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN reviewed_by TEXT REFERENCES users(id) ON DELETE SET NULL;")
        if "reviewed_at" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN reviewed_at TEXT;")
        if "review_notes" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN review_notes TEXT;")
        if "investigation_status" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN investigation_status TEXT NOT NULL DEFAULT 'NOT_NEEDED';")
        if "enriched_text" not in fb_cols:
            conn.execute("ALTER TABLE feedback_items ADD COLUMN enriched_text TEXT;")

    # Investigation Questions table (Phase 5)
    conn.execute("""
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
    """)

    # Issue Clusters & Links (Phase 6)
    conn.execute("""
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
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cluster_feedback_links (
            cluster_id TEXT NOT NULL REFERENCES issue_clusters(id) ON DELETE CASCADE,
            feedback_item_id TEXT NOT NULL REFERENCES feedback_items(id) ON DELETE CASCADE,
            similarity_score REAL NOT NULL DEFAULT 1.0,
            correlation_type TEXT NOT NULL DEFAULT 'SAME_ISSUE',
            added_by TEXT DEFAULT 'SYSTEM_AI',
            created_at TEXT NOT NULL,
            PRIMARY KEY (cluster_id, feedback_item_id)
        );
    """)

    # Issues table migrations (Phases 6, 8)
    issue_cols = get_columns("issues")
    if issue_cols:
        if "cluster_id" not in issue_cols:
            conn.execute("ALTER TABLE issues ADD COLUMN cluster_id TEXT REFERENCES issue_clusters(id) ON DELETE SET NULL;")
        if "recurrence_count" not in issue_cols:
            conn.execute("ALTER TABLE issues ADD COLUMN recurrence_count INTEGER NOT NULL DEFAULT 0;")
        if "geographic_spread_count" not in issue_cols:
            conn.execute("ALTER TABLE issues ADD COLUMN geographic_spread_count INTEGER NOT NULL DEFAULT 1;")
        if "factor_breakdown" not in issue_cols:
            conn.execute("ALTER TABLE issues ADD COLUMN factor_breakdown TEXT;")
        if "prioritization_explanation" not in issue_cols:
            conn.execute("ALTER TABLE issues ADD COLUMN prioritization_explanation TEXT;")
        if "assigned_user_id" not in issue_cols:
            conn.execute("ALTER TABLE issues ADD COLUMN assigned_user_id TEXT REFERENCES users(id) ON DELETE SET NULL;")
        if "sla_minutes" not in issue_cols:
            conn.execute("ALTER TABLE issues ADD COLUMN sla_minutes INTEGER DEFAULT 60;")
        if "sla_deadline" not in issue_cols:
            conn.execute("ALTER TABLE issues ADD COLUMN sla_deadline TEXT;")
        if "routing_status" not in issue_cols:
            conn.execute("ALTER TABLE issues ADD COLUMN routing_status TEXT DEFAULT 'ROUTED';")
        if "routing_decision_id" not in issue_cols:
            conn.execute("ALTER TABLE issues ADD COLUMN routing_decision_id TEXT;")

    # Routing Decisions table (Phase 10)
    conn.execute("""
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
    """)

    # Alerts table migrations (Phase 7)
    alert_cols = get_columns("alerts")
    if alert_cols:
        if "urgency" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN urgency TEXT NOT NULL DEFAULT 'MEDIUM';")
        if "confidence" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN confidence REAL NOT NULL DEFAULT 0.85;")
        if "what" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN what TEXT;")
        if "where_zone" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN where_zone TEXT;")
        if "observation_count" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN observation_count INTEGER NOT NULL DEFAULT 1;")
        if "sources_summary" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN sources_summary TEXT;")
        if "baseline_diff" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN baseline_diff REAL DEFAULT 0.0;")
        if "velocity_zscore" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN velocity_zscore REAL DEFAULT 0.0;")
        if "growth_rate" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN growth_rate REAL DEFAULT 0.0;")
        if "baseline_status" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN baseline_status TEXT DEFAULT 'NORMAL';")
        if "why_generated" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN why_generated TEXT;")
        if "uncertainties" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN uncertainties TEXT;")
        if "status" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN status TEXT NOT NULL DEFAULT 'NEW';")
        if "escalated_to_team_id" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN escalated_to_team_id TEXT REFERENCES operational_teams(id) ON DELETE SET NULL;")
        if "escalated_by" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN escalated_by TEXT REFERENCES users(id) ON DELETE SET NULL;")
        if "escalated_at" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN escalated_at TEXT;")
        if "dismissed_by" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN dismissed_by TEXT REFERENCES users(id) ON DELETE SET NULL;")
        if "dismissed_at" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN dismissed_at TEXT;")
        if "dismiss_reason" not in alert_cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN dismiss_reason TEXT;")

    # Evidence table migrations (Phase 9)
    ev_cols = get_columns("evidence")
    if ev_cols:
        if "lineage_stage" not in ev_cols:
            conn.execute("ALTER TABLE evidence ADD COLUMN lineage_stage TEXT DEFAULT 'EXTRACTION';")
        if "claim_type" not in ev_cols:
            conn.execute("ALTER TABLE evidence ADD COLUMN claim_type TEXT DEFAULT 'FACT';")
        if "uncertainty_note" not in ev_cols:
            conn.execute("ALTER TABLE evidence ADD COLUMN uncertainty_note TEXT;")

    # Outcome Measurements table migrations (Phase 12)
    conn.execute("""
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
            outcome_status TEXT NOT NULL,
            status_message TEXT,
            confidence REAL NOT NULL DEFAULT 0.5,
            comparison_data TEXT,
            baseline_snapshot TEXT,
            post_snapshot TEXT,
            evidence TEXT,
            measured_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_org ON outcome_measurements(organization_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_issue ON outcome_measurements(issue_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_status ON outcome_measurements(outcome_status);")

    # Operational Intelligence Briefs migrations (Phase 14)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS operational_briefs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            store_id TEXT REFERENCES stores(id) ON DELETE CASCADE,
            region_id TEXT REFERENCES regions(id) ON DELETE CASCADE,
            timeframe_type TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            title TEXT NOT NULL,
            executive_summary TEXT NOT NULL,
            what_changed TEXT,
            emerging_issues TEXT,
            highest_priority_issues TEXT,
            affected_locations TEXT,
            evidence TEXT,
            hypotheses TEXT,
            recommended_actions TEXT,
            uncertainties TEXT,
            unresolved_issues TEXT,
            intervention_outcomes TEXT,
            labeled_claims TEXT,
            deterministic_metrics TEXT,
            generated_by TEXT REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)
    # -------------------------------------------------------------------------
    # Phase 19: Reliability & Observability Tables and Indexes
    # -------------------------------------------------------------------------
    # Idempotency Keys table
    conn.execute("""
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
    """)

    # Background Jobs table
    conn.execute("""
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
    """)

    # AI Governance Logs column migrations
    ai_cols = get_columns("ai_governance_logs")
    if ai_cols:
        if "request_id" not in ai_cols:
            conn.execute("ALTER TABLE ai_governance_logs ADD COLUMN request_id TEXT;")
        if "status" not in ai_cols:
            conn.execute("ALTER TABLE ai_governance_logs ADD COLUMN status TEXT NOT NULL DEFAULT 'SUCCESS';")
        if "error_message" not in ai_cols:
            conn.execute("ALTER TABLE ai_governance_logs ADD COLUMN error_message TEXT;")
        if "task_type" not in ai_cols:
            conn.execute("ALTER TABLE ai_governance_logs ADD COLUMN task_type TEXT NOT NULL DEFAULT 'INFERENCE';")

    # User table migrations (Customer Auth & OTP)
    user_cols = get_columns("users")
    if user_cols:
        if "is_verified" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 1;")
        if "phone" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN phone TEXT;")

    # Email Verification OTPs table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_verification_otps (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            email TEXT NOT NULL,
            otp_code_hash TEXT NOT NULL,
            purpose TEXT NOT NULL DEFAULT 'REGISTRATION',
            expires_at TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 5,
            is_used INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
    """)

    # Customer Complaints table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customer_complaints (
            id TEXT PRIMARY KEY,
            reference_number TEXT UNIQUE NOT NULL,
            customer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            customer_phone TEXT,
            category TEXT NOT NULL,
            order_number TEXT,
            store_id TEXT REFERENCES stores(id) ON DELETE SET NULL,
            store_name TEXT,
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            attachment_url TEXT,
            attachment_name TEXT,
            status TEXT NOT NULL DEFAULT 'SUBMITTED',
            priority TEXT NOT NULL DEFAULT 'MEDIUM',
            assigned_team_id TEXT REFERENCES operational_teams(id) ON DELETE SET NULL,
            assigned_team_name TEXT,
            assigned_to_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
            assigned_to_name TEXT,
            investigation_notes TEXT,
            resolution_summary TEXT,
            feedback_item_id TEXT REFERENCES feedback_items(id) ON DELETE SET NULL,
            issue_id TEXT REFERENCES issues(id) ON DELETE SET NULL,
            timeline TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)

    # Production Performance Indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fb_org_created ON feedback_items(organization_id, created_at DESC);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fb_status ON feedback_items(status, processing_status);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fb_channel ON feedback_items(channel_type, created_at DESC);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_org_status ON issues(organization_id, status);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_store_priority ON issues(store_id, priority_score DESC);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_store_status ON alerts(store_id, status);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_org_time ON alerts(organization_id, created_at DESC);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status_sched ON background_jobs(status, scheduled_at);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_type ON background_jobs(job_type);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_idempotency_expires ON idempotency_keys(expires_at);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_logs_req ON ai_governance_logs(request_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_logs_status ON ai_governance_logs(status, created_at DESC);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_customer_complaints_cust ON customer_complaints(customer_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_customer_complaints_ref ON customer_complaints(reference_number);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_customer_complaints_status ON customer_complaints(status);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_customer_complaints_store ON customer_complaints(store_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_email_otps_email ON email_verification_otps(email);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_email_otps_user ON email_verification_otps(user_id);")

    conn.commit()

def init_db() -> None:
    """Execute schema initialization and ensure all tables exist."""
    schema_path = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
    if not schema_path.exists():
        schema_path = settings.ROOT_DIR / "server" / "src" / "db" / "schema.sql"

    logger.info(f"Initializing database from {schema_path}...")
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            );
        """)

        run_schema_migrations(conn)

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        run_schema_migrations(conn)
        conn.commit()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Database initialization error: {e}")
        raise
    finally:
        conn.close()

def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency for database session management."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
