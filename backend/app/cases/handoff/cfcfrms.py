"""CFCFRMS and 1930 Emergency Lien Handoff Adapter.

Formats pre-filled, compliant dispatch messages for the National Cybercrime Portal,
Nodal Bank Officers, and Maharashtra Cyber Desk.
"""

from datetime import datetime, timezone
from typing import Any, Dict


def generate_cfcfrms_lien_payload(case_data: Dict[str, Any], ref_no: str) -> Dict[str, Any]:
    """Generates standardized Emergency Freeze / Lien Request for CFCFRMS."""
    amt = case_data.get("amount_inr", {}).get("value", 0) or 0
    utrs = case_data.get("transaction_ids", [])
    suspect_ids = case_data.get("suspect_identifiers", [])
    
    suspect_phones = [s["value"] for s in suspect_ids if s.get("kind") == "phone"]
    suspect_upis = [s["value"] for s in suspect_ids if s.get("kind") == "upi"]
    suspect_accounts = [s["value"] for s in suspect_ids if s.get("kind") == "account"]

    notice_text = (
        f"URGENT LIEN REQUEST UNDER CFCFRMS / BNSS 2023\n"
        f"INCIDENT REF: {ref_no}\n"
        f"DATE/TIME: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"CATEGORY: FINANCIAL CYBER FRAUD (GOLDEN HOUR ACTIVE)\n"
        f"DISPUTED AMOUNT: INR {amt:,.2f}\n"
        f"SOURCE BANK: {case_data.get('victim_bank', 'Reported via Victim')}\n"
        f"TRANSACTION UTR / REF: {', '.join(utrs) if utrs else 'PENDING BANK STATEMENT'}\n"
        f"BENEFICIARY UPI / ACCOUNT: {', '.join(suspect_upis + suspect_accounts) if (suspect_upis or suspect_accounts) else 'NOT DISCLOSED'}\n"
        f"SUSPECT CONTACT: {', '.join(suspect_phones) if suspect_phones else 'N/A'}\n"
        f"ACTION MANDATED: Place immediate emergency administrative freeze on beneficiary wallet/account "
        f"to prevent ATM withdrawal or secondary mule routing."
    )

    return {
        "status": "READY_FOR_DISPATCH",
        "reference_id": ref_no,
        "urgency": "CRITICAL" if case_data.get("flags", {}).get("money_moved_recently") else "HIGH",
        "target_gateway": "I4C_CFCFRMS_RELAY",
        "notice_text": notice_text,
        "structured_entities": {
            "amount": amt,
            "utrs": utrs,
            "suspect_phones": suspect_phones,
            "suspect_upis": suspect_upis,
            "victim_bank": case_data.get("victim_bank")
        }
    }

