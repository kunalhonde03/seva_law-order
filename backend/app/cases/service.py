"""Case Management Service for SurakshaVani.

Handles encrypted persistence, blind indexing, search, audit logging,
and status transitions.
"""

import json
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.crypto import encrypt_field, decrypt_field, hmac_hash, compute_audit_hash
from backend.app.cases.urgency import calculate_case_urgency
from backend.app.db.models import Case, Reporter, Identifier, CaseEvent, AuditLog, District


async def get_latest_audit_hash(session: AsyncSession) -> str:
    stmt = select(AuditLog).order_by(desc(AuditLog.at)).limit(1)
    res = await session.execute(stmt)
    latest = res.scalar_one_or_none()
    return latest.hash if latest else "GENESIS_BLOCK_SURAKSHAVANI_2026"


async def append_audit_entry(
    session: AsyncSession,
    actor_type: str,
    actor_id: Optional[str],
    action: str,
    entity: str,
    entity_id: Optional[str],
    details: Dict[str, Any],
    ip_address: Optional[str] = "127.0.0.1"
) -> AuditLog:
    prev_hash = await get_latest_audit_hash(session)
    entry_dict = {
        "actor_type": actor_type,
        "actor_id": actor_id,
        "action": action,
        "entity": entity,
        "entity_id": entity_id,
        "details": details,
        "ip": ip_address
    }
    cur_hash = compute_audit_hash(prev_hash, entry_dict)
    
    log = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        ip_address=ip_address,
        details_json=details,
        prev_hash=prev_hash,
        hash=cur_hash
    )
    session.add(log)
    return log


async def create_case_from_complaint(
    session: AsyncSession,
    reporter_id: str,
    complaint_data: Dict[str, Any],
    district_code: str = "MUM",
    language: str = "mr"
) -> Case:
    """Persists a new encrypted cyber complaint with blind indexes and urgency rules."""
    now = datetime.now(timezone.utc)
    ref_suffix = f"{random.randint(1000, 9999)}"
    ref_no = f"SV-{now.strftime('%Y%m')}-{district_code}-{ref_suffix}"

    amount = complaint_data.get("amount_inr", {}).get("value")
    flags = complaint_data.get("flags", {})
    category = complaint_data.get("category", "fraud")
    subtype = complaint_data.get("subtype", "other")

    # Resolve incident time
    inc_time_str = complaint_data.get("incident_time", {}).get("value")
    inc_dt = None
    if inc_time_str:
        try:
            inc_dt = datetime.fromisoformat(inc_time_str.replace("Z", "+00:00"))
        except Exception:
            inc_dt = now

    urgency = calculate_case_urgency(inc_dt, amount, flags, category)

    # Encrypt full complaint payload
    payload_json = json.dumps(complaint_data, ensure_ascii=False)
    data_enc = encrypt_field(payload_json)

    # District lookup
    stmt = select(District).where(District.code == district_code)
    res = await session.execute(stmt)
    district_obj = res.scalar_one_or_none()
    district_id = district_obj.id if district_obj else None

    case = Case(
        ref_no=ref_no,
        reporter_id=reporter_id,
        category=category,
        subtype=subtype,
        status="NEW",
        urgency=urgency,
        incident_at=inc_dt,
        reported_at=now,
        amount_inr=float(amount) if amount is not None else 0.0,
        district_id=district_id,
        language=language,
        data_enc=data_enc,
        confidence_json=complaint_data.get("field_confidence", {}),
        flags_json=flags
    )
    session.add(case)
    await session.flush()

    # Index Suspect Identifiers
    for s in complaint_data.get("suspect_identifiers", []):
        val = s.get("value", "").strip()
        if val:
            kind = s.get("kind", "phone")
            role = s.get("role", "suspect")
            val_enc = encrypt_field(val)
            val_hash = hmac_hash(val)
            raw_preview = val[:4] + "***" + val[-3:] if len(val) > 7 else val
            
            ident = Identifier(
                case_id=case.id,
                kind=kind,
                role=role,
                value_enc=val_enc,
                value_hash=val_hash,
                raw_preview=raw_preview
            )
            session.add(ident)

    # Initial Case Event
    event = CaseEvent(
        case_id=case.id,
        actor_type="system",
        event="CASE_REGISTERED",
        to_status="NEW",
        note=f"Complaint registered via citizen interface. Urgency: {urgency}"
    )
    session.add(event)

    # Cryptographic Audit Log
    await append_audit_entry(
        session,
        actor_type="system",
        actor_id=reporter_id,
        action="CREATE_CASE",
        entity="Case",
        entity_id=case.id,
        details={"ref_no": ref_no, "urgency": urgency, "category": category}
    )

    await session.commit()
    await session.refresh(case)
    return case


async def get_decrypted_case(session: AsyncSession, case_id: str) -> Optional[Dict[str, Any]]:
    stmt = select(Case).where(Case.id == case_id)
    res = await session.execute(stmt)
    case = res.scalar_one_or_none()
    if not case:
        return None

    # Decrypt payload
    data_str = decrypt_field(case.data_enc)
    try:
        data_dict = json.loads(data_str)
    except Exception:
        data_dict = {}

    return {
        "id": case.id,
        "ref_no": case.ref_no,
        "category": case.category,
        "subtype": case.subtype,
        "status": case.status,
        "urgency": case.urgency,
        "amount_inr": case.amount_inr,
        "incident_at": case.incident_at.isoformat() if case.incident_at else None,
        "reported_at": case.reported_at.isoformat() if case.reported_at else None,
        "language": case.language,
        "confidence": case.confidence_json,
        "flags": case.flags_json,
        "details": data_dict
    }

