"""Database Seeder for SurakshaVani Prototype."""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from backend.app.db.session import engine, Base, AsyncSessionLocal
from backend.app.db.models import District, User, Reporter, Case, Identifier, CaseEvent, AuditLog
from backend.app.core.crypto import encrypt_field, hmac_hash, compute_audit_hash

DISTRICTS = [
    {"code": "MUM", "name": "Mumbai City", "state": "Maharashtra", "email": "cybercell.mumbai@mahapolice.gov.in"},
    {"code": "PUN", "name": "Pune Urban", "state": "Maharashtra", "email": "cybercell.pune@mahapolice.gov.in"},
    {"code": "NAG", "name": "Nagpur Urban", "state": "Maharashtra", "email": "cybercell.nagpur@mahapolice.gov.in"},
    {"code": "THA", "name": "Thane City", "state": "Maharashtra", "email": "cybercell.thane@mahapolice.gov.in"},
    {"code": "NSK", "name": "Nashik Rural", "state": "Maharashtra", "email": "cybercell.nashik@mahapolice.gov.in"},
    {"code": "CSN", "name": "Chhatrapati Sambhajinagar", "state": "Maharashtra", "email": "cybercell.csn@mahapolice.gov.in"},
]


async def seed_all():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        chk = await session.execute(select(District).limit(1))
        if chk.scalar_one_or_none():
            print("Database already contains data. Skipping re-seed.")
            return

        print("Seeding Maharashtra Districts...")
        district_map = {}
        for d in DISTRICTS:
            obj = District(
                code=d["code"],
                name=d["name"],
                state=d["state"],
                cyber_cell_email=d["email"]
            )
            session.add(obj)
            await session.flush()
            district_map[d["code"]] = obj.id

        print("Seeding Police Desk Users...")
        officer = User(
            email="s.shinde@mahapolice.gov.in",
            name="Insp. Sanjay Shinde",
            role="operator",
            badge_number="MH-CY-8812",
            district_id=district_map["MUM"],
            password_hash="argon2_demo_hash_secured"
        )
        session.add(officer)

        analyst = User(
            email="r.deshmukh@mahapolice.gov.in",
            name="Radhika Deshmukh",
            role="analyst",
            badge_number="MH-CY-4409",
            district_id=district_map["MUM"],
            password_hash="argon2_demo_hash_secured"
        )
        session.add(analyst)
        await session.flush()

        print("Seeding Canonical Case 1 (Golden Hour Marathi MSEDCL Scam)...")
        now = datetime.now(timezone.utc)
        rep1_phone = "+919890011223"
        rep1 = Reporter(
            phone_hash=hmac_hash(rep1_phone),
            phone_enc=encrypt_field(rep1_phone),
            language="mr",
            consent_version="v1.0"
        )
        session.add(rep1)
        await session.flush()

        c1_payload = {
            "category": "fraud",
            "subtype": "kyc_sim_scam",
            "incident_time": {"value": (now - timedelta(minutes=18)).isoformat(), "precision": "exact"},
            "amount_inr": {"value": 50000.0, "evidence": "५०,००० रुपये कट झाले"},
            "payment_method": "upi",
            "victim_bank": "Bank of Maharashtra",
            "transaction_ids": ["429182736152"],
            "contact_channel": "call",
            "suspect_identifiers": [
                {"kind": "phone", "value": "+919823412345", "role": "suspect"},
                {"kind": "upi", "value": "msedcl-billpay@axisbank", "role": "beneficiary"}
            ],
            "claimed_identity": "MSEDCL Electricity Official",
            "narrative_local": "तक्रारदाराला महावितरण वीज बिल थकल्याचे सांगून वीज कापण्याची भीती दाखवण्यात आली आणि ॲपद्वारे ५०,००० रुपयांची सायबर फसवणूक करण्यात आली.",
            "narrative_en": "Victim was intimidated by a fake MSEDCL electricity official threatening immediate power cutoff, resulting in unauthorized debit of INR 50,000 from Bank of Maharashtra.",
            "flags": {"money_moved_recently": True, "minor_involved": False, "self_harm_risk": False, "intimate_images_involved": False},
            "field_confidence": {"amount_inr": 0.98, "incident_time": 0.95}
        }

        case1 = Case(
            ref_no=f"SV-{now.strftime('%Y%m')}-MUM-0912",
            reporter_id=rep1.id,
            category="fraud",
            subtype="kyc_sim_scam",
            status="NEW",
            urgency="CRITICAL",
            incident_at=now - timedelta(minutes=18),
            reported_at=now,
            amount_inr=50000.0,
            district_id=district_map["MUM"],
            language="mr",
            data_enc=encrypt_field(json.dumps(c1_payload)),
            confidence_json={"amount_inr": 0.98, "incident_time": 0.95},
            flags_json=c1_payload["flags"]
        )
        session.add(case1)
        await session.flush()

        # Identifiers
        session.add(Identifier(
            case_id=case1.id,
            kind="phone",
            role="suspect",
            value_enc=encrypt_field("+919823412345"),
            value_hash=hmac_hash("+919823412345"),
            raw_preview="+91 9823***345"
        ))
        session.add(Identifier(
            case_id=case1.id,
            kind="upi",
            role="beneficiary",
            value_enc=encrypt_field("msedcl-billpay@axisbank"),
            value_hash=hmac_hash("msedcl-billpay@axisbank"),
            raw_preview="msedcl***@axisbank"
        ))

        # Event
        session.add(CaseEvent(
            case_id=case1.id,
            actor_type="system",
            event="CASE_REGISTERED",
            to_status="NEW",
            note="Urgent Golden Hour case: 18 minutes elapsed since transfer."
        ))

        print("Seeding Canonical Case 2 (Senior Pension OTP Impersonation)...")
        rep2_phone = "+919811223344"
        rep2 = Reporter(
            phone_hash=hmac_hash(rep2_phone),
            phone_enc=encrypt_field(rep2_phone),
            language="hi",
            consent_version="v1.0"
        )
        session.add(rep2)
        await session.flush()

        c2_payload = {
            "category": "fraud",
            "subtype": "otp_impersonation",
            "incident_time": {"value": (now - timedelta(minutes=35)).isoformat(), "precision": "exact"},
            "amount_inr": {"value": 120000.0, "evidence": "1,20,000 rupaye nikal gaye"},
            "payment_method": "netbanking",
            "victim_bank": "State Bank of India",
            "transaction_ids": ["SBI908123456"],
            "contact_channel": "call",
            "suspect_identifiers": [
                {"kind": "phone", "value": "+918877112233", "role": "suspect"}
            ],
            "claimed_identity": "SBI Treasury Pension Officer",
            "narrative_local": "वरिष्ठ नागरिक को जीवन प्रमाण पत्र एक्सपायर होने का झांसा देकर ओटीपी लेकर 1,20,000 रुपये निकाल लिए गए।",
            "narrative_en": "Elderly pensioner was tricked into revealing OTP under the pretext of life certificate renewal, losing INR 1,20,000 from SBI.",
            "flags": {"money_moved_recently": True, "minor_involved": False, "self_harm_risk": False, "intimate_images_involved": False},
            "field_confidence": {"amount_inr": 0.95, "incident_time": 0.92}
        }

        case2 = Case(
            ref_no=f"SV-{now.strftime('%Y%m')}-MUM-0894",
            reporter_id=rep2.id,
            category="fraud",
            subtype="otp_impersonation",
            status="UNDER_REVIEW",
            urgency="CRITICAL",
            incident_at=now - timedelta(minutes=35),
            reported_at=now - timedelta(minutes=10),
            amount_inr=120000.0,
            district_id=district_map["MUM"],
            language="hi",
            data_enc=encrypt_field(json.dumps(c2_payload)),
            confidence_json={"amount_inr": 0.95, "incident_time": 0.92},
            flags_json=c2_payload["flags"]
        )
        session.add(case2)
        await session.flush()

        session.add(Identifier(
            case_id=case2.id,
            kind="phone",
            role="suspect",
            value_enc=encrypt_field("+918877112233"),
            value_hash=hmac_hash("+918877112233"),
            raw_preview="+91 8877***233"
        ))

        # Initial Audit Log Entry
        audit = AuditLog(
            actor_type="system",
            action="SYSTEM_INIT_SEED",
            entity="Database",
            prev_hash="GENESIS_BLOCK_SURAKSHAVANI_2026",
            hash=compute_audit_hash("GENESIS_BLOCK_SURAKSHAVANI_2026", {"action": "SYSTEM_INIT_SEED"})
        )
        session.add(audit)

        await session.commit()
        print("Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_all())

