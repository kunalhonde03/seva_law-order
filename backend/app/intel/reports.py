"""Weekly Police Leads & Financial Crime Intelligence Report Generator."""

from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import Case, Identifier, Cluster


async def generate_weekly_leads_report(session: AsyncSession) -> Dict[str, Any]:
    """Compiles high-priority leads for Maharashtra Cyber Cell and I4C."""
    # 1. Total statistics
    case_count_res = await session.execute(select(func.count(Case.id)))
    total_cases = case_count_res.scalar() or 0

    total_amount_res = await session.execute(select(func.sum(Case.amount_inr)))
    total_siphoned = total_amount_res.scalar() or 0.0

    # 2. Top Subtypes
    subtypes_stmt = (
        select(Case.subtype, func.count(Case.id).label("count"), func.sum(Case.amount_inr).label("loss"))
        .group_by(Case.subtype)
        .order_by(desc("count"))
        .limit(5)
    )
    subtypes_res = await session.execute(subtypes_stmt)
    top_subtypes = [
        {"subtype": row[0], "case_count": row[1], "total_loss_inr": float(row[2] or 0.0)}
        for row in subtypes_res.all()
    ]

    # 3. Repeat Identifiers (Highest Risk Suspects)
    id_stmt = (
        select(Identifier.raw_preview, Identifier.kind, func.count(Identifier.id).label("freq"))
        .group_by(Identifier.raw_preview, Identifier.kind)
        .order_by(desc("freq"))
        .limit(10)
    )
    id_res = await session.execute(id_stmt)
    repeat_identifiers = [
        {"identifier_preview": row[0], "kind": row[1], "frequency": row[2]}
        for row in id_res.all()
    ]

    # 4. Actionable Intelligence Directives
    return {
        "report_id": f"LEADS-{datetime.now(timezone.utc).strftime('%Y-W%W')}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "jurisdiction": "Maharashtra Cyber Crime Directorate",
        "total_cases_analyzed": total_cases,
        "total_financial_loss_inr": float(total_siphoned),
        "top_emerging_scam_scripts": top_subtypes,
        "critical_suspect_leads": repeat_identifiers,
        "operational_recommendations": [
            "Initiate Section 91 CrPC bulk freeze requests for repeat beneficiary UPIs.",
            "Liaise with DoT Western Telecom Circle for expedited IMEI/SIM revocation of serial scam callers.",
            "Broadcast targeted cyber awareness warning in Pune & Mumbai regarding MSEDCL fake SMS links."
        ]
    }
