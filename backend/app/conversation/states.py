"""Conversation State Machine Definitions for SurakshaVani."""

from enum import Enum


class ConvState(str, Enum):
    NEW = "NEW"
    LANG_SELECT = "LANG_SELECT"
    CONSENT = "CONSENT"
    MENU = "MENU"
    
    # Fraud flow
    FRAUD_PROMPT_VOICE = "FRAUD_PROMPT_VOICE"
    PROCESSING = "PROCESSING"
    CONFIRM = "CONFIRM"
    CORRECTING = "CORRECTING"
    MISSING_FIELDS = "MISSING_FIELDS"
    SUBMITTED = "SUBMITTED"
    AFTERCARE = "AFTERCARE"
    
    # Extortion flow
    EXT_SAFE_INTRO = "EXT_SAFE_INTRO"
    EXT_COLLECT = "EXT_COLLECT"
    EXT_EVIDENCE = "EXT_EVIDENCE"
    EXT_CONFIRM = "EXT_CONFIRM"
    EXT_SUBMITTED = "EXT_SUBMITTED"
    
    # Nominee flow
    NOMINEE_SETUP = "NOMINEE_SETUP"
    NOMINEE_VERIFY = "NOMINEE_VERIFY"
    
    # Status lookup
    STATUS_LOOKUP = "STATUS_LOOKUP"
    
    # Data Erasure / DPDP
    ERASE_CONFIRM = "ERASE_CONFIRM"
    ERASED = "ERASED"
    
    # Safety Interruption States
    SAFETY_ESCALATE = "SAFETY_ESCALATE"
    MINOR_ROUTE = "MINOR_ROUTE"

