"""Complaint Schema and Typed Models for SurakshaVani Extraction."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class IncidentTime(BaseModel):
    value: Optional[str] = Field(None, description="ISO-8601 formatted timestamp of the incident")
    precision: Literal["exact", "approx", "unknown"] = "unknown"
    evidence: Optional[str] = Field(None, description="Verbatim quote from transcript")


class AmountINR(BaseModel):
    value: Optional[float] = Field(None, description="Financial loss in Indian Rupees")
    evidence: Optional[str] = Field(None, description="Verbatim quote for the loss amount")


class SuspectIdentifier(BaseModel):
    kind: Literal["phone", "upi", "account", "url", "app", "email", "handle"]
    value: str
    role: Literal["suspect", "beneficiary"] = "suspect"


class SafetyFlags(BaseModel):
    money_moved_recently: bool = False
    minor_involved: bool = False
    self_harm_risk: bool = False
    intimate_images_involved: bool = False


class ComplaintSchema(BaseModel):
    category: Literal["fraud", "extortion", "unknown"] = "unknown"
    subtype: Literal[
        "otp_impersonation",
        "investment_scam",
        "task_job_scam",
        "kyc_sim_scam",
        "fake_loan_app",
        "digital_arrest",
        "upi_collect_scam",
        "sextortion",
        "loan_app_harassment",
        "other"
    ] = "other"
    incident_time: IncidentTime = Field(default_factory=IncidentTime)
    amount_inr: AmountINR = Field(default_factory=AmountINR)
    payment_method: Literal["upi", "card", "netbanking", "wallet", "cash", "crypto", "other", "unknown"] = "unknown"
    victim_bank: Optional[str] = None
    transaction_ids: List[str] = Field(default_factory=list)
    contact_channel: Literal["call", "sms", "whatsapp", "social_media", "app", "email", "other"] = "call"
    suspect_identifiers: List[SuspectIdentifier] = Field(default_factory=list)
    claimed_identity: Optional[str] = None
    narrative_local: str = Field(..., description="2-4 sentence neutral summary in user's language")
    narrative_en: str = Field(..., description="Neutral summary in English")
    flags: SafetyFlags = Field(default_factory=SafetyFlags)
    missing_fields: List[str] = Field(default_factory=list)
    field_confidence: dict = Field(default_factory=dict)
