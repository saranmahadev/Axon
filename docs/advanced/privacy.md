# Privacy & PII Detection

Automatic detection and protection of personally identifiable information.

---

## Overview

The **Privacy & PII Detection** system helps you comply with data protection regulations (GDPR, CCPA, HIPAA) by automatically detecting and classifying personally identifiable information (PII) in memory entries.

**Key Features:**
- ✓ Automatic PII detection (SSN, email, phone, credit cards)
- ✓ Privacy level recommendations
- ✓ Regex-based pattern matching
- ✓ Customizable detection rules
- ✓ Integration with memory storage

---

## Supported PII Types

| PII Type | Pattern | Privacy Level | Example |
|----------|---------|---------------|---------|
| **SSN** | xxx-xx-xxxx | RESTRICTED | 123-45-6789 |
| **Credit Card** | xxxx-xxxx-xxxx-xxxx | RESTRICTED | 4532-1234-5678-9010 |
| **Email** | user@example.com | INTERNAL | john@company.com |
| **Phone** | (xxx) xxx-xxxx | INTERNAL | (555) 123-4567 |
| **IP Address** | xxx.xxx.xxx.xxx | INTERNAL | 192.168.1.1 |

---

## Basic Usage

```python
from axon.core.privacy import PIIDetector

detector = PIIDetector()

# Detect PII in text
text = "My email is john@example.com and SSN is 123-45-6789"
result = detector.detect(text)

print(f"Detected PII: {result.detected_types}")
# Output: {'email', 'ssn'}

print(f"Recommended level: {result.recommended_privacy_level}")
# Output: PrivacyLevel.RESTRICTED

print(f"Has PII: {result.has_pii}")
# Output: True
```

---

## Privacy Levels

### PrivacyLevel Enum

```python
from axon.models.base import PrivacyLevel

# Four levels of privacy
PrivacyLevel.PUBLIC       # No PII, safe to share publicly
PrivacyLevel.INTERNAL     # Internal use only (emails, phones)
PrivacyLevel.CONFIDENTIAL # Confidential business data
PrivacyLevel.RESTRICTED   # Highly sensitive (SSN, credit cards)
```

### Level Recommendations

The detector recommends privacy levels based on detected PII:

```python
# No PII detected
detector.detect("The weather is nice today")
# → PrivacyLevel.PUBLIC

# Email detected
detector.detect("Contact: john@example.com")
# → PrivacyLevel.INTERNAL

# SSN detected
detector.detect("SSN: 123-45-6789")
# → PrivacyLevel.RESTRICTED
```

---

## Integration with Memory System

### Automatic Detection

```python
from axon import MemorySystem

memory = MemorySystem(config)

# Store with PII detection
await memory.store(
    "User john@example.com called from (555) 123-4567",
    detect_pii=True  # Automatically detects and sets privacy level
)

# The entry will have:
# - privacy_level = PrivacyLevel.INTERNAL (email + phone)
# - metadata["pii_detected"] = {"email", "phone"}
```

### Manual Detection and Storage

```python
from axon.core.privacy import PIIDetector

detector = PIIDetector()

# Detect PII first
text = "Patient SSN: 123-45-6789, Insurance: 4532-1234-5678-9010"
result = detector.detect(text)

# Store with detected privacy level
await memory.store(
    text,
    privacy_level=result.recommended_privacy_level,
    metadata={"pii_types": list(result.detected_types)}
)
```

---

## Detection Results

### PIIDetectionResult

```python
result = detector.detect(text)

# Properties
result.detected_types        # Set of PII types found
result.has_pii               # Boolean: any PII detected
result.recommended_privacy_level  # Recommended PrivacyLevel
result.details               # Dict with counts by type

# Example
print(result.details)
# Output: {'email': 2, 'phone': 1, 'ssn': 1}
```

---

## Custom Detection Rules

### Extend PIIDetector

```python
import re
from axon.core.privacy import PIIDetector
from axon.models.base import PrivacyLevel

class CustomPIIDetector(PIIDetector):
    """Extended PII detector with custom patterns."""
    
    def __init__(self):
        super().__init__()
        
        # Add custom patterns
        self.PATTERNS["passport"] = re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")
        self.PATTERNS["driver_license"] = re.compile(r"\b[A-Z]\d{7,8}\b")
        
        # Define privacy levels for custom patterns
        self.PRIVACY_LEVELS["passport"] = PrivacyLevel.RESTRICTED
        self.PRIVACY_LEVELS["driver_license"] = PrivacyLevel.RESTRICTED

# Use custom detector
detector = CustomPIIDetector()
result = detector.detect("Passport: A1234567")
print(result.detected_types)  # {'passport'}
```

---

## Examples

### GDPR Compliance

```python
async def store_with_gdpr_compliance(memory, text: str, user_id: str):
    """Store data with GDPR compliance checks."""
    
    # Detect PII
    detector = PIIDetector()
    result = detector.detect(text)
    
    if result.has_pii:
        # Log PII detection for audit trail
        logger.info(
            f"PII detected for user {user_id}",
            extra={
                "pii_types": list(result.detected_types),
                "privacy_level": result.recommended_privacy_level.value
            }
        )
        
        # Store with restricted access
        await memory.store(
            text,
            user_id=user_id,
            privacy_level=result.recommended_privacy_level,
            metadata={
                "pii_detected": True,
                "pii_types": list(result.detected_types),
                "requires_consent": True
            }
        )
    else:
        # Safe to store normally
        await memory.store(text, user_id=user_id)
```

### PII Redaction

```python
def redact_pii(text: str) -> tuple[str, PIIDetectionResult]:
    """Redact PII from text."""
    detector = PIIDetector()
    result = detector.detect(text)
    
    redacted_text = text
    
    # Redact each type
    for pii_type, pattern in detector.PATTERNS.items():
        if pii_type in result.detected_types:
            redacted_text = pattern.sub(f"[{pii_type.upper()}_REDACTED]", redacted_text)
    
    return redacted_text, result

# Usage
original = "Email: john@example.com, SSN: 123-45-6789"
redacted, result = redact_pii(original)
print(redacted)
# Output: "Email: [EMAIL_REDACTED], SSN: [SSN_REDACTED]"
```

### Privacy-Aware Search

```python
from axon.models.filter import Filter

async def search_with_privacy(memory, query: str, user_privacy_level: PrivacyLevel):
    """Search respecting user's privacy clearance."""
    
    # Filter by maximum privacy level user can access
    results = await memory.recall(
        query,
        filter=Filter(
            max_privacy_level=user_privacy_level
        ),
        k=10
    )
    
    return results

# Example: Internal user can't see restricted data
results = await search_with_privacy(
    memory,
    "patient information",
    user_privacy_level=PrivacyLevel.INTERNAL
)
# Only returns PUBLIC and INTERNAL level entries
```

---

## Best Practices

### 1. Always Detect Before Storing Sensitive Data

```python
# ✓ Good: Detect and classify
result = detector.detect(text)
await memory.store(
    text,
    privacy_level=result.recommended_privacy_level
)

# ✗ Bad: Store without detection
await memory.store(text)  # Might store SSN as PUBLIC!
```

### 2. Use Appropriate Privacy Levels

```python
# Map business requirements to privacy levels
user_roles = {
    "public_viewer": PrivacyLevel.PUBLIC,
    "employee": PrivacyLevel.INTERNAL,
    "manager": PrivacyLevel.CONFIDENTIAL,
    "admin": PrivacyLevel.RESTRICTED
}

# Filter based on role
async def get_memories_for_role(role: str, query: str):
    max_level = user_roles[role]
    return await memory.recall(
        query,
        filter=Filter(max_privacy_level=max_level)
    )
```

### 3. Audit PII Access

```python
# Log all access to restricted data
async def audit_pii_access(memory, query: str, user_id: str):
    results = await memory.recall(query)
    
    for entry in results:
        if entry.privacy_level == PrivacyLevel.RESTRICTED:
            await audit_logger.log_event(
                operation=OperationType.RECALL,
                user_id=user_id,
                entry_ids=[entry.id],
                metadata={
                    "privacy_level": "RESTRICTED",
                    "pii_access": True
                }
            )
    
    return results
```

### 4. Implement Data Retention Policies

```python
from datetime import timedelta

# Auto-delete restricted data after retention period
config = MemoryConfig(
    persistent=PersistentPolicy(
        ttl=timedelta(days=90),  # 90-day retention
        adapter_type="redis"
    )
)

# Or with privacy-based retention
async def apply_retention_policy(memory):
    """Delete expired restricted data."""
    
    # Get all restricted entries
    restricted = await memory.recall(
        "",
        filter=Filter(privacy_level=PrivacyLevel.RESTRICTED),
        k=10000
    )
    
    # Delete entries older than retention period
    cutoff = datetime.now() - timedelta(days=90)
    for entry in restricted:
        if entry.created_at < cutoff:
            await memory.forget(entry.id)
            logger.info(f"Deleted expired restricted entry: {entry.id}")
```

---

## Performance

### Detection Overhead

- **Latency:** 1-10ms per text (depends on length)
- **Regex matching:** O(n) where n is text length
- **Memory:** Negligible (~1KB for patterns)

### Optimization

```python
# Cache detector instance (don't recreate)
detector = PIIDetector()  # Create once

# Batch detection for multiple texts
texts = ["text1 with email@test.com", "text2 with 123-45-6789"]
results = [detector.detect(t) for t in texts]
```

---

## Limitations

### Pattern-Based Detection

The detector uses regex patterns, which have limitations:

**May Miss:**
- Obfuscated PII: "john [at] example [dot] com"
- Typos: "123-456-789" (missing digit)
- Non-standard formats: International phone numbers

**May False Positive:**
- Numbers that look like SSN: "123-45-6789" in a different context
- Generic email patterns in code examples

**For Advanced Detection:**
Consider ML-based PII detection libraries:
- Microsoft Presidio
- AWS Comprehend PII detection
- spaCy NER models

---

## Next Steps

<div class="grid cards" markdown>

-   :material-clipboard-text:{ .lg .middle } **Audit Logging**

    ---

    Track PII access for compliance.

    [:octicons-arrow-right-24: Audit Guide](audit.md)

-   :material-database-sync:{ .lg .middle } **Transactions**

    ---

    Atomic operations with privacy checks.

    [:octicons-arrow-right-24: Transactions Guide](transactions.md)

-   :material-shield-check:{ .lg .middle } **Security**

    ---

    Production security best practices.

    [:octicons-arrow-right-24: Security Guide](../deployment/security.md)

</div>
