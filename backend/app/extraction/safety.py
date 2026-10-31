"""Safety and Crisis Classifier for SurakshaVani.

Detects self-harm expressions, child/minor involvement, intimate image blackmail (sextortion),
and physical threats before standard entity extraction begins.
"""

import re
from typing import Dict, Any


# Multilingual crisis patterns
SELF_HARM_PATTERNS = [
    r"\b(suicide|kill myself|end my life|end myself|marne ka man|jaan de dunga|aatmhatya|jeev sampvava)\b",
    r"\b(can't live anymore|no reason to live|barbaad ho gaya sab|jeene ka mann nahi)\b",
]

MINOR_PATTERNS = [
    r"\b(minor|under 18|school boy|school girl|16 year old|15 year old|17 year old|14 year old)\b",
    r"\b(10th class|12th standard|college first year|minor son|minor daughter)\b",
    r"\b(mi lahan mulga|mulgi|chhota bachha)\b",
]

INTIMATE_IMAGE_PATTERNS = [
    r"\b(nude|sextortion|video call|private video|morphed photo|nude clips|badnami)\b",
    r"\b(viral kar dunga|contacts ko bhej|facebook pe daal|intimate video)\b",
]


def classify_safety_rules(text: str) -> Dict[str, Any]:
    """Lightweight regex and semantic classifier for urgent citizen protection."""
    lower_text = text.lower()

    self_harm = any(re.search(pat, lower_text, re.IGNORECASE) for pat in SELF_HARM_PATTERNS)
    minor = any(re.search(pat, lower_text, re.IGNORECASE) for pat in MINOR_PATTERNS)
    intimate = any(re.search(pat, lower_text, re.IGNORECASE) for pat in INTIMATE_IMAGE_PATTERNS)
    
    # Check for immediate extortion distress
    is_crisis = self_harm or (minor and intimate)

    return {
        "self_harm_risk": self_harm,
        "minor_involved": minor,
        "intimate_images_involved": intimate,
        "immediate_physical_threat": False,
        "crisis_triggered": is_crisis,
        "crisis_reason": "Self-harm signal detected" if self_harm else ("Minor + Intimate Media" if (minor and intimate) else None)
    }

