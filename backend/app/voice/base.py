"""Base Interface for Speech-to-Text (ASR) Providers."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseASRProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> Dict[str, Any]:
        """Transcribes incoming audio bytes.

        Returns:
            Dict containing:
            - text: str
            - language: str ('mr', 'hi', 'en')
            - confidence: float (0.0 to 1.0)
            - duration_seconds: float
        """
        pass

