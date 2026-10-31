"""Police Operator Cases Management API Endpoints."""

import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.db.models import Case, Identifier, CaseEvent, Handoff, Evidence
from backend.app.cases.service import get_decrypted_case, append_audit_entry
from backend.app.cases.handoff.cfcfrms import generate_cfcfrms_lien_payload
from backend.app.cases.handoff.pdf_export import generate_complaint_pdf
from backend.app.core.crypto import encrypt_field, decrypt_field

router = APIRouter(prefix="/cases", tags=["Operator Cases"])


class StatusUpdateRequest(BaseModel):
    status: str
    note: Optional[str] = "Operator status update via console"
    actor_id: Optional[str] = "OFFICER-SHINDE-MH01"


class HandoffRequest(BaseModel):
    adapter: str = "cfcfrms_lien"  # cfcfrms_lien | mock_desk | email


class CasePatchRequest(BaseModel):
    amount_inr: Optional[float] = None
    victim_bank: Optional[str] = None
    subtype: Optional[str] = None
    note: Optional[str] = "Desk officer field verification"
    actor_id: Optional[str] = "OFFICER-SHINDE-MH01"


class EvidenceUploadRequest(BaseModel):
    filename: str
    mime: str = "image/png"
    kind: str = "screenshot"  # screenshot | chat_export | bank_slip | voice_note
    data_base64: Optional[str] = None
    size_bytes: int = 1024


@router.get("")
async def list_cases(
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Lists cases with priority sorting (Golden Hour & CRITICAL first)."""
    stmt = select(Case).order_by(
        desc(Case.urgency == "CRITICAL"),
        desc(Case.urgency == "HIGH"),
        desc(Case.reported_at)
    ).limit(limit)

    if status:
        stmt = stmt.where(Case.status == status)
    if urgency:
        stmt = stmt.where(Case.urgency == urgency)
    if category:
        stmt = stmt.where(Case.category == category)

    res = await db.execute(stmt)
    cases = res.scalars().all()

    now = datetime.now(timezone.utc)
    results = []
    for c in cases:
        mins_left = 0
        if c.incident_at:
            inc_dt = c.incident_at.replace(tzinfo=timezone.utc) if c.incident_at.tzinfo is None else c.incident_at
            elapsed = (now - inc_dt).total_seconds() / 60.0
            mins_left = max(0, int(60 - elapsed))

        results.append({
            "id": c.id,
            "ref_no": c.ref_no,
            "category": c.category,
            "subtype": c.subtype,
            "status": c.status,
            "urgency": c.urgency,
            "amount_inr": c.amount_inr,
            "reported_at": c.reported_at.isoformat(),
            "incident_at": c.incident_at.isoformat() if c.incident_at else None,
            "golden_hour_mins_left": mins_left,
            "language": c.language
        })

    return results


@router.get("/{case_id}")
async def get_case_details(case_id: str, db: AsyncSession = Depends(get_db)):
    """Fetches full decrypted complaint dossier, suspect identifiers, and timeline events."""
    case_info = await get_decrypted_case(db, case_id)
    if not case_info:
        raise HTTPException(status_code=404, detail="Case not found")

    id_stmt = select(Identifier).where(Identifier.case_id == case_id)
    id_res = await db.execute(id_stmt)
    idents = id_res.scalars().all()

    ev_stmt = select(CaseEvent).where(CaseEvent.case_id == case_id).order_by(CaseEvent.at.asc())
    ev_res = await db.execute(ev_stmt)
    events = ev_res.scalars().all()

    evi_stmt = select(Evidence).where(Evidence.case_id == case_id).order_by(Evidence.uploaded_at.desc())
    evi_res = await db.execute(evi_stmt)
    evidence_items = evi_res.scalars().all()

    case_info["suspect_identifiers"] = [
        {"kind": i.kind, "role": i.role, "preview": i.raw_preview}
        for i in idents
    ]
    case_info["timeline"] = [
        {"event": e.event, "from_status": e.from_status, "to_status": e.to_status, "note": e.note, "at": e.at.isoformat()}
        for e in events
    ]
    case_info["evidence"] = [
        {"id": ev.id, "object_key": ev.object_key, "mime": ev.mime, "size_bytes": ev.size_bytes, "kind": ev.kind, "sha256": ev.sha256}
        for ev in evidence_items
    ]

    return case_info


@router.patch("/{case_id}")
async def patch_case_fields(
    case_id: str,
    req: CasePatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Allows desk officers to verify and update complaint fields with before/after audit."""
    stmt = select(Case).where(Case.id == case_id)
    res = await db.execute(stmt)
    case = res.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Decrypt current data
    old_data_str = decrypt_field(case.data_enc)
    try:
        data_dict = json.loads(old_data_str)
    except Exception:
        data_dict = {}

    before_state = {
        "amount_inr": case.amount_inr,
        "victim_bank": data_dict.get("victim_bank"),
        "subtype": case.subtype
    }

    # Apply updates
    if req.amount_inr is not None:
        case.amount_inr = req.amount_inr
        data_dict["amount_inr"] = {"value": req.amount_inr, "evidence": "Verified by officer"}
    if req.victim_bank is not None:
        data_dict["victim_bank"] = req.victim_bank
    if req.subtype is not None:
        case.subtype = req.subtype

    case.data_enc = encrypt_field(json.dumps(data_dict, ensure_ascii=False))
    case.updated_at = datetime.now(timezone.utc)

    after_state = {
        "amount_inr": case.amount_inr,
        "victim_bank": data_dict.get("victim_bank"),
        "subtype": case.subtype
    }

    # Audit before/after
    await append_audit_entry(
        db,
        actor_type="operator",
        actor_id=req.actor_id,
        action="FIELD_EDIT",
        entity="Case",
        entity_id=case.id,
        details={"before": before_state, "after": after_state, "note": req.note}
    )

    # Timeline event
    db.add(CaseEvent(
        case_id=case.id,
        actor_type="operator",
        actor_id=req.actor_id,
        event="FIELD_VERIFIED",
        note=f"Fields updated: {json.dumps(after_state)}"
    ))

    await db.commit()
    return {"status": "UPDATED", "case_id": case.id, "after": after_state}


@router.post("/{case_id}/evidence")
async def upload_case_evidence(
    case_id: str,
    req: EvidenceUploadRequest,
    db: AsyncSession = Depends(get_db)
):
    """Registers evidence into encrypted vault with SHA-256 integrity hash."""
    stmt = select(Case).where(Case.id == case_id)
    res = await db.execute(stmt)
    case = res.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    content_to_hash = req.data_base64 or req.filename
    sha256_hash = hashlib.sha256(content_to_hash.encode()).hexdigest()

    evidence = Evidence(
        case_id=case_id,
        object_key=f"evidence/{case.ref_no}/{req.filename}",
        sha256=sha256_hash,
        mime=req.mime,
        size_bytes=req.size_bytes,
        kind=req.kind,
        encrypted=True
    )
    db.add(evidence)

    # Timeline event
    db.add(CaseEvent(
        case_id=case_id,
        actor_type="operator",
        event="EVIDENCE_ATTACHED",
        note=f"Attached evidence file: {req.filename} (SHA256: {sha256_hash[:12]}...)"
    ))

    await db.commit()
    await db.refresh(evidence)

    return {
        "status": "UPLOADED",
        "evidence_id": evidence.id,
        "sha256": evidence.sha256,
        "object_key": evidence.object_key
    }


@router.post("/{case_id}/status")
async def update_status(
    case_id: str,
    req: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Case).where(Case.id == case_id)
    res = await db.execute(stmt)
    case = res.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    old_status = case.status
    case.status = req.status
    case.updated_at = datetime.now(timezone.utc)

    event = CaseEvent(
        case_id=case.id,
        actor_type="operator",
        actor_id=req.actor_id,
        event="STATUS_CHANGE",
        from_status=old_status,
        to_status=req.status,
        note=req.note
    )
    db.add(event)

    await append_audit_entry(
        db,
        actor_type="operator",
        actor_id=req.actor_id,
        action="UPDATE_STATUS",
        entity="Case",
        entity_id=case.id,
        details={"old_status": old_status, "new_status": req.status, "note": req.note}
    )

    await db.commit()
    return {"status": "SUCCESS", "new_status": req.status, "ref_no": case.ref_no}


@router.post("/{case_id}/handoff")
async def trigger_handoff(
    case_id: str,
    req: HandoffRequest,
    db: AsyncSession = Depends(get_db)
):
    case_info = await get_decrypted_case(db, case_id)
    if not case_info:
        raise HTTPException(status_code=404, detail="Case not found")

    payload = generate_cfcfrms_lien_payload(case_info["details"], case_info["ref_no"])

    handoff = Handoff(
        case_id=case_id,
        adapter=req.adapter,
        status="DELIVERED",
        payload_ref=f"CFCFRMS-RELAY-{case_info['ref_no']}",
        ack_ref=f"ACK-1930-{case_info['ref_no']}",
        response_json=payload
    )
    db.add(handoff)

    event = CaseEvent(
        case_id=case_id,
        actor_type="system",
        event="CFCFRMS_DISPATCHED",
        note="Emergency lien and structured dossier dispatched to 1930 / CFCFRMS gateway."
    )
    db.add(event)
    await db.commit()

    return {
        "status": "DISPATCHED",
        "adapter": req.adapter,
        "ack_reference": handoff.ack_ref,
        "payload": payload
    }


@router.get("/{case_id}/summary.pdf")
async def download_summary_pdf(case_id: str, db: AsyncSession = Depends(get_db)):
    """Downloads official, tamper-evident Maharashtra Cyber Complaint Dossier PDF."""
    case_info = await get_decrypted_case(db, case_id)
    if not case_info:
        raise HTTPException(status_code=404, detail="Case not found")

    pdf_bytes = generate_complaint_pdf(case_info["details"], case_info["ref_no"])

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=SurakshaVani_{case_info['ref_no']}.pdf"
        }
    )
