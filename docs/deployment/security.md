# Security

Secure your Axon memory systems with best practices and hardening guidelines.

---

## Overview

Security is critical for production deployments. This guide covers authentication, authorization, encryption, PII protection, and security best practices for Axon-based applications.

**Key Topics:**
- ✓ Authentication & authorization
- ✓ Encryption (at rest & in transit)
- ✓ PII detection & protection
- ✓ Network security
- ✓ Secret management
- ✓ Audit logging

---

## Authentication

### API Key Authentication

```python
# auth.py
from fastapi import FastAPI, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

app = FastAPI()
security = HTTPBearer()

# Load API keys from environment
VALID_API_KEYS = set(os.getenv("API_KEYS", "").split(","))

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify API key."""
    if credentials.credentials not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

# Protected endpoints
@app.post("/store")
async def store(text: str, api_key: str = Security(verify_api_key)):
    """Store with API key auth."""
    await memory.store(text, user_id=api_key)
    return {"status": "success"}
```

### JWT Authentication

```python
# jwt_auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

security = HTTPBearer()

def create_access_token(user_id: str, expires_delta: timedelta = timedelta(hours=24)):
    """Create JWT token."""
    expire = datetime.utcnow() + expires_delta
    to_encode = {"sub": user_id, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(security)):
    """Verify JWT and extract user."""
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Use in endpoints
@app.post("/store")
async def store(text: str, user_id: str = Depends(get_current_user)):
    await memory.store(text, user_id=user_id)
    return {"status": "success"}
```

---

## Authorization

### Role-Based Access Control (RBAC)

```python
# rbac.py
from enum import Enum
from typing import Set

class Role(Enum):
    """User roles."""
    VIEWER = "viewer"
    USER = "user"
    ADMIN = "admin"

class Permissions:
    """Role permissions."""
    VIEWER = {"recall", "get"}
    USER = {"recall", "get", "store", "delete"}
    ADMIN = {"recall", "get", "store", "delete", "export", "compact"}

def check_permission(user_role: Role, operation: str) -> bool:
    """Check if role has permission for operation."""
    role_perms = getattr(Permissions, user_role.value.upper())
    return operation in role_perms

# Enforce in application
class SecureMemorySystem:
    """Memory system with RBAC."""
    
    def __init__(self, memory, user_role: Role):
        self.memory = memory
        self.role = user_role
    
    async def store(self, text: str, **kwargs):
        """Store with permission check."""
        if not check_permission(self.role, "store"):
            raise PermissionError("User lacks 'store' permission")
        
        return await self.memory.store(text, **kwargs)
    
    async def recall(self, query: str, **kwargs):
        """Recall with permission check."""
        if not check_permission(self.role, "recall"):
            raise PermissionError("User lacks 'recall' permission")
        
        return await self.memory.recall(query, **kwargs)

# Usage
admin_memory = SecureMemorySystem(memory, Role.ADMIN)
await admin_memory.store("Admin data")  # ✓ Allowed

viewer_memory = SecureMemorySystem(memory, Role.VIEWER)
await viewer_memory.store("Data")  # ✗ PermissionError
```

### Data Access Control

```python
# access_control.py
from axon.models.filter import Filter

class DataAccessController:
    """Control data access by user."""
    
    def __init__(self, memory, user_id: str, user_roles: Set[str]):
        self.memory = memory
        self.user_id = user_id
        self.user_roles = user_roles
    
    async def recall(self, query: str, **kwargs):
        """Recall with access control."""
        # Add user filter
        user_filter = Filter(metadata={"owner": self.user_id})
        
        # Merge with provided filter
        if "filter" in kwargs:
            existing_filter = kwargs["filter"]
            # Combine filters
            user_filter.metadata.update(existing_filter.metadata)
        
        kwargs["filter"] = user_filter
        
        # Only see own data
        return await self.memory.recall(query, **kwargs)

# Usage
user_memory = DataAccessController(memory, "user_123", {"user"})
results = await user_memory.recall("query")
# Only returns entries where metadata.owner == "user_123"
```

---

## Encryption

### Encryption at Rest

```python
# encryption.py
from cryptography.fernet import Fernet
import os

class EncryptedMemorySystem:
    """Memory system with encryption at rest."""
    
    def __init__(self, memory, encryption_key: bytes = None):
        self.memory = memory
        self.key = encryption_key or Fernet.generate_key()
        self.cipher = Fernet(self.key)
    
    async def store(self, text: str, **kwargs):
        """Store encrypted text."""
        # Encrypt text
        encrypted_text = self.cipher.encrypt(text.encode())
        encrypted_str = encrypted_text.decode()
        
        # Store encrypted
        entry_id = await self.memory.store(encrypted_str, **kwargs)
        return entry_id
    
    async def recall(self, query: str, **kwargs):
        """Recall and decrypt."""
        # Encrypt query for matching
        encrypted_query = self.cipher.encrypt(query.encode()).decode()
        
        # Recall encrypted entries
        results = await self.memory.recall(encrypted_query, **kwargs)
        
        # Decrypt results
        for entry in results:
            try:
                decrypted = self.cipher.decrypt(entry.text.encode())
                entry.text = decrypted.decode()
            except Exception:
                pass  # Entry not encrypted or wrong key
        
        return results

# Usage
# Load encryption key from secure storage
encryption_key = os.getenv("ENCRYPTION_KEY").encode()
encrypted_memory = EncryptedMemorySystem(memory, encryption_key)

await encrypted_memory.store("Sensitive data")
```

### Encryption in Transit (TLS)

```yaml
# docker-compose.yml with TLS
services:
  app:
    build: .
    ports:
      - "443:443"
    volumes:
      - ./certs:/certs:ro
    environment:
      - SSL_CERT_FILE=/certs/server.crt
      - SSL_KEY_FILE=/certs/server.key
  
  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --tls-port 6380
      --port 0
      --tls-cert-file /tls/redis.crt
      --tls-key-file /tls/redis.key
      --tls-ca-cert-file /tls/ca.crt
    volumes:
      - ./certs:/tls:ro
```

```python
# TLS configuration
import ssl

# Redis with TLS
config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        adapter_config={
            "url": "rediss://redis:6380",  # Note: rediss://
            "ssl_cert_reqs": ssl.CERT_REQUIRED,
            "ssl_ca_certs": "/certs/ca.crt"
        }
    )
)
```

---

## PII Protection

### Automatic PII Detection

```python
# pii_protection.py
from axon.core.privacy import PIIDetector
from axon.models.base import PrivacyLevel

class PIIProtectedMemorySystem:
    """Memory system with automatic PII detection."""
    
    def __init__(self, memory):
        self.memory = memory
        self.detector = PIIDetector()
    
    async def store(self, text: str, **kwargs):
        """Store with PII detection."""
        # Detect PII
        result = self.detector.detect(text)
        
        if result.has_pii:
            # Log PII detection
            logger.warning(f"PII detected: {result.detected_types}")
            
            # Set privacy level
            kwargs["privacy_level"] = result.recommended_privacy_level
            
            # Add metadata
            if "metadata" not in kwargs:
                kwargs["metadata"] = {}
            kwargs["metadata"]["pii_detected"] = True
            kwargs["metadata"]["pii_types"] = list(result.detected_types)
        
        return await self.memory.store(text, **kwargs)

# Usage
protected_memory = PIIProtectedMemorySystem(memory)
await protected_memory.store("My SSN is 123-45-6789")
# Automatically marked as RESTRICTED
```

### PII Redaction

```python
# pii_redaction.py
import re

class PIIRedactor:
    """Redact PII from text."""
    
    PATTERNS = {
        "ssn": (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
        "email": (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"),
        "phone": (re.compile(r"\b\d{3}-\d{3}-\d{4}\b"), "[PHONE]"),
        "credit_card": (re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"), "[CARD]")
    }
    
    def redact(self, text: str) -> str:
        """Redact PII from text."""
        redacted = text
        
        for pii_type, (pattern, replacement) in self.PATTERNS.items():
            redacted = pattern.sub(replacement, redacted)
        
        return redacted

# Usage
redactor = PIIRedactor()

original = "Email: john@example.com, SSN: 123-45-6789"
redacted = redactor.redact(original)
print(redacted)
# Output: "Email: [EMAIL], SSN: [SSN]"

# Store redacted version
await memory.store(redacted)
```

---

## Network Security

### Firewall Rules

```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow application
sudo ufw allow 8000/tcp

# Allow Redis (internal only)
sudo ufw allow from 10.0.0.0/8 to any port 6379

# Allow Qdrant (internal only)
sudo ufw allow from 10.0.0.0/8 to any port 6333

# Enable firewall
sudo ufw enable
```

### Network Segmentation

```yaml
# docker-compose.yml with networks
version: '3.8'

services:
  app:
    networks:
      - frontend
      - backend
  
  redis:
    networks:
      - backend  # Not exposed to frontend
  
  qdrant:
    networks:
      - backend  # Not exposed to frontend

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No external access
```

---

## Secret Management

### Environment Variables

```bash
# .env (DO NOT commit to git)
REDIS_PASSWORD=your-secure-password
QDRANT_API_KEY=your-api-key
OPENAI_API_KEY=your-openai-key
JWT_SECRET_KEY=your-jwt-secret
ENCRYPTION_KEY=your-encryption-key
```

### Secrets Management Services

```python
# aws_secrets.py
import boto3
import json

def get_secret(secret_name: str, region: str = "us-east-1") -> dict:
    """Get secret from AWS Secrets Manager."""
    client = boto3.client('secretsmanager', region_name=region)
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        logger.error(f"Failed to get secret: {e}")
        raise

# Load secrets
secrets = get_secret("axon-production-secrets")

config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        adapter_config={
            "url": secrets["redis_url"],
            "password": secrets["redis_password"]
        }
    )
)
```

---

## Audit Logging

### Security Event Logging

```python
# security_audit.py
from axon.core.audit import AuditLogger
from axon.models.audit import OperationType, EventStatus

audit_logger = AuditLogger()

async def log_security_event(
    event_type: str,
    user_id: str,
    success: bool,
    details: dict = None
):
    """Log security event."""
    await audit_logger.log_event(
        operation=OperationType.CUSTOM,
        user_id=user_id,
        status=EventStatus.SUCCESS if success else EventStatus.FAILURE,
        metadata={
            "event_type": event_type,
            "details": details or {}
        }
    )

# Log authentication attempts
await log_security_event(
    "authentication",
    user_id="user_123",
    success=True,
    details={"method": "jwt", "ip": "192.168.1.100"}
)

# Log authorization failures
await log_security_event(
    "authorization",
    user_id="user_456",
    success=False,
    details={"operation": "delete", "reason": "insufficient_permissions"}
)
```

---

## Security Best Practices

### 1. Principle of Least Privilege

```python
# ✓ Good: Minimal permissions
user_role = Role.USER  # Can store and recall
admin_role = Role.ADMIN  # Full access

# ✗ Bad: Everyone is admin
all_admin = Role.ADMIN
```

### 2. Defense in Depth

```python
# ✓ Good: Multiple security layers
# - Authentication (JWT)
# - Authorization (RBAC)
# - Encryption (at rest + in transit)
# - PII detection
# - Audit logging
# - Network segmentation

# ✗ Bad: Single security layer
# - Only authentication
```

### 3. Regular Security Updates

```bash
# ✓ Good: Keep dependencies updated
pip install --upgrade axon-sdk
pip install --upgrade redis
pip install --upgrade qdrant-client

# Check for vulnerabilities
pip-audit
```

### 4. Secure Configuration

```python
# ✓ Good: Secure defaults
config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        adapter_config={
            "url": "rediss://redis:6380",  # TLS
            "password": get_secret("redis_password"),
            "ssl_cert_reqs": ssl.CERT_REQUIRED
        }
    )
)

# ✗ Bad: Insecure configuration
config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        adapter_config={
            "url": "redis://redis:6379",  # No TLS
            "password": "password123"  # Hardcoded
        }
    )
)
```

---

## Security Checklist

- [ ] Authentication enabled (API keys or JWT)
- [ ] Authorization implemented (RBAC)
- [ ] Encryption at rest configured
- [ ] TLS/SSL enabled for all connections
- [ ] PII detection active
- [ ] Secrets in environment variables or secrets manager
- [ ] Firewall rules configured
- [ ] Network segmentation implemented
- [ ] Audit logging enabled
- [ ] Regular security updates scheduled
- [ ] Monitoring and alerting configured
- [ ] Backup encryption enabled

---

## Next Steps

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Production**

    ---

    Deploy securely to production.

    [:octicons-arrow-right-24: Production Guide](production.md)

-   :material-shield-lock:{ .lg .middle } **Privacy & PII**

    ---

    Advanced PII protection.

    [:octicons-arrow-right-24: Privacy Guide](../advanced/privacy.md)

-   :material-clipboard-text:{ .lg .middle } **Audit Logging**

    ---

    Complete audit trail.

    [:octicons-arrow-right-24: Audit Guide](../advanced/audit.md)

</div>
