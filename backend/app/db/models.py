"""SQLAlchemy 2.0 ORM Models for SurakshaVani.

Implements all 15 core tables specified in the build plan with types,
foreign keys, encrypted columns, blind-index hashes, and audit constraints.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    Numeric, String, Text, LargeBinary, Index
)
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

# Universal JSON type
JSON_TYPE = SQLITE_JSON


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class District(Base):
    __tablename__ = "districts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(10), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False, default="Maharashtra")
    cyber_cell_email = Column(String(255), nullable=True)
    cyber_cell_phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    users = relationship("User", back_populates="district")
    cases = relationship("Case", back_populates="district")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    role = Column(String(30), nullable=False, default="operator")  # operator, analyst, admin
    district_id = Column(String(36), ForeignKey("districts.id", ondelete="SET NULL"), nullable=True)
    badge_number = Column(String(50), nullable=True)
    password_hash = Column(String(255), nullable=False)
    totp_secret_enc = Column(LargeBinary, nullable=True)
    totp_enabled = Column(Boolean, default=False, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    district = relationship("District", back_populates="users")


class Reporter(Base):
    __tablename__ = "reporters"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    phone_hash = Column(String(64), unique=True, nullable=False, index=True)  # HMAC-SHA256
    phone_enc = Column(LargeBinary, nullable=False)                           # AES-256-GCM
    language = Column(String(10), nullable=False, default="mr")               # mr, hi, en
    consent_version = Column(String(20), nullable=False, default="v1.0")
    nominee_name_enc = Column(LargeBinary, nullable=True)
    nominee_phone_enc = Column(LargeBinary, nullable=True)
    nominee_phone_hash = Column(String(64), nullable=True)
    deleted_at = Column(DateTime, nullable=True)                              # Soft delete for erasure
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    consents = relationship("Consent", back_populates="reporter", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="reporter", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="reporter")


class Consent(Base):
    __tablename__ = "consents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    reporter_id = Column(String(36), ForeignKey("reporters.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(20), nullable=False)
    language = Column(String(10), nullable=False)
    purposes = Column(JSON_TYPE, nullable=False)  # list of purposes
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    granted_at = Column(DateTime, default=get_utc_now, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    reporter = relationship("Reporter", back_populates="consents")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    reporter_id = Column(String(36), ForeignKey("reporters.id", ondelete="CASCADE"), nullable=False)
    channel = Column(String(30), nullable=False, default="web_sim")
    state = Column(String(50), nullable=False, default="NEW")
    context_enc = Column(LargeBinary, nullable=True)
    last_activity_at = Column(DateTime, default=get_utc_now, nullable=False)
    case_id = Column(String(36), nullable=True)
    is_locked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    reporter = relationship("Reporter", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    direction = Column(String(20), nullable=False)  # inbound, outbound
    kind = Column(String(30), nullable=False, default="text")  # text, audio, image, button_reply
    body_enc = Column(LargeBinary, nullable=False)
    media_ref = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    ref_no = Column(String(30), unique=True, nullable=False, index=True)
    reporter_id = Column(String(36), ForeignKey("reporters.id", ondelete="RESTRICT"), nullable=False)
    category = Column(String(50), nullable=False)  # fraud, extortion, unknown
    subtype = Column(String(80), nullable=False)   # otp_impersonation, task_job_scam, digital_arrest, etc.
    status = Column(String(30), nullable=False, default="NEW")  # NEW, NEEDS_INFO, UNDER_REVIEW, FORWARDED, CLOSED, REJECTED_DUPLICATE
    urgency = Column(String(20), nullable=False, default="NORMAL")  # CRITICAL, HIGH, NORMAL
    incident_at = Column(DateTime, nullable=True)
    reported_at = Column(DateTime, default=get_utc_now, nullable=False)
    amount_inr = Column(Float, default=0.0, nullable=False)
    district_id = Column(String(36), ForeignKey("districts.id", ondelete="SET NULL"), nullable=True)
    language = Column(String(10), nullable=False, default="mr")
    data_enc = Column(LargeBinary, nullable=False)
    confidence_json = Column(JSON_TYPE, default=dict, nullable=False)
    flags_json = Column(JSON_TYPE, default=dict, nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    reporter = relationship("Reporter", back_populates="cases")
    district = relationship("District", back_populates="cases")
    identifiers = relationship("Identifier", back_populates="case", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    events = relationship("CaseEvent", back_populates="case", cascade="all, delete-orphan")
    handoffs = relationship("Handoff", back_populates="case", cascade="all, delete-orphan")


class Identifier(Base):
    __tablename__ = "identifiers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(30), nullable=False)  # phone, upi, account, url, app, email, handle
    role = Column(String(20), nullable=False, default="suspect")  # suspect, beneficiary
    value_enc = Column(LargeBinary, nullable=False)
    value_hash = Column(String(64), nullable=False, index=True)
    raw_preview = Column(String(40), nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    case = relationship("Case", back_populates="identifiers")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    object_key = Column(String(500), nullable=False)
    sha256 = Column(String(64), nullable=False)
    mime = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    kind = Column(String(50), nullable=False)  # screenshot, chat_export, voice_note
    encrypted = Column(Boolean, default=True, nullable=False)
    uploaded_at = Column(DateTime, default=get_utc_now, nullable=False)

    case = relationship("Case", back_populates="evidence")


class CaseEvent(Base):
    __tablename__ = "case_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    actor_type = Column(String(30), nullable=False)  # system, operator, analyst, user
    actor_id = Column(String(36), nullable=True)
    event = Column(String(100), nullable=False)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=True)
    note = Column(Text, nullable=True)
    at = Column(DateTime, default=get_utc_now, nullable=False)

    case = relationship("Case", back_populates="events")


class Handoff(Base):
    __tablename__ = "handoffs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    adapter = Column(String(50), nullable=False)  # mock_desk, email, pdf_export, cfcfrms_api
    status = Column(String(50), nullable=False, default="QUEUED")  # QUEUED, DELIVERED, ACKNOWLEDGED, FAILED
    payload_ref = Column(String(500), nullable=True)
    sent_at = Column(DateTime, default=get_utc_now, nullable=False)
    ack_ref = Column(String(100), nullable=True)
    response_json = Column(JSON_TYPE, default=dict, nullable=False)

    case = relationship("Case", back_populates="handoffs")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    at = Column(DateTime, default=get_utc_now, nullable=False)
    actor_type = Column(String(30), nullable=False)
    actor_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False)
    entity = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=True)
    ip_address = Column(String(45), nullable=True)
    details_json = Column(JSON_TYPE, default=dict, nullable=False)
    prev_hash = Column(String(64), nullable=False)
    hash = Column(String(64), nullable=False)


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    kind = Column(String(50), nullable=False)  # script_cluster, upi_ring, phone_network
    label = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0, nullable=False)
    case_count = Column(Integer, default=1, nullable=False)
    total_amount_inr = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)
    params_json = Column(JSON_TYPE, default=dict, nullable=False)

    members = relationship("ClusterMember", back_populates="cluster", cascade="all, delete-orphan")


class ClusterMember(Base):
    __tablename__ = "cluster_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    cluster_id = Column(String(36), ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False)
    case_id_hash = Column(String(64), nullable=False)
    case_ref_no = Column(String(30), nullable=False)
    score = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    cluster = relationship("Cluster", back_populates="members")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    kind = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, default="HIGH")  # CRITICAL, HIGH, MEDIUM, LOW
    text = Column(Text, nullable=False)
    district_id = Column(String(36), ForeignKey("districts.id", ondelete="SET NULL"), nullable=True)
    cluster_id = Column(String(36), ForeignKey("clusters.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    acknowledged_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

