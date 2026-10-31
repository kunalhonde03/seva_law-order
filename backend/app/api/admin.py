"""Admin Endpoints for Audit Chaining and DPDP Data Retention."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.db.models import AuditLog, User
from backend.app.retention.jobs import run_retention_purge_job

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/audit")
async def get_audit_trail(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Retrieves immutable, hash-chained audit log entries."""
    stmt = select(AuditLog).order_by(desc(AuditLog.at)).limit(limit)
    res = await db.execute(stmt)
    logs = res.scalars().all()

    return [
        {
            "id": log.id,
            "at": log.at.isoformat(),
            "actor_type": log.actor_type,
            "actor_id": log.actor_id,
            "action": log.action,
            "entity": log.entity,
            "entity_id": log.entity_id,
            "details": log.details_json,
            "prev_hash": log.prev_hash,
            "hash": log.hash
        }
        for log in logs
    ]


@router.get("/users")
async def list_admin_users(db: AsyncSession = Depends(get_db)):
    """Lists registered operators, analysts, and admins."""
    stmt = select(User).order_by(User.name)
    res = await db.execute(stmt)
    users = res.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "badge_number": u.badge_number,
            "active": u.active
        }
        for u in users
    ]


@router.post("/retention/run")
async def trigger_retention_purge(db: AsyncSession = Depends(get_db)):
    """Manually triggers the DPDP retention purge worker."""
    result = await run_retention_purge_job(db)
    return result
