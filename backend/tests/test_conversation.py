"""Integration tests for Conversation Engine & State Transitions."""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.app.db.models import Base
from backend.app.conversation.engine import process_user_input
from backend.app.conversation.states import ConvState

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.mark.asyncio
async def test_full_intake_to_submission_flow():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        phone = "+919988776655"

        # Step 1: Initial Prompt -> Select Language Marathi
        r1 = await process_user_input(session, phone_number=phone)
        assert r1.state == ConvState.LANG_SELECT.value

        # Step 2: Choose Marathi -> Expect Consent Prompt
        r2 = await process_user_input(session, phone_number=phone, button_payload="lang_mr")
        assert r2.state == ConvState.CONSENT.value

        # Step 3: Consent Agree -> Expect Main Menu
        r3 = await process_user_input(session, phone_number=phone, button_payload="consent_agree")
        assert r3.state == ConvState.MENU.value

        # Step 4: Click Report Fraud -> Expect Voice Prompt
        r4 = await process_user_input(session, phone_number=phone, button_payload="menu_fraud")
        assert r4.state == ConvState.FRAUD_PROMPT_VOICE.value

        # Step 5: Send Voice Transcript -> Expect Readback & CONFIRM state
        marathi_statement = "मला आज दुपारी अडीच वाजता महावितरण वीज बिलासाठी फोन आला आणि बँक ऑफ महाराष्ट्र खात्यातून ५०,००० रुपये कापले गेले. UTR 429182736152 आहे."
        r5 = await process_user_input(session, phone_number=phone, text_content=marathi_statement)
        assert r5.state == ConvState.CONFIRM.value

        # Step 6: Confirm Yes -> Expect Case Creation & Reference Number
        r6 = await process_user_input(session, phone_number=phone, button_payload="confirm_yes")
        assert r6.state == ConvState.AFTERCARE.value
        assert r6.case_ref is not None
        assert r6.case_ref.startswith("SV-")
        assert r6.golden_hour is True
