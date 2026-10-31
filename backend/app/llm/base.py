"""Base Interface for LLM Providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseLLMProvider(ABC):
    @abstractmethod
    async def extract_complaint(
        self,
        transcript: str,
        language: str,
        system_time_iso: str
    ) -> Dict[str, Any]:
        """Extracts structured complaint dictionary conforming to ComplaintSchema."""
        pass

    @abstractmethod
    async def classify_crisis(self, text: str) -> Dict[str, Any]:
        """Classifies safety risk flags."""
        pass

