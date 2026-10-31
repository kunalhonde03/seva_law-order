"""Recorded and Heuristic Fallback LLM Provider.

Provides instant, 100% deterministic, offline responses for known demo scripts
and performs rule-based entity extraction for novel inputs without cloud API keys.
"""

import json
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from backend.app.llm.base import BaseLLMProvider
from backend.app.extraction.safety import classify_safety_rules


class RecordedLLMProvider(BaseLLMProvider):
    async def classify_crisis(self, text: str) -> Dict[str, Any]:
        return classify_safety_rules(text)

    async def extract_complaint(
        self,
        transcript: str,
        language: str,
        system_time_iso: str
    ) -> Dict[str, Any]:
        crisis_data = classify_safety_rules(transcript)
        lower = transcript.lower()

        # Heuristic 1: Detect subtype
        subtype = "other"
        category = "fraud"

        if "महावितरण" in transcript or "msedcl" in lower or "वीज बिल" in transcript or "electricity" in lower:
            subtype = "kyc_sim_scam"
            category = "fraud"
            claimed_id = "MSEDCL Electricity Official"
        elif "pension" in lower or "जीवन प्रमाण" in transcript or "life certificate" in lower:
            subtype = "otp_impersonation"
            category = "fraud"
            claimed_id = "SBI Pension Treasury Officer"
        elif "telegram" in lower or "youtube video" in lower or "part time job" in lower or "task" in lower:
            subtype = "task_job_scam"
            category = "fraud"
            claimed_id = "Part-Time Task Coordinator"
        elif "fedex" in lower or "customs" in lower or "digital arrest" in lower or "mdma" in lower:
            subtype = "digital_arrest"
            category = "fraud"
            claimed_id = "Mumbai Crime Branch / CBI Inspector"
        elif "video call" in lower or "morphed" in lower or "nude" in lower or "sextortion" in lower:
            subtype = "sextortion"
            category = "extortion"
            claimed_id = "Cyber Police Blackmailer"
        elif "loan" in lower or "कर्ज" in transcript or "rupee" in lower:
            subtype = "loan_app_harassment"
            category = "extortion"
            claimed_id = "Predatory Loan App Recovery Agent"
        elif "olx" in lower or "qr code" in lower or "सोफा" in transcript:
            subtype = "upi_collect_scam"
            category = "fraud"
            claimed_id = "Marketplace Buyer Impersonator"
        elif "stock" in lower or "trading" in lower or "crypto" in lower:
            subtype = "investment_scam"
            category = "fraud"
            claimed_id = "Investment Advisor Impersonator"
        else:
            claimed_id = "Unknown Caller"

        # Heuristic 2: Extract Amount
        amount = None
        evidence_amount = None
        amt_match = re.search(r"(?:₹|rs\.?|inr|रुपये|रु\.?)\s*([\d,]+(?:\.\d+)?)", transcript, re.IGNORECASE)
        if amt_match:
            try:
                raw_amt = amt_match.group(1).replace(",", "")
                amount = float(raw_amt)
                evidence_amount = amt_match.group(0)
            except ValueError:
                pass
        
        if not amount:
            if "1 lakh" in lower or "१ लाख" in transcript or "1,00,000" in transcript:
                amount = 100000.0
                evidence_amount = "1 lakh"
            elif "50,000" in transcript or "५०,०००" in transcript or "fifty thousand" in lower:
                amount = 50000.0
                evidence_amount = "50,000"
            elif "1,20,000" in transcript or "1.2 lakh" in lower:
                amount = 120000.0
                evidence_amount = "1,20,000"
            elif "4,50,000" in transcript or "4.5 lakh" in lower:
                amount = 450000.0
                evidence_amount = "4,50,000"
            elif "10,000" in transcript or "१०,०००" in transcript:
                amount = 10000.0
                evidence_amount = "10,000"
            elif "45,000" in transcript:
                amount = 45000.0 if category == "fraud" else 0.0
                evidence_amount = "45,000 demanded"

        # Heuristic 3: Extract Identifiers
        suspect_ids: List[Dict[str, str]] = []
        # Phone
        phones = re.findall(r"(?:\+91[\s-]?)?[6789]\d{9}\b", transcript)
        for ph in set(phones):
            clean_ph = re.sub(r"[\s-]", "", ph)
            if not clean_ph.startswith("+91"):
                clean_ph = "+91" + clean_ph
            suspect_ids.append({"kind": "phone", "value": clean_ph, "role": "suspect"})

        # UPI
        upis = re.findall(r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}", transcript)
        for u in set(upis):
            suspect_ids.append({"kind": "upi", "value": u, "role": "beneficiary"})

        # Bank Mention
        victim_bank = None
        for b_name in ["Bank of Maharashtra", "State Bank of India", "SBI", "HDFC Bank", "ICICI Bank", "Kotak Mahindra Bank", "Axis Bank"]:
            if b_name.lower() in lower or b_name in transcript:
                victim_bank = b_name
                break

        # Transaction ID / UTR
        utrs: List[str] = []
        utr_matches = re.findall(r"\b\d{12}\b", transcript)
        for utr in utr_matches:
            utrs.append(utr)

        # Incident Time
        now = datetime.now(timezone.utc)
        incident_time_iso = (now - timedelta(minutes=20)).isoformat()
        is_golden_hour = True

        if "kal" in lower or "yesterday" in lower or "three weeks" in lower or "seven days" in lower:
            incident_time_iso = (now - timedelta(hours=24)).isoformat()
            is_golden_hour = False

        missing_fields: List[str] = []
        if amount is None:
            missing_fields.append("amount_inr")
        if not utrs and category == "fraud":
            missing_fields.append("transaction_ids")
        if not victim_bank and category == "fraud":
            missing_fields.append("victim_bank")

        # Local narrative
        if language == "mr":
            narrative_local = f"तक्रारदाराने {subtype} संदर्भात फसवणूक झाल्याची तक्रार नोंदवली आहे. संशयिताने ₹{amount if amount else 0} ची रक्कम बेकायदेशीरपणे वळवली किंवा मागणी केली."
        elif language == "hi":
            narrative_local = f"पीड़ित ने {subtype} के संबंध में साइबर अपराध की सूचना दी है। संदिग्ध द्वारा ₹{amount if amount else 0} की ठगी या मांग की गई है।"
        else:
            narrative_local = f"Victim reported an incident of {subtype}. Suspect unlawfully transferred or demanded ₹{amount if amount else 0}."

        narrative_en = f"Victim reported an incident of {subtype}. Suspect unlawfully transferred or demanded ₹{amount if amount else 0}."

        return {
            "category": category,
            "subtype": subtype,
            "incident_time": {
                "value": incident_time_iso,
                "precision": "approx",
                "evidence": "Reported relative time"
            },
            "amount_inr": {
                "value": amount,
                "evidence": evidence_amount
            },
            "payment_method": "upi" if ("upi" in lower or "google pay" in lower or "phonepe" in lower) else "netbanking",
            "victim_bank": victim_bank,
            "transaction_ids": utrs,
            "contact_channel": "call" if "call" in lower or "फोन" in transcript else "whatsapp",
            "suspect_identifiers": suspect_ids,
            "claimed_identity": claimed_id,
            "narrative_local": narrative_local,
            "narrative_en": narrative_en,
            "flags": {
                "money_moved_recently": is_golden_hour,
                "minor_involved": crisis_data["minor_involved"],
                "self_harm_risk": crisis_data["self_harm_risk"],
                "intimate_images_involved": crisis_data["intimate_images_involved"]
            },
            "missing_fields": missing_fields,
            "field_confidence": {
                "amount_inr": 0.95 if amount else 0.0,
                "incident_time": 0.90,
                "suspect_identifiers": 0.95 if suspect_ids else 0.50
            }
        }
