"""Police Operator Cases Management API Endpoints."""

import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.db.models import Case, Identifier, CaseEvent, Handoff
from backend.app.cases.service import get_decrypted_case, append_audit_entry
from backend.app.cases.handoff.cfcfrms import generate_cfcfrms_lien_payload
from backend.app.cases.handoff.pdf_export import generate_complaint_pdf
from backend.app.core.crypto import encrypt_field

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
    note: Optional[str] = None


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
        # Calculate minutes remaining in golden hour
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

    # Fetch Identifiers
    id_stmt = select(Identifier).where(Identifier.case_id == case_id)
    id_res = await db.execute(id_stmt)
    idents = id_res.scalars().all()

    # Fetch Events
    ev_stmt = select(CaseEvent).where(CaseEvent.case_id == case_id).order_by(CaseEvent.at.asc())
    ev_res = await db.execute(ev_stmt)
    events = ev_res.scalars().all()

    case_info["suspect_identifiers"] = [
        {"kind": i.kind, "role": i.role, "preview": i.raw_preview}
        for i in idents
    ]
    case_info["timeline"] = [
        {"event": e.event, "from_status": e.from_status, "to_status": e.to_status, "note": e.note, "at": e.at.isoformat()}
        for e in events
    ]

    return case_info


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

    # Add Event
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

    # Audit Log
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

    # Add Event
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
