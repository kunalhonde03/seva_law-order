"""Deterministic Mock ASR Provider for SurakshaVani.

Enables instant, zero-cloud local testing and demo capability.
"""

from typing import Any, Dict
from backend.app.voice.base import BaseASRProvider


class MockASRProvider(BaseASRProvider):
    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> Dict[str, Any]:
        fn_lower = filename.lower()

        # Check filename hints or default to canonical Marathi MSEDCL case
        if "pension" in fn_lower or "sbi" in fn_lower:
            return {
                "text": "Hello, mera naam Ramesh Chandra hai. Aaj subah 11:15 baje mujhe ek call aaya. Saamne wale ne kaha ki wo SBI treasury branch se bol raha hai aur pension Life Certificate expire ho gaya hai. OTP batane par mere account se 1,20,000 rupaye nikal gaye. Fraudster number 8877112233 tha.",
                "language": "hi",
                "confidence": 0.96,
                "duration_seconds": 18.4
            }
        elif "telegram" in fn_lower or "task" in fn_lower:
            return {
                "text": "Bhaiya mere saath fraud ho gaya hai. YouTube video like karne ke bahane Telegram group me add kiya aur crypto task ke naam pe UPI ID payfast@icici par 1 lakh rupaye transfer karwa liye.",
                "language": "hi",
                "confidence": 0.94,
                "duration_seconds": 14.2
            }
        elif "extortion" in fn_lower or "video" in fn_lower:
            return {
                "text": "I received an unknown video call on WhatsApp yesterday. A man claiming to be Inspector Rathore is demanding ₹45,000 from number +91 9711223344 threatening to leak morphed videos to my contacts.",
                "language": "en",
                "confidence": 0.95,
                "duration_seconds": 16.0
            }
        else:
            # Default Canonical Marathi MSEDCL Scam
            return {
                "text": "नमस्कार साहेब, मला आज दुपारी अडीच वाजता एका नंबरवरून फोन आला. तो म्हणाला की मी महावितरण ऑफिसमधून बोलतोय, तुमचं वीज बिल अपडेट नाही आणि आज रात्री ८ वाजता वीज कापली जाईल. मला घाबरवून त्याने ॲप डाउनलोड करायला लावलं आणि १० रुपये भरायला सांगितले. मी जसे गुगल पे वरून १० रुपये भरले, तसे बँक ऑफ महाराष्ट्र खात्यातून ५०,००० रुपये कट झाले. फोन नंबर 9823412345 होता आणि UTR नंबर 429182736152 आहे. अवघ्या वीस मिनिटांपूर्वीच हे घडलंय, प्लीज मदत करा.",
                "language": "mr",
                "confidence": 0.98,
                "duration_seconds": 22.1
            }

