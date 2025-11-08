"""Unit tests for PII detection."""

import pytest

from axon.core.privacy import PIIDetector, PIIDetectionResult
from axon.models.base import PrivacyLevel


class TestPIIDetector:
    """Test PIIDetector functionality."""

    def test_create_detector(self):
        """Test creating a PII detector."""
        detector = PIIDetector()

        assert detector is not None
        supported_types = detector.get_supported_types()
        assert len(supported_types) >= 4
        assert "email" in supported_types
        assert "ssn" in supported_types

    def test_detect_email(self):
        """Test detecting email addresses."""
        detector = PIIDetector()

        result = detector.detect("Contact me at user@example.com for details")

        assert result.has_pii is True
        assert "email" in result.detected_types
        assert result.recommended_privacy_level == PrivacyLevel.INTERNAL
        assert result.details["email"] == 1

    def test_detect_multiple_emails(self):
        """Test detecting multiple email addresses."""
        detector = PIIDetector()

        text = "Email john@company.com or jane@company.com"
        result = detector.detect(text)

        assert result.has_pii is True
        assert "email" in result.detected_types
        assert result.details["email"] == 2

    def test_detect_ssn(self):
        """Test detecting Social Security Numbers."""
        detector = PIIDetector()

        # SSN with dashes
        result1 = detector.detect("My SSN is 123-45-6789")
        assert result1.has_pii is True
        assert "ssn" in result1.detected_types
        assert result1.recommended_privacy_level == PrivacyLevel.RESTRICTED

        # SSN without dashes
        result2 = detector.detect("SSN: 987654321")
        assert result2.has_pii is True
        assert "ssn" in result2.detected_types

    def test_detect_credit_card(self):
        """Test detecting credit card numbers."""
        detector = PIIDetector()

        # With spaces
        result1 = detector.detect("Card: 4532 1234 5678 9010")
        assert result1.has_pii is True
        assert "credit_card" in result1.detected_types
        assert result1.recommended_privacy_level == PrivacyLevel.RESTRICTED

        # With dashes
        result2 = detector.detect("CC: 4532-1234-5678-9010")
        assert result2.has_pii is True
        assert "credit_card" in result2.detected_types

    def test_detect_phone(self):
        """Test detecting phone numbers."""
        detector = PIIDetector()

        # Format: (xxx) xxx-xxxx
        result1 = detector.detect("Call me at (555) 123-4567")
        assert result1.has_pii is True
        assert "phone" in result1.detected_types
        assert result1.recommended_privacy_level == PrivacyLevel.INTERNAL

        # Format: xxx-xxx-xxxx
        result2 = detector.detect("Phone: 555-123-4567")
        assert result2.has_pii is True
        assert "phone" in result2.detected_types

    def test_detect_ip_address(self):
        """Test detecting IP addresses."""
        detector = PIIDetector()

        result = detector.detect("Server IP: 192.168.1.100")

        assert result.has_pii is True
        assert "ip_address" in result.detected_types
        assert result.recommended_privacy_level == PrivacyLevel.INTERNAL

    def test_detect_multiple_pii_types(self):
        """Test detecting multiple PII types in same text."""
        detector = PIIDetector()

        text = "Contact john@example.com or call (555) 123-4567. IP: 10.0.0.1"
        result = detector.detect(text)

        assert result.has_pii is True
        assert "email" in result.detected_types
        assert "phone" in result.detected_types
        assert "ip_address" in result.detected_types
        assert len(result.detected_types) == 3

    def test_privacy_level_priority(self):
        """Test that most restrictive privacy level is recommended."""
        detector = PIIDetector()

        # Email only (INTERNAL)
        result1 = detector.detect("Email: user@example.com")
        assert result1.recommended_privacy_level == PrivacyLevel.INTERNAL

        # SSN (RESTRICTED) takes priority over email (INTERNAL)
        result2 = detector.detect("Email: user@example.com, SSN: 123-45-6789")
        assert result2.recommended_privacy_level == PrivacyLevel.RESTRICTED

        # Credit card (RESTRICTED) takes priority
        result3 = detector.detect("Card: 4532 1234 5678 9010, Phone: 555-123-4567")
        assert result3.recommended_privacy_level == PrivacyLevel.RESTRICTED

    def test_no_pii_detected(self):
        """Test text with no PII."""
        detector = PIIDetector()

        result = detector.detect("This is just regular text without any sensitive info")

        assert result.has_pii is False
        assert len(result.detected_types) == 0
        assert result.recommended_privacy_level == PrivacyLevel.PUBLIC
        assert result.details == {}

    def test_empty_text(self):
        """Test empty text."""
        detector = PIIDetector()

        result = detector.detect("")

        assert result.has_pii is False
        assert len(result.detected_types) == 0
        assert result.recommended_privacy_level == PrivacyLevel.PUBLIC

    def test_none_text(self):
        """Test None text."""
        detector = PIIDetector()

        result = detector.detect(None)

        assert result.has_pii is False
        assert result.recommended_privacy_level == PrivacyLevel.PUBLIC

    def test_detect_multiple_texts(self):
        """Test batch detection on multiple texts."""
        detector = PIIDetector()

        texts = [
            "Email: user@example.com",
            "No PII here",
            "SSN: 123-45-6789",
        ]

        results = detector.detect_multiple(texts)

        assert len(results) == 3
        assert results[0].has_pii is True
        assert results[0].detected_types == {"email"}
        assert results[1].has_pii is False
        assert results[2].has_pii is True
        # SSN may also match phone pattern due to dashes
        assert "ssn" in results[2].detected_types

    def test_pii_detection_result_structure(self):
        """Test PIIDetectionResult structure."""
        detector = PIIDetector()

        result = detector.detect("Email: user@example.com, Phone: 555-123-4567")

        # Check all fields exist
        assert hasattr(result, "detected_types")
        assert hasattr(result, "recommended_privacy_level")
        assert hasattr(result, "has_pii")
        assert hasattr(result, "details")

        # Check types
        assert isinstance(result.detected_types, set)
        assert isinstance(result.recommended_privacy_level, PrivacyLevel)
        assert isinstance(result.has_pii, bool)
        assert isinstance(result.details, dict)

    def test_details_count_accuracy(self):
        """Test that details accurately count PII occurrences."""
        detector = PIIDetector()

        # Multiple emails
        result = detector.detect(
            "Contact a@ex.com, b@ex.com, or c@ex.com"
        )

        assert result.details["email"] == 3

        # Mixed PII types with multiple occurrences
        result2 = detector.detect(
            "Email a@ex.com or b@ex.com. Call 555-123-4567 or 555-987-6543"
        )

        assert result2.details["email"] == 2
        assert result2.details["phone"] == 2

    def test_get_supported_types(self):
        """Test getting supported PII types."""
        detector = PIIDetector()

        supported = detector.get_supported_types()

        assert isinstance(supported, list)
        assert "ssn" in supported
        assert "credit_card" in supported
        assert "email" in supported
        assert "phone" in supported
        assert "ip_address" in supported
        assert len(supported) >= 5
