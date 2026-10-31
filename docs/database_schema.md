# SurakshaVani: Comprehensive Database Schema & Cryptographic Model

## 1. Architectural Principles & Security Model

SurakshaVani enforces strict data protection rules aligned with India's **Digital Personal Data Protection Act (DPDP), 2023** and **DPDP Rules, 2025**.
1. **Application-Layer Field Encryption (`*_enc`)**:
   - All Personally Identifiable Information (PII) including phone numbers, victim names, full complaint narratives, and TOTP secrets are encrypted before leaving the Python process using **AES-256-GCM**.
   - Each encrypted field includes a 96-bit random IV (nonce) and a 128-bit authentication tag.
2. **Blind Indexing via HMAC (`*_hash`)**:
   - Searchable lookups (such as finding an existing reporter by phone, or detecting repeat scammer phone numbers/UPI IDs) use HMAC-SHA256 with a secret server-side pepper (`HMAC_PEPPER`).
   - Raw values are never stored in plaintext and never leaked via SQL queries.
3. **Immutable Hash-Chained Audit Trail**:
   - Every read and write to sensitive records produces an entry in `audit_log` where each record contains `prev_hash` and `hash = SHA256(prev_hash + record_data)`.
4. **Data Minimization & Automated Purge**:
   - Ephemeral WhatsApp audio recordings are deleted immediately upon transcription.
   - Conversation messages carry `expires_at` (default 7 days) and are purged via background retention workers.

---

## 2. PostgreSQL 16 DDL with Types, Constraints & Indexes

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enums
CREATE TYPE user_role AS ENUM ('operator', 'analyst', 'admin');
CREATE TYPE case_status AS ENUM ('NEW', 'NEEDS_INFO', 'UNDER_REVIEW', 'FORWARDED', 'CLOSED', 'REJECTED_DUPLICATE');
CREATE TYPE urgency_level AS ENUM ('CRITICAL', 'HIGH', 'NORMAL');
CREATE TYPE identifier_kind AS ENUM ('phone', 'upi', 'account', 'url', 'app', 'email', 'handle');
CREATE TYPE identifier_role AS ENUM ('suspect', 'beneficiary');
CREATE TYPE message_direction AS ENUM ('inbound', 'outbound');
CREATE TYPE message_kind AS ENUM ('text', 'audio', 'image', 'document', 'button_reply');
CREATE TYPE actor_type AS ENUM ('system', 'operator', 'analyst', 'admin', 'user');

-- 1. Districts (Maharashtra Routing)
CREATE TABLE districts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL DEFAULT 'Maharashtra',
    cyber_cell_email VARCHAR(255),
    cyber_cell_phone VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_districts_state ON districts(state);
CREATE INDEX idx_districts_name ON districts(name);

-- 2. Internal Users (Police Operators, Cyber Analysts, Admins)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    role user_role NOT NULL DEFAULT 'operator',
    district_id UUID REFERENCES districts(id) ON DELETE SET NULL,
    badge_number VARCHAR(50),
    password_hash VARCHAR(255) NOT NULL,
    totp_secret_enc BYTEA,
    totp_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_role_district ON users(role, district_id);

-- 3. Reporters (Citizen Victims / Nominees)
CREATE TABLE reporters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_hash VARCHAR(64) UNIQUE NOT NULL, -- HMAC-SHA256(phone, pepper)
    phone_enc BYTEA NOT NULL,               -- AES-256-GCM(phone)
    language VARCHAR(10) NOT NULL DEFAULT 'mr', -- mr | hi | en
    consent_version VARCHAR(20) NOT NULL,
    nominee_name_enc BYTEA,
    nominee_phone_enc BYTEA,
    nominee_phone_hash VARCHAR(64),
    deleted_at TIMESTAMPTZ,                 -- Soft delete / DPDP Right to Erasure
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reporters_phone_hash ON reporters(phone_hash) WHERE deleted_at IS NULL;

-- 4. Consents (DPDP Act 2023 Compliant Append-Only Audit)
CREATE TABLE consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id UUID NOT NULL REFERENCES reporters(id) ON DELETE CASCADE,
    version VARCHAR(20) NOT NULL,
    language VARCHAR(10) NOT NULL,
    purposes JSONB NOT NULL,                -- e.g. ["fraud_reporting", "cfcfrms_handoff", "threat_intel"]
    ip_address VARCHAR(45),
    user_agent TEXT,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);

CREATE INDEX idx_consents_reporter ON consents(reporter_id);

-- 5. Conversations (State Machine Tracker)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id UUID NOT NULL REFERENCES reporters(id) ON DELETE CASCADE,
    channel VARCHAR(30) NOT NULL DEFAULT 'web_sim', -- web_sim | whatsapp_cloud | telegram
    state VARCHAR(50) NOT NULL DEFAULT 'NEW',       -- State machine status
    context_enc BYTEA,                             -- Encrypted session memory
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    case_id UUID,                                  -- Associated active case if initiated
    is_locked BOOLEAN NOT NULL DEFAULT FALSE,      -- Concurrency lock
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conversations_reporter ON conversations(reporter_id);
CREATE INDEX idx_conversations_state ON conversations(state);
CREATE INDEX idx_conversations_last_activity ON conversations(last_activity_at);

-- 6. Messages (Audit & Short Retention purge)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    direction message_direction NOT NULL,
    kind message_kind NOT NULL DEFAULT 'text',
    body_enc BYTEA NOT NULL,
    media_ref VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days')
);

CREATE INDEX idx_messages_conv_created ON messages(conversation_id, created_at);
CREATE INDEX idx_messages_expires_at ON messages(expires_at);

-- 7. Cases (Structured Cyber-Crime & Extortion Reports)
CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ref_no VARCHAR(30) UNIQUE NOT NULL,            -- e.g. SV-202610-MUM-8921
    reporter_id UUID NOT NULL REFERENCES reporters(id) ON DELETE RESTRICT,
    category VARCHAR(50) NOT NULL,                 -- fraud | extortion | unknown
    subtype VARCHAR(80) NOT NULL,                  -- otp_impersonation, task_job_scam, digital_arrest, etc.
    status case_status NOT NULL DEFAULT 'NEW',
    urgency urgency_level NOT NULL DEFAULT 'NORMAL',
    incident_at TIMESTAMPTZ,
    reported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    amount_inr NUMERIC(12, 2) DEFAULT 0.00,
    district_id UUID REFERENCES districts(id) ON DELETE SET NULL,
    language VARCHAR(10) NOT NULL DEFAULT 'mr',
    data_enc BYTEA NOT NULL,                       -- AES-256-GCM of full JSON complaint schema
    confidence_json JSONB NOT NULL DEFAULT '{}',   -- Field-level confidence scores
    flags_json JSONB NOT NULL DEFAULT '{}',        -- { money_moved_recently, minor_involved, self_harm_risk, intimate_images }
    golden_hour_active BOOLEAN GENERATED ALWAYS AS (
        incident_at IS NOT NULL AND reported_at <= (incident_at + INTERVAL '60 minutes')
    ) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cases_ref_no ON cases(ref_no);
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_urgency ON cases(urgency);
CREATE INDEX idx_cases_district ON cases(district_id);
CREATE INDEX idx_cases_reported_at ON cases(reported_at DESC);
CREATE INDEX idx_cases_category_subtype ON cases(category, subtype);
CREATE INDEX idx_cases_flags ON cases USING GIN (flags_json);

-- 8. Identifiers (Extracted Entities for Graph Analytics & Linking)
CREATE TABLE identifiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    kind identifier_kind NOT NULL,
    role identifier_role NOT NULL DEFAULT 'suspect',
    value_enc BYTEA NOT NULL,
    value_hash VARCHAR(64) NOT NULL,               -- Blind index HMAC(value, pepper)
    raw_preview VARCHAR(20),                       -- Redacted preview e.g. "+91 98*** 1234"
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_identifiers_lookup ON identifiers(kind, value_hash);
CREATE INDEX idx_identifiers_case_id ON identifiers(case_id);

-- 9. Evidence Vault (Screenshots, PDF receipts, Audio transcripts)
CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    object_key VARCHAR(500) NOT NULL,
    sha256 VARCHAR(64) NOT NULL,                   -- Integrity hash verification
    mime VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    kind VARCHAR(50) NOT NULL,                     -- screenshot | chat_export | bank_slip | voice_note
    encrypted BOOLEAN NOT NULL DEFAULT TRUE,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_evidence_case ON evidence(case_id);

-- 10. Case Events (Audit Timeline for Case State Changes)
CREATE TABLE case_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    actor_type actor_type NOT NULL,
    actor_id UUID,
    event VARCHAR(100) NOT NULL,                   -- STATUS_CHANGE, FIELD_EDIT, 1930_DISPATCH, NOMINEE_NOTIFIED
    from_status case_status,
    to_status case_status,
    note TEXT,
    at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_case_events_case_timeline ON case_events(case_id, at ASC);

-- 11. Handoffs (Dispatches to CFCFRMS, 1930 Desk, Police Cyber Cell)
CREATE TABLE handoffs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    adapter VARCHAR(50) NOT NULL,                  -- mock_desk | email | pdf_export | cfcfrms_api
    status VARCHAR(50) NOT NULL DEFAULT 'QUEUED',  -- QUEUED | DELIVERED | ACKNOWLEDGED | FAILED
    payload_ref VARCHAR(500),
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ack_ref VARCHAR(100),
    response_json JSONB DEFAULT '{}'
);

CREATE INDEX idx_handoffs_case_adapter ON handoffs(case_id, adapter);

-- 12. Audit Log (Cryptographically Tamper-evident Ledger)
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_type actor_type NOT NULL,
    actor_id UUID,
    action VARCHAR(100) NOT NULL,
    entity VARCHAR(50) NOT NULL,
    entity_id UUID,
    ip_address VARCHAR(45),
    details_json JSONB DEFAULT '{}',
    prev_hash VARCHAR(64) NOT NULL,
    hash VARCHAR(64) NOT NULL
);

CREATE INDEX idx_audit_log_entity ON audit_log(entity, entity_id);
CREATE INDEX idx_audit_log_at ON audit_log(at DESC);

-- 13. Clusters (Machine Learning Threat Intelligence & Emerging Syndicates)
CREATE TABLE clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind VARCHAR(50) NOT NULL,                     -- script_cluster | upi_ring | phone_network
    label VARCHAR(255) NOT NULL,                   -- e.g. "MSEDCL Electricity Meter Disconnection Ring"
    summary TEXT NOT NULL,
    confidence NUMERIC(4, 3) DEFAULT 0.000,
    case_count INT NOT NULL DEFAULT 1,
    total_amount_inr NUMERIC(14, 2) DEFAULT 0.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    params_json JSONB DEFAULT '{}'
);

CREATE INDEX idx_clusters_kind_created ON clusters(kind, created_at DESC);

-- 14. Cluster Members (Linkage between Clusters and Cases)
CREATE TABLE cluster_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_id UUID NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    case_id_hash VARCHAR(64) NOT NULL,
    case_ref_no VARCHAR(30) NOT NULL,
    score NUMERIC(4, 3) NOT NULL,                  -- Similarity distance / confidence
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cluster_members_cluster ON cluster_members(cluster_id);
CREATE INDEX idx_cluster_members_case_hash ON cluster_members(case_id_hash);

-- 15. Threat Alerts (Proactive Early-Warning Signals for Law Enforcement)
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind VARCHAR(50) NOT NULL,                     -- surge_alert | new_scam_variant | serial_blackmailer
    severity VARCHAR(20) NOT NULL DEFAULT 'HIGH',   -- CRITICAL | HIGH | MEDIUM | LOW
    text TEXT NOT NULL,
    district_id UUID REFERENCES districts(id) ON DELETE SET NULL,
    cluster_id UUID REFERENCES clusters(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_by UUID REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_at TIMESTAMPTZ
);

CREATE INDEX idx_alerts_unack ON alerts(acknowledged_at) WHERE acknowledged_at IS NULL;
```
