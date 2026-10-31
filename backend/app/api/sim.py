"""Web Simulator API Endpoints for Citizen Interface."""

import base64
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.conversation.engine import process_user_input

router = APIRouter(prefix="/sim", tags=["Simulator"])


class SimulatorMessageRequest(BaseModel):
    phone_number: str = "+919890011223"
    text: Optional[str] = None
    button_payload: Optional[str] = None
    audio_base64: Optional[str] = None
    audio_filename: str = "msedcl_scam_marathi.wav"


@router.post("/messages")
async def send_simulator_message(
    req: SimulatorMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """Processes simulated citizen interaction (Voice note, text, or interactive button)."""
    audio_bytes = None
    if req.audio_base64:
        try:
            audio_bytes = base64.b64decode(req.audio_base64)
        except Exception:
            audio_bytes = None

    response = await process_user_input(
        session=db,
        phone_number=req.phone_number,
        text_content=req.text,
        audio_bytes=audio_bytes,
        audio_filename=req.audio_filename,
        button_payload=req.button_payload,
        channel="web_sim"
    )

    return response.to_dict()

