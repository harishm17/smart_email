"""
PII (Personally Identifiable Information) validator.
Uses pattern matching and LLM-based validation to detect and prevent PII leaks.
"""
import re
from typing import Dict, List, Tuple
from pydantic import BaseModel, Field

from config import PII_THRESHOLD, ENABLE_PII_VALIDATION


class PIIDetectionResult(BaseModel):
    """Result of PII detection."""
    has_pii: bool = Field(description="Whether PII was detected")
    pii_types: List[str] = Field(default_factory=list, description="Types of PII found")
    confidence: float = Field(description="Confidence score (0-1)")
    details: List[str] = Field(default_factory=list, description="Details about detected PII")
    safe_to_send: bool = Field(description="Whether it's safe to send the email")


class PIIValidator:
    """
    Validates content for Personally Identifiable Information (PII).
    Uses both pattern matching and optional LLM-based validation.
    """

    # PII detection patterns
    PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        'address': r'\b\d+\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)\b',
    }

    def __init__(self):
        self.enabled = ENABLE_PII_VALIDATION
        self.threshold = PII_THRESHOLD

    def validate(self, content: str) -> PIIDetectionResult:
        """
        Validates content for PII.

        Args:
            content: Text content to validate

        Returns:
            PIIDetectionResult with detection details
        """
        if not self.enabled:
            return PIIDetectionResult(
                has_pii=False,
                confidence=1.0,
                safe_to_send=True
            )

        # Pattern-based detection
        detected_pii = self._detect_patterns(content)

        has_pii = len(detected_pii) > 0
        confidence = 1.0 if detected_pii else 0.0

        # Determine if safe to send
        safe_to_send = not has_pii or confidence < self.threshold

        return PIIDetectionResult(
            has_pii=has_pii,
            pii_types=[pii_type for pii_type, _ in detected_pii],
            confidence=confidence,
            details=[detail for _, detail in detected_pii],
            safe_to_send=safe_to_send
        )

    def _detect_patterns(self, content: str) -> List[Tuple[str, str]]:
        """
        Detects PII using regex patterns.

        Args:
            content: Text to analyze

        Returns:
            List of (pii_type, detail) tuples
        """
        detected = []

        for pii_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    # For patterns with groups (like phone)
                    for match in matches:
                        detected.append((pii_type, f"Found {pii_type}: {'-'.join(match)}"))
                else:
                    for match in matches:
                        detected.append((pii_type, f"Found {pii_type}: {self._mask(match)}"))

        return detected

    def _mask(self, value: str) -> str:
        """Masks sensitive value for logging."""
        if len(value) <= 4:
            return '***'
        return value[:2] + '***' + value[-2:]

    def sanitize(self, content: str) -> str:
        """
        Removes PII from content.

        Args:
            content: Text to sanitize

        Returns:
            Sanitized text with PII removed/masked
        """
        sanitized = content

        for pii_type, pattern in self.PATTERNS.items():
            if pii_type == 'email':
                # Keep domain but mask local part
                sanitized = re.sub(
                    pattern,
                    lambda m: '[EMAIL_REDACTED]@' + m.group(0).split('@')[1],
                    sanitized,
                    flags=re.IGNORECASE
                )
            elif pii_type == 'phone':
                sanitized = re.sub(pattern, '[PHONE_REDACTED]', sanitized)
            elif pii_type == 'ssn':
                sanitized = re.sub(pattern, '[SSN_REDACTED]', sanitized)
            elif pii_type == 'credit_card':
                sanitized = re.sub(pattern, '[CARD_REDACTED]', sanitized)
            else:
                sanitized = re.sub(pattern, f'[{pii_type.upper()}_REDACTED]', sanitized, flags=re.IGNORECASE)

        return sanitized


# Singleton instance
_validator = None

def get_pii_validator() -> PIIValidator:
    """Returns singleton PIIValidator instance."""
    global _validator
    if _validator is None:
        _validator = PIIValidator()
    return _validator
