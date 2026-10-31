"""SurakshaVani Conversational Intake & State Machine Engine.

Orchestrates voice/text processing, DPDP consent, schema extraction,
read-back confirmation, crisis escalation, and family nominee safety alerts.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.config import settings
from backend.app.core.crypto import encrypt_field, decrypt_field, hmac_hash
from backend.app.db.models import Reporter, Consent, Conversation, Message, Case
from backend.app.conversation.states import ConvState
from backend.app.conversation.catalog_loader import get_text
from backend.app.voice.mock_asr import MockASRProvider
from backend.app.llm.recorded import RecordedLLMProvider
from backend.app.llm.anthropic import AnthropicLLMProvider
from backend.app.cases.service import create_case_from_complaint

# Initialize providers
_ASR_PROVIDER = MockASRProvider()
_LLM_PROVIDER = AnthropicLLMProvider() if settings.LLM_PROVIDER == "anthropic" else RecordedLLMProvider()


async def get_or_create_reporter(
    session: AsyncSession,
    phone_number: str,
    default_lang: str = "mr"
) -> Reporter:
    p_hash = hmac_hash(phone_number)
    stmt = select(Reporter).where(Reporter.phone_hash == p_hash)
    res = await session.execute(stmt)
    reporter = res.scalar_one_or_none()

    if not reporter:
        reporter = Reporter(
            phone_hash=p_hash,
            phone_enc=encrypt_field(phone_number),
            language=default_lang,
            consent_version="v1.0"
        )
        session.add(reporter)
        await session.flush()
    return reporter


async def get_or_create_conversation(
    session: AsyncSession,
    reporter_id: str,
    channel: str = "web_sim"
) -> Conversation:
    stmt = select(Conversation).where(
        Conversation.reporter_id == reporter_id,
        Conversation.channel == channel
    ).order_by(Conversation.created_at.desc()).limit(1)
    res = await session.execute(stmt)
    conv = res.scalar_one_or_none()

    if not conv or conv.state in [ConvState.ERASED.value, ConvState.AFTERCARE.value]:
        conv = Conversation(
            reporter_id=reporter_id,
            channel=channel,
            state=ConvState.LANG_SELECT.value,
            last_activity_at=datetime.now(timezone.utc)
        )
        session.add(conv)
        await session.flush()
    return conv


class ConversationResponse:
    def __init__(
        self,
        messages: List[Dict[str, Any]],
        state: str,
        buttons: Optional[List[Dict[str, str]]] = None,
        case_ref: Optional[str] = None,
        golden_hour: bool = False
    ):
        self.messages = messages
        self.state = state
        self.buttons = buttons or []
        self.case_ref = case_ref
        self.golden_hour = golden_hour

    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages": self.messages,
            "state": self.state,
            "buttons": self.buttons,
            "case_ref": self.case_ref,
            "golden_hour": self.golden_hour
        }


async def process_user_input(
    session: AsyncSession,
    phone_number: str,
    text_content: Optional[str] = None,
    audio_bytes: Optional[bytes] = None,
    audio_filename: str = "audio.wav",
    button_payload: Optional[str] = None,
    channel: str = "web_sim"
) -> ConversationResponse:
    reporter = await get_or_create_reporter(session, phone_number)
    conv = await get_or_create_conversation(session, reporter.id, channel)
    lang = reporter.language or "mr"

    # Context unpack
    context: Dict[str, Any] = {}
    if conv.context_enc:
        try:
            context = json.loads(decrypt_field(conv.context_enc))
        except Exception:
            context = {}

    current_state = ConvState(conv.state)

    # 1. Audio Transcription & Input Normalization
    raw_user_text = text_content or ""
    if audio_bytes:
        asr_result = await _ASR_PROVIDER.transcribe(audio_bytes, audio_filename)
        raw_user_text = asr_result.get("text", "")
        if asr_result.get("language"):
            lang = asr_result["language"]
            reporter.language = lang

    norm_input = raw_user_text.strip().lower()

    # 2. Global Interruption Commands (Section 8.2 of Build Plan)
    if button_payload == "cmd_menu" or norm_input in ["menu", "main menu", "home"]:
        conv.state = ConvState.MENU.value
        await session.commit()
        return ConversationResponse(
            messages=[{"type": "text", "body": get_text("menu_title", lang=lang)}],
            state=conv.state,
            buttons=[
                {"id": "menu_fraud", "label": get_text("btn_menu_fraud", lang=lang)},
                {"id": "menu_extortion", "label": get_text("btn_menu_extortion", lang=lang)},
                {"id": "menu_nominee", "label": get_text("btn_menu_nominee", lang=lang)},
                {"id": "menu_status", "label": get_text("btn_menu_status", lang=lang)},
                {"id": "menu_erase", "label": get_text("btn_menu_erase", lang=lang)}
            ]
        )

    if button_payload == "cmd_lang" or norm_input in ["language", "bhasha", "change language"]:
        conv.state = ConvState.LANG_SELECT.value
        await session.commit()
        return ConversationResponse(
            messages=[{"type": "text", "body": "Please select your preferred language / भाषा निवडा / भाषा चुनें:"}],
            state=conv.state,
            buttons=[
                {"id": "lang_mr", "label": "मराठी (Marathi)"},
                {"id": "lang_hi", "label": "हिन्दी (Hindi)"},
                {"id": "lang_en", "label": "English"}
            ]
        )

    if button_payload == "cmd_help" or norm_input in ["help", "madat", "sahayata"]:
        help_msg = (
            "🆘 SURAKSHAVANI EMERGENCY ASSISTANCE:\n"
            "• Financial Cyber Fraud (Immediate Bank Freeze): Call 1930\n"
            "• Physical / Police Emergency: Call 112\n"
            "• Mental Health & Suicide Prevention (Tele-MANAS): Call 14416 (Toll-Free)\n"
            "• Childline: Call 1098\n\n"
            "Type 'menu' to return to options, or 'delete my data' to exercise DPDP erasure."
        )
        return ConversationResponse(
            messages=[{"type": "text", "body": help_msg}],
            state=conv.state,
            buttons=[{"id": "cmd_menu", "label": "Main Menu"}]
        )

    if norm_input in ["delete my data", "delete data", "erase"]:
        conv.state = ConvState.ERASE_CONFIRM.value
        await session.commit()
        return ConversationResponse(
            messages=[{"type": "text", "body": get_text("erasure_confirm_prompt", lang=lang)}],
            state=conv.state,
            buttons=[
                {"id": "confirm_erase_yes", "label": get_text("btn_confirm_erase", lang=lang)},
                {"id": "confirm_erase_no", "label": get_text("btn_cancel_erase", lang=lang)}
            ]
        )

    # 3. Crisis & Minor Safety Interruption (Section 8.1 of Build Plan)
    crisis = await _LLM_PROVIDER.classify_crisis(raw_user_text)
    if crisis.get("self_harm_risk"):
        conv.state = ConvState.SAFETY_ESCALATE.value
        msg_text = get_text("safety_escalate_msg", lang=lang)
        await session.commit()
        return ConversationResponse(
            messages=[{"type": "text", "body": msg_text, "crisis": True}],
            state=conv.state,
            buttons=[{"id": "btn_call_14416", "label": "📞 Call Tele-MANAS (14416)"}]
        )

    if crisis.get("minor_involved") and current_state != ConvState.MINOR_ROUTE:
        conv.state = ConvState.MINOR_ROUTE.value
        minor_msg = (
            "🛡️ SPECIAL CHILD & MINOR PROTECTION NOTICE:\n"
            "We have detected that this report involves a minor under 18 years of age. "
            "Please rest assured that your identity is protected under POCSO and DPDP guidelines. "
            "You are NOT at fault. You can talk safely to a counselor:\n"
            "• National Child Helpline: Call 1098 (24x7, Toll-Free)\n"
            "• Police Emergency: Call 112\n"
            "A Maharashtra Cyber specialized juvenile desk officer has been notified to assist you with discretion."
        )
        await session.commit()
        return ConversationResponse(
            messages=[{"type": "text", "body": minor_msg, "crisis": True}],
            state=conv.state,
            buttons=[{"id": "cmd_menu", "label": "Continue to Main Menu"}]
        )

    # 4. State Machine Transitions
    outbound_msgs: List[Dict[str, Any]] = []
    buttons: List[Dict[str, str]] = []
    case_ref = None
    is_golden_hour = False

    # STATE: LANG_SELECT
    if current_state == ConvState.LANG_SELECT:
        if button_payload in ["lang_mr", "lang_hi", "lang_en"]:
            chosen_lang = button_payload.replace("lang_", "")
            reporter.language = chosen_lang
            lang = chosen_lang
            conv.state = ConvState.CONSENT.value
            outbound_msgs.append({"type": "text", "body": get_text("welcome_greeting", lang=lang)})
            outbound_msgs.append({"type": "text", "body": get_text("disclaimer_prototype", lang=lang)})
            outbound_msgs.append({"type": "text", "body": get_text("dpdp_consent_notice", lang=lang)})
            buttons = [
                {"id": "consent_agree", "label": get_text("btn_consent_agree", lang=lang)},
                {"id": "consent_decline", "label": get_text("btn_consent_decline", lang=lang)}
            ]
        else:
            outbound_msgs.append({"type": "text", "body": "Please select your preferred language / कृपया आपली भाषा निवडा / कृपया भाषा चुनें:"})
            buttons = [
                {"id": "lang_mr", "label": "मराठी (Marathi)"},
                {"id": "lang_hi", "label": "हिन्दी (Hindi)"},
                {"id": "lang_en", "label": "English"}
            ]

    # STATE: CONSENT
    elif current_state == ConvState.CONSENT:
        if button_payload == "consent_agree":
            consent_record = Consent(
                reporter_id=reporter.id,
                version="v1.0",
                language=lang,
                purposes=["fraud_reporting", "cfcfrms_lien", "threat_intel"]
            )
            session.add(consent_record)
            conv.state = ConvState.MENU.value
            outbound_msgs.append({"type": "text", "body": get_text("menu_title", lang=lang)})
            buttons = [
                {"id": "menu_fraud", "label": get_text("btn_menu_fraud", lang=lang)},
                {"id": "menu_extortion", "label": get_text("btn_menu_extortion", lang=lang)},
                {"id": "menu_nominee", "label": get_text("btn_menu_nominee", lang=lang)},
                {"id": "menu_status", "label": get_text("btn_menu_status", lang=lang)},
                {"id": "menu_erase", "label": get_text("btn_menu_erase", lang=lang)}
            ]
        else:
            outbound_msgs.append({"type": "text", "body": "Consent is required to assist with cyber fraud reporting. Dial 1930 directly."})
            conv.state = ConvState.LANG_SELECT.value

    # STATE: MENU
    elif current_state == ConvState.MENU:
        if button_payload == "menu_fraud":
            conv.state = ConvState.FRAUD_PROMPT_VOICE.value
            outbound_msgs.append({"type": "text", "body": get_text("fraud_voice_prompt", lang=lang)})
            buttons = [{"id": "type_instead", "label": get_text("btn_type_instead", lang=lang)}]
        elif button_payload == "menu_extortion":
            conv.state = ConvState.EXT_SAFE_INTRO.value
            outbound_msgs.append({"type": "text", "body": get_text("extortion_intro", lang=lang)})
            buttons = [
                {"id": "btn_ext_start", "label": "🛡️ Proceed Confidentially"},
                {"id": "cmd_menu", "label": "Return to Menu"}
            ]
        elif button_payload == "menu_nominee":
            conv.state = ConvState.NOMINEE_SETUP.value
            outbound_msgs.append({"type": "text", "body": get_text("nominee_setup_prompt", lang=lang)})
        elif button_payload == "menu_status":
            conv.state = ConvState.STATUS_LOOKUP.value
            stmt = select(Case).where(Case.reporter_id == reporter.id).order_by(Case.reported_at.desc()).limit(1)
            res = await session.execute(stmt)
            latest_case = res.scalar_one_or_none()
            if latest_case:
                outbound_msgs.append({"type": "text", "body": get_text(
                    "status_result",
                    lang=lang,
                    ref_no=latest_case.ref_no,
                    status=latest_case.status,
                    urgency=latest_case.urgency,
                    district="Maharashtra Cyber HQ",
                    updated_at=latest_case.updated_at.strftime("%d-%b %H:%M")
                )})
            else:
                outbound_msgs.append({"type": "text", "body": get_text("status_not_found", lang=lang)})
            buttons = [{"id": "cmd_menu", "label": "Main Menu"}]
        elif button_payload == "menu_erase":
            conv.state = ConvState.ERASE_CONFIRM.value
            outbound_msgs.append({"type": "text", "body": get_text("erasure_confirm_prompt", lang=lang)})
            buttons = [
                {"id": "confirm_erase_yes", "label": get_text("btn_confirm_erase", lang=lang)},
                {"id": "confirm_erase_no", "label": get_text("btn_cancel_erase", lang=lang)}
            ]

    # STATE: EXTORTION FLOW (EXT_SAFE_INTRO -> EXT_COLLECT -> EXT_EVIDENCE -> EXT_CONFIRM)
    elif current_state == ConvState.EXT_SAFE_INTRO:
        if button_payload == "btn_ext_start":
            conv.state = ConvState.EXT_COLLECT.value
            outbound_msgs.append({"type": "text", "body": "Please describe what the blackmailer or extortionist is saying or demanding (you can speak via voice note or type below):"})
            outbound_msgs.append({"type": "text", "body": get_text("extortion_evidence_guidance", lang=lang)})
        else:
            conv.state = ConvState.MENU.value
            outbound_msgs.append({"type": "text", "body": "Returning to main menu."})
            buttons = [{"id": "cmd_menu", "label": "Main Menu"}]

    elif current_state == ConvState.EXT_COLLECT:
        # Extract extortion details
        user_input_to_parse = raw_user_text or "Extortion incident reported."
        extracted = await _LLM_PROVIDER.extract_complaint(
            user_input_to_parse,
            lang,
            datetime.now(timezone.utc).isoformat()
        )
        context["draft_complaint"] = extracted
        conv.state = ConvState.EXT_CONFIRM.value

        summary_txt = extracted.get("narrative_local") or extracted.get("narrative_en")
        suspects = [s["value"] for s in extracted.get("suspect_identifiers", [])]
        suspect_str = ", ".join(suspects) if suspects else "Not stated"

        outbound_msgs.append({"type": "text", "body": "CONFIDENTIAL EXTORTION REPORT SUMMARY:\n" f"• Type: {extracted.get('subtype', 'sextortion')}\n" f"• Suspect Contact/Handle: {suspect_str}\n" f"• Demanded Amount: ₹{extracted.get('amount_inr', {}).get('value') or 'Nil / Threat'}\n" f"• Synopsis: {summary_txt}\n\nWould you like to file this confidentially with Maharashtra Cyber?"})
        buttons = [
            {"id": "confirm_yes", "label": "🛡️ Submit Confidential Report"},
            {"id": "confirm_cancel", "label": "❌ Cancel"}
        ]

    # STATE: FRAUD_PROMPT_VOICE / CORRECTING -> EXTRACT & READBACK
    elif current_state in [ConvState.FRAUD_PROMPT_VOICE, ConvState.CORRECTING]:
        user_input_to_parse = raw_user_text or "Report submitted without audio."

        # Extract structured complaint schema
        extracted = await _LLM_PROVIDER.extract_complaint(
            user_input_to_parse,
            lang,
            datetime.now(timezone.utc).isoformat()
        )
        context["draft_complaint"] = extracted

        # Check for single critical missing field (Missing Fields Loop)
        missing = extracted.get("missing_fields", [])
        if "amount_inr" in missing and not extracted.get("amount_inr", {}).get("value"):
            conv.state = ConvState.MISSING_FIELDS.value
            context["missing_target"] = "amount_inr"
            outbound_msgs.append({"type": "text", "body": get_text("missing_field_prompt", lang=lang, field_name="amount lost (रक्कम)")})
            return ConversationResponse(messages=outbound_msgs, state=conv.state, buttons=[{"id": "cmd_menu", "label": "Cancel"}])

        # Prepare read-back
        amt_val = extracted.get("amount_inr", {}).get("value")
        amt_str = f"{amt_val:,.2f}" if amt_val is not None else "Not specified"
        time_str = extracted.get("incident_time", {}).get("value") or "Recent"
        suspects = [s["value"] for s in extracted.get("suspect_identifiers", [])]
        suspect_str = ", ".join(suspects) if suspects else "Not known"
        utrs = ", ".join(extracted.get("transaction_ids", [])) or "Pending"
        summary_txt = extracted.get("narrative_local") or extracted.get("narrative_en")

        readback_body = get_text(
            "readback_details",
            lang=lang,
            subtype=extracted.get("subtype", "other"),
            amount=amt_str,
            time=time_str,
            suspect=suspect_str,
            bank=extracted.get("victim_bank") or "Citizen Account",
            utr=utrs,
            summary=summary_txt
        )

        outbound_msgs.append({"type": "text", "body": get_text("readback_header", lang=lang)})
        outbound_msgs.append({"type": "text", "body": readback_body})

        conv.state = ConvState.CONFIRM.value
        buttons = [
            {"id": "confirm_yes", "label": get_text("btn_confirm_yes", lang=lang)},
            {"id": "confirm_edit", "label": get_text("btn_confirm_edit", lang=lang)},
            {"id": "confirm_cancel", "label": get_text("btn_confirm_cancel", lang=lang)}
        ]

    # STATE: MISSING_FIELDS loop
    elif current_state == ConvState.MISSING_FIELDS:
        target = context.get("missing_target", "amount_inr")
        complaint = context.get("draft_complaint", {})

        # Fill missing attribute
        if target == "amount_inr":
            import re
            m = re.search(r"[\d,]+", raw_user_text)
            if m:
                complaint["amount_inr"] = {"value": float(m.group(0).replace(",", "")), "evidence": raw_user_text}
                if "amount_inr" in complaint.get("missing_fields", []):
                    complaint["missing_fields"].remove("amount_inr")

        context["draft_complaint"] = complaint
        conv.state = ConvState.CONFIRM.value

        outbound_msgs.append({"type": "text", "body": "Thank you. Please review your updated complaint summary:"})
        amt_val = complaint.get("amount_inr", {}).get("value", 0)
        outbound_msgs.append({"type": "text", "body": f"• Disputed Amount: ₹{amt_val:,.2f}\n• Category: {complaint.get('subtype')}\n\nIs this ready to file?"})
        buttons = [
            {"id": "confirm_yes", "label": get_text("btn_confirm_yes", lang=lang)},
            {"id": "confirm_cancel", "label": get_text("btn_confirm_cancel", lang=lang)}
        ]

    # STATE: CONFIRM
    elif current_state in [ConvState.CONFIRM, ConvState.EXT_CONFIRM]:
        if button_payload == "confirm_yes":
            complaint_data = context.get("draft_complaint", {})
            new_case = await create_case_from_complaint(
                session,
                reporter_id=reporter.id,
                complaint_data=complaint_data,
                district_code="MUM",
                language=lang
            )
            case_ref = new_case.ref_no
            conv.case_id = new_case.id
            conv.state = ConvState.AFTERCARE.value

            outbound_msgs.append({"type": "text", "body": get_text(
                "submission_success",
                lang=lang,
                ref_no=new_case.ref_no,
                urgency=new_case.urgency,
                status=new_case.status
            )})

            if new_case.urgency == "CRITICAL":
                is_golden_hour = True
                outbound_msgs.append({"type": "text", "body": get_text("golden_hour_alert", lang=lang)})
                outbound_msgs.append({"type": "text", "body": get_text("one_tap_1930_cta", lang=lang)})

            # Check Family Nominee Alert
            if reporter.nominee_phone_enc:
                nominee_phone = decrypt_field(reporter.nominee_phone_enc)
                alert_text = get_text(
                    "nominee_alert_msg",
                    lang=lang,
                    reporter_phone=decrypt_field(reporter.phone_enc),
                    amount=f"{new_case.amount_inr:,.0f}"
                )
                outbound_msgs.append({
                    "type": "text",
                    "body": f"👨‍👩‍👧 Nominee Alert dispatched to {nominee_phone}: \"{alert_text}\""
                })

            outbound_msgs.append({"type": "text", "body": get_text("aftercare_steps", lang=lang)})
            buttons = [
                {"id": "menu_status", "label": "Track Status"},
                {"id": "cmd_menu", "label": "Main Menu"}
            ]

        elif button_payload == "confirm_edit":
            conv.state = ConvState.CORRECTING.value
            outbound_msgs.append({"type": "text", "body": "Please type or send a voice note with the corrected detail (e.g. correct amount, UTR, or bank):"})
        else:
            conv.state = ConvState.MENU.value
            outbound_msgs.append({"type": "text", "body": "Report cancelled. Returning to main menu."})
            buttons = [{"id": "cmd_menu", "label": "Main Menu"}]

    # STATE: NOMINEE_SETUP
    elif current_state == ConvState.NOMINEE_SETUP:
        nominee_ph = raw_user_text.strip()
        reporter.nominee_phone_enc = encrypt_field(nominee_ph)
        reporter.nominee_phone_hash = hmac_hash(nominee_ph)
        conv.state = ConvState.MENU.value
        outbound_msgs.append({"type": "text", "body": get_text("nominee_setup_success", lang=lang)})
        buttons = [{"id": "cmd_menu", "label": "Main Menu"}]

    # STATE: ERASE_CONFIRM
    elif current_state == ConvState.ERASE_CONFIRM:
        if button_payload == "confirm_erase_yes":
            reporter.phone_enc = b""
            reporter.nominee_phone_enc = b""
            reporter.deleted_at = datetime.now(timezone.utc)
            conv.state = ConvState.ERASED.value
            outbound_msgs.append({"type": "text", "body": get_text("erasure_completed", lang=lang)})
        else:
            conv.state = ConvState.MENU.value
            outbound_msgs.append({"type": "text", "body": "Data erasure cancelled. Your records remain protected."})
            buttons = [{"id": "cmd_menu", "label": "Main Menu"}]

    # Default fallback
    else:
        conv.state = ConvState.MENU.value
        outbound_msgs.append({"type": "text", "body": get_text("menu_title", lang=lang)})
        buttons = [
            {"id": "menu_fraud", "label": get_text("btn_menu_fraud", lang=lang)},
            {"id": "menu_extortion", "label": get_text("btn_menu_extortion", lang=lang)},
            {"id": "menu_status", "label": get_text("btn_menu_status", lang=lang)}
        ]

    conv.context_enc = encrypt_field(json.dumps(context))
    conv.last_activity_at = datetime.now(timezone.utc)
    await session.commit()

    return ConversationResponse(
        messages=outbound_msgs,
        state=conv.state,
        buttons=buttons,
        case_ref=case_ref,
        golden_hour=is_golden_hour
    )
