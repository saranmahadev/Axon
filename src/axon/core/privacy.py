"""Privacy and PII detection for compliance and data protection.

This module provides basic PII (Personally Identifiable Information) detection
using regex patterns to identify sensitive data in memory entries.
"""

import re
from dataclasses import dataclass
from typing import List, Set

from ..models.base import PrivacyLevel


@dataclass
class PIIDetectionResult:
    """Result of PII detection analysis.

    Attributes:
        detected_types: Set of PII types detected (e.g., "email", "ssn")
        recommended_privacy_level: Recommended privacy level based on detected PII
        has_pii: Whether any PII was detected
        details: Additional details about detected PII (count by type)
    """

    detected_types: Set[str]
    recommended_privacy_level: PrivacyLevel
    has_pii: bool
    details: dict[str, int]


class PIIDetector:
    """Detects personally identifiable information using regex patterns.

    Supports detection of:
    - Social Security Numbers (SSN)
    - Credit Card Numbers
    - Email Addresses
    - Phone Numbers
    - IP Addresses (IPv4)

    Example:
        >>> detector = PIIDetector()
        >>> result = detector.detect("My email is user@example.com")
        >>> result.detected_types
        {'email'}
        >>> result.recommended_privacy_level
        <PrivacyLevel.INTERNAL: 'internal'>
    """

    # Regex patterns for common PII types
    PATTERNS = {
        # SSN: xxx-xx-xxxx or xxxxxxxxx
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b"),
        # Credit card: 4 groups of 4 digits (with optional spaces/dashes)
        "credit_card": re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
        # Email: basic email pattern
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        # Phone: General format with 7+ digits, optional +, spaces, dashes, parentheses
        "phone": re.compile(r"(?:\+?\d{1,3}[\s\-\.]?)?\(?\d{2,4}\)?[\s\-\.]?\d{2,4}[\s\-\.]?\d{2,4}"),
        # IPv4 address
        "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    }

    # Privacy level mapping based on detected PII
    PRIVACY_LEVELS = {
        "ssn": PrivacyLevel.RESTRICTED,
        "credit_card": PrivacyLevel.RESTRICTED,
        "email": PrivacyLevel.INTERNAL,
        "phone": PrivacyLevel.INTERNAL,
        "ip_address": PrivacyLevel.INTERNAL,
    }

    def detect(self, text: str) -> PIIDetectionResult:
        """Detect PII in the given text.

        Args:
            text: Text to analyze for PII

        Returns:
            PIIDetectionResult with detected types and recommended privacy level
        """
        if not text:
            return PIIDetectionResult(
                detected_types=set(),
                recommended_privacy_level=PrivacyLevel.PUBLIC,
                has_pii=False,
                details={},
            )

        detected_types: Set[str] = set()
        details: dict[str, int] = {}

        # Check each pattern
        for pii_type, pattern in self.PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                detected_types.add(pii_type)
                details[pii_type] = len(matches)

        # Determine recommended privacy level
        # Use the highest (most restrictive) level from detected types
        if detected_types:
            privacy_levels = [
                self.PRIVACY_LEVELS[pii_type]
                for pii_type in detected_types
                if pii_type in self.PRIVACY_LEVELS
            ]

            # Order: PUBLIC < INTERNAL < SENSITIVE < RESTRICTED
            level_order = {
                PrivacyLevel.PUBLIC: 0,
                PrivacyLevel.INTERNAL: 1,
                PrivacyLevel.SENSITIVE: 2,
                PrivacyLevel.RESTRICTED: 3,
            }

            recommended_level = max(
                privacy_levels, key=lambda x: level_order.get(x, 0), default=PrivacyLevel.PUBLIC
            )
        else:
            recommended_level = PrivacyLevel.PUBLIC

        return PIIDetectionResult(
            detected_types=detected_types,
            recommended_privacy_level=recommended_level,
            has_pii=len(detected_types) > 0,
            details=details,
        )

    def detect_multiple(self, texts: List[str]) -> List[PIIDetectionResult]:
        """Detect PII in multiple texts.

        Args:
            texts: List of texts to analyze

        Returns:
            List of PIIDetectionResult, one per text
        """
        return [self.detect(text) for text in texts]

    def get_supported_types(self) -> List[str]:
        """Get list of supported PII types.

        Returns:
            List of PII type names
        """
        return list(self.PATTERNS.keys())
