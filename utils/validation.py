"""
Validation utilities for lead data and user input.
"""
from typing import Optional
import re

from config import VALID_STATUSES


def validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    if not phone:
        return False

    # Remove common separators
    phone_clean = re.sub(r'[\s\-\(\)\+]', '', phone)

    # Check if it's numeric and has reasonable length
    if not phone_clean.isdigit():
        return False

    # Phone should be between 7 and 15 digits
    return 7 <= len(phone_clean) <= 15


def validate_status(status: str) -> bool:
    """Validate lead status."""
    return status in VALID_STATUSES


def validate_lead_id(lead_id: str) -> bool:
    """Validate lead ID format."""
    if not lead_id:
        return False
    # Lead ID should be non-empty string
    return len(lead_id.strip()) > 0


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input text."""
    if not text:
        return ""
    # Remove excessive whitespace and limit length
    text = " ".join(text.split())
    return text[:max_length].strip()


def validate_email(email: str) -> bool:
    """Basic email validation."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def extract_lead_id(text: str) -> Optional[str]:
    """Extract lead ID from text (useful for parsing user input)."""
    if not text:
        return None

    # Try to find ID pattern (alphanumeric, possibly with dashes/underscores)
    match = re.search(r'([A-Za-z0-9_-]+)', text.strip())
    if match:
        return match.group(1)
    return None

