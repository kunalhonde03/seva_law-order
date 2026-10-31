"""Unit tests for Urgency and Golden Hour Threshold Rules."""

from datetime import datetime, timezone, timedelta
from backend.app.cases.urgency import calculate_case_urgency


def test_golden_hour_critical():
    now = datetime.now(timezone.utc)
    # Incident 25 minutes ago
    inc_time = now - timedelta(minutes=25)
    urgency = calculate_case_urgency(
        incident_time=inc_time,
        amount_inr=50000.0,
        flags={"money_moved_recently": True},
        category="fraud"
    )
    assert urgency == "CRITICAL"


def test_crisis_self_harm_critical():
    urgency = calculate_case_urgency(
        incident_time=None,
        amount_inr=0.0,
        flags={"self_harm_risk": True},
        category="extortion"
    )
    assert urgency == "CRITICAL"


def test_delayed_report_high_urgency():
    now = datetime.now(timezone.utc)
    # Incident 3 hours ago with high value
    inc_time = now - timedelta(hours=3)
    urgency = calculate_case_urgency(
        incident_time=inc_time,
        amount_inr=150000.0,
        flags={},
        category="fraud"
    )
    assert urgency == "HIGH"


def test_minor_sextortion_critical():
    urgency = calculate_case_urgency(
        incident_time=None,
        amount_inr=0.0,
        flags={"minor_involved": True, "intimate_images_involved": True},
        category="extortion"
    )
    assert urgency == "CRITICAL"

