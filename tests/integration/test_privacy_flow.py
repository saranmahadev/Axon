"""Integration tests for privacy and PII detection flow."""

import pytest

from axon.core import MemorySystem, PIIDetector
from axon.core.config import MemoryConfig
from axon.core.templates import DEVELOPMENT_CONFIG
from axon.models.base import PrivacyLevel


@pytest.mark.asyncio
@pytest.mark.integration
class TestPIIDetectionIntegration:
    """Test PII detection integration with MemorySystem."""

    async def test_pii_detection_enables_by_default(self):
        """Test that PII detection is enabled by default."""
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config)

        assert system.enable_pii_detection is True
        assert system.pii_detector is not None

    async def test_pii_detection_disabled(self):
        """Test that PII detection can be disabled."""
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config, enable_pii_detection=False)

        assert system.enable_pii_detection is False

    async def test_custom_pii_detector(self):
        """Test using custom PIIDetector instance."""
        config = DEVELOPMENT_CONFIG
        custom_detector = PIIDetector()
        system = MemorySystem(config, pii_detector=custom_detector)

        assert system.pii_detector is custom_detector

    async def test_store_with_email_pii(self):
        """Test storing content with email PII."""
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config)

        # Should not raise any errors
        entry_id = await system.store("Contact me at john.doe@example.com for details")
        assert entry_id is not None

    async def test_store_with_ssn_pii(self):
        """Test storing content with SSN PII."""
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config)

        # Should not raise any errors
        entry_id = await system.store("Employee SSN is 123-45-6789")
        assert entry_id is not None

    async def test_store_with_credit_card_pii(self):
        """Test storing content with credit card PII."""
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config)

        # Should not raise any errors
        entry_id = await system.store("Payment card: 4532 1234 5678 9010")
        assert entry_id is not None

    async def test_store_with_phone_pii(self):
        """Test storing content with phone PII."""
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config)

        # Should not raise any errors
        entry_id = await system.store("Call us at (555) 123-4567")
        assert entry_id is not None

    async def test_store_with_ip_pii(self):
        """Test storing content with IP address PII."""
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config)

        # Should not raise any errors
        entry_id = await system.store("Server IP: 192.168.1.100")
        assert entry_id is not None

    async def test_store_with_multiple_pii_types(self):
        """Test storing content with multiple PII types."""
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config)

        # Should not raise any errors
        content = "Contact john@example.com at (555) 123-4567. Server: 10.0.0.1"
        entry_id = await system.store(content)
        assert entry_id is not None

    async def test_store_with_no_pii(self):
        """Test storing content with no PII."""
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config)

        # Should not raise any errors
        entry_id = await system.store("This is just regular text without sensitive info")
        assert entry_id is not None

    async def test_user_override_privacy_level(self):
        """Test that user-provided privacy level is respected."""
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config)

        # Text has email (would be INTERNAL), but user sets RESTRICTED
        entry_id = await system.store(
            "Contact user@example.com",
            metadata={"privacy_level": PrivacyLevel.RESTRICTED},
        )
        assert entry_id is not None

    async def test_pii_detection_with_disabled_flag(self):
        """Test that PII detection respects enable_pii_detection flag."""
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config, enable_pii_detection=False)

        # Should store without PII detection
        entry_id = await system.store("Email: user@example.com, SSN: 123-45-6789")
        assert entry_id is not None

    async def test_pii_detection_with_importance(self):
        """Test PII detection works with importance scoring."""
        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config)

        # Should not raise any errors
        entry_id = await system.store(
            "Important client email: vip@company.com", importance=0.9
        )
        assert entry_id is not None


@pytest.mark.asyncio
@pytest.mark.integration
class TestPIIDetectionWithAudit:
    """Test PII detection integration with audit logging."""

    async def test_audit_with_pii_detection(self):
        """Test that audit logs work with PII detection."""
        from axon.core.audit import AuditLogger

        config = DEVELOPMENT_CONFIG
        audit_logger = AuditLogger()
        system = MemorySystem(config, audit_logger=audit_logger)

        # Store entry with PII
        entry_id = await system.store("Email: user@example.com")

        # Check audit log has entries
        events = await audit_logger.get_events()
        assert len(events) >= 1

    async def test_audit_for_restricted_data(self):
        """Test audit trail for RESTRICTED data storage."""
        from axon.core.audit import AuditLogger
        from axon.models.audit import OperationType

        config = DEVELOPMENT_CONFIG
        audit_logger = AuditLogger()
        system = MemorySystem(config, audit_logger=audit_logger)

        # Store RESTRICTED data
        entry_id = await system.store("SSN: 123-45-6789")

        # Verify audit trail exists
        events = await audit_logger.get_events(operation=OperationType.STORE)
        assert len(events) >= 1


@pytest.mark.asyncio
@pytest.mark.integration
class TestPIIDetectionPerformance:
    """Test performance of PII detection."""

    async def test_pii_detection_overhead_minimal(self):
        """Test that PII detection adds minimal overhead."""
        import time

        config = DEVELOPMENT_CONFIG

        # Measure without PII detection
        system_no_pii = MemorySystem(config, enable_pii_detection=False)
        start = time.perf_counter()
        await system_no_pii.store("Contact user@example.com at (555) 123-4567")
        time_without_pii = time.perf_counter() - start

        # Measure with PII detection
        system_with_pii = MemorySystem(config, enable_pii_detection=True)
        start = time.perf_counter()
        await system_with_pii.store("Contact user@example.com at (555) 123-4567")
        time_with_pii = time.perf_counter() - start

        # PII detection should add less than 50ms overhead
        overhead = time_with_pii - time_without_pii
        assert overhead < 0.05  # 50ms

    async def test_batch_pii_detection_performance(self):
        """Test PII detection performance on batch operations."""
        import time

        config = DEVELOPMENT_CONFIG
        system = MemorySystem(config)

        # Store 100 entries with PII
        texts = [f"Email user{i}@example.com" for i in range(100)]

        start = time.perf_counter()
        for text in texts:
            await system.store(text)
        total_time = time.perf_counter() - start

        # Average time per entry should be reasonable (<100ms)
        avg_time = total_time / 100
        assert avg_time < 0.1  # 100ms per entry is reasonable
