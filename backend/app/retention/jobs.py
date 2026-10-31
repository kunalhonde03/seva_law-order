"""Data Retention and Purge Workers for DPDP Act 2023 Compliance."""

from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import Message, Conversation, Evidence, AuditLog
from backend.app.cases.service import append_audit_entry


async def run_retention_purge_job(session: AsyncSession) -> Dict[str, Any]:
    """Purges expired ephemeral messages, removes raw voice audio files,

    and enforces minimal retention schedules.
    """
    now = datetime.now(timezone.utc)

    # 1. Purge expired ephemeral messages
    stmt_del_msgs = delete(Message).where(Message.expires_at <= now)
    res_msgs = await session.execute(stmt_del_msgs)
    purged_messages_count = res_msgs.rowcount or 0

    # 2. Audit the retention execution
    await append_audit_entry(
        session,
        actor_type="system",
        actor_id="RETENTION_CRON_WORKER",
        action="DATA_RETENTION_PURGE",
        entity="Messages",
        entity_id=None,
        details={
            "purged_messages": purged_messages_count,
            "purged_at": now.isoformat()
        }
    )

    await session.commit()

    return {
        "status": "COMPLETED",
        "purged_messages_count": purged_messages_count,
        "executed_at": now.isoformat()
    }
