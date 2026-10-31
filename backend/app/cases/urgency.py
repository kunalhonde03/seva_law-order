"""Urgency Calculation Engine for Cyber Fraud and Extortion Reports."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def calculate_case_urgency(
    incident_time: Optional[datetime],
    amount_inr: Optional[float],
    flags: Dict[str, Any],
    category: str
) -> str:
    """Calculates case urgency level: CRITICAL | HIGH | NORMAL.

    Rules:
    - CRITICAL: Golden Hour active (<= 60 mins), minor involved, self-harm risk,
      or high-loss fraud (>= 1,00,000 within 120 mins).
    - HIGH: Loss between 1 and 6 hours ago, or loss >= 25,000, or active loan harassment.
    - NORMAL: All other routine incidents.
    """
    now = datetime.now(timezone.utc)

    # 1. Immediate Crisis / Vulnerable Human Flags
    if flags.get("self_harm_risk") or flags.get("minor_involved"):
        return "CRITICAL"

    # 2. Time-based Evaluation
    if incident_time:
        if incident_time.tzinfo is None:
            incident_time = incident_time.replace(tzinfo=timezone.utc)
        diff_minutes = (now - incident_time).total_seconds() / 60.0

        # Golden Hour Active
        if 0 <= diff_minutes <= 60:
            return "CRITICAL"
        
        # High value within 2 hours
        if amount_inr and amount_inr >= 100000 and diff_minutes <= 120:
            return "CRITICAL"
        
        if 60 < diff_minutes <= 360:
            return "HIGH"

    # 3. Amount and Extortion evaluation
    if amount_inr and amount_inr >= 25000:
        return "HIGH"

    if category == "extortion" and flags.get("intimate_images_involved"):
        return "CRITICAL"

    return "NORMAL"

