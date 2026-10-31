"""WhatsApp Cloud API Webhook Endpoints with HMAC Signature Verification."""

import hashlib
import hmac
from typing import Any, Dict
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.config import settings
from backend.app.db.session import get_db
from backend.app.conversation.engine import process_user_input

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.get("/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """Meta Webhook Handshake Verification."""
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Invalid verification token")


@router.post("/whatsapp")
async def receive_whatsapp_message(
    request: Request,
    x_hub_signature_256: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Processes inbound WhatsApp messages with X-Hub-Signature-256 verification."""
    raw_body = await request.body()

    # Verify signature if secret configured
    if settings.WHATSAPP_APP_SECRET and x_hub_signature_256:
        expected_sig = "sha256=" + hmac.new(
            settings.WHATSAPP_APP_SECRET.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(x_hub_signature_256, expected_sig):
            raise HTTPException(status_code=401, detail="Invalid signature")

    payload: Dict[str, Any] = await request.json()
    
    # Process message from payload structure
    try:
        entries = payload.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                for msg in messages:
                    sender = msg.get("from", "+919999900000")
                    msg_type = msg.get("type", "text")
                    text_body = None
                    button_payload = None

                    if msg_type == "text":
                        text_body = msg.get("text", {}).get("body")
                    elif msg_type == "button":
                        button_payload = msg.get("button", {}).get("payload")

                    await process_user_input(
                        session=db,
                        phone_number=sender,
                        text_content=text_body,
                        button_payload=button_payload,
                        channel="whatsapp_cloud"
                    )
    except Exception as e:
        # Avoid crashing webhook worker
        pass

    return {"status": "received"}
