# Production Deployment

Deploy Axon memory systems to production with best practices and reliability.

---

## Overview

This guide covers deploying Axon-based applications to production environments with high availability, scalability, and reliability.

**Key Topics:**
- ✓ Infrastructure setup
- ✓ Configuration management
- ✓ High availability
- ✓ Scalability patterns
- ✓ Backup and recovery
- ✓ Monitoring and alerting

---

## Quick Start

### Minimal Production Setup

```python
# production_config.py
import os
from axon.core.config import MemoryConfig
from axon.core.policies import (
    EphemeralPolicy,
    SessionPolicy,
    PersistentPolicy
)
from datetime import timedelta

# Load from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

# Production configuration
PRODUCTION_CONFIG = MemoryConfig(
    ephemeral=EphemeralPolicy(
        adapter_type="memory",  # Fast in-memory cache
        ttl=timedelta(minutes=15),
        compaction_threshold=1000
    ),
    session=SessionPolicy(
        adapter_type="redis",
        ttl=timedelta(hours=24),
        compaction_threshold=5000,
        adapter_config={
            "url": REDIS_URL,
            "namespace": "axon:session"
        }
    ),
    persistent=PersistentPolicy(
        adapter_type="qdrant",
        compaction_threshold=50000,
        adapter_config={
            "url": QDRANT_URL,
            "collection_name": "memories"
        }
    )
)
```

---

## Infrastructure Setup

### Docker Compose

Complete stack with Redis and Qdrant:

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Application
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - QDRANT_URL=http://qdrant:6333
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AXON_LOG_LEVEL=INFO
    depends_on:
      - redis
      - qdrant
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  # Redis for session tier
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
  
  # Qdrant for persistent tier
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redis_data:
  qdrant_data:
```

### Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: axon-app
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: axon-app
  template:
    metadata:
      labels:
        app: axon-app
    spec:
      containers:
      - name: app
        image: your-registry/axon-app:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: axon-secrets
              key: redis-url
        - name: QDRANT_URL
          valueFrom:
            secretKeyRef:
              name: axon-secrets
              key: qdrant-url
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: axon-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: axon-app-service
  namespace: production
spec:
  selector:
    app: axon-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

## Configuration Management

### Environment Variables

```bash
# .env.production
# Redis Configuration
REDIS_URL=redis://redis-cluster:6379
REDIS_PASSWORD=your-secure-password
REDIS_MAX_CONNECTIONS=50

# Qdrant Configuration
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-api-key

# OpenAI Configuration
OPENAI_API_KEY=your-openai-key

# Axon Configuration
AXON_LOG_LEVEL=INFO
AXON_STRUCTURED_LOGGING=true
AXON_LOG_FILE=/var/log/axon.log

# Application Configuration
APP_ENV=production
APP_DEBUG=false
```

### Secrets Management

```python
# config/secrets.py
import os
from typing import Optional

class SecretsManager:
    """Manage secrets from environment or secrets manager."""
    
    @staticmethod
    def get_secret(key: str, default: Optional[str] = None) -> str:
        """Get secret from environment."""
        value = os.getenv(key, default)
        
        if value is None:
            raise ValueError(f"Required secret '{key}' not found")
        
        return value
    
    @staticmethod
    def get_redis_url() -> str:
        """Get Redis connection URL."""
        return SecretsManager.get_secret("REDIS_URL")
    
    @staticmethod
    def get_qdrant_url() -> str:
        """Get Qdrant connection URL."""
        return SecretsManager.get_secret("QDRANT_URL")
    
    @staticmethod
    def get_openai_key() -> str:
        """Get OpenAI API key."""
        return SecretsManager.get_secret("OPENAI_API_KEY")

# Use in application
from config.secrets import SecretsManager

config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        adapter_config={"url": SecretsManager.get_redis_url()}
    )
)
```

---

## High Availability

### Redis Cluster

```yaml
# Redis Sentinel for HA
services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    
  redis-slave-1:
    image: redis:7-alpine
    command: redis-server --slaveof redis-master 6379
    
  redis-slave-2:
    image: redis:7-alpine
    command: redis-server --slaveof redis-master 6379
    
  redis-sentinel-1:
    image: redis:7-alpine
    command: redis-sentinel /etc/sentinel.conf
    
  redis-sentinel-2:
    image: redis:7-alpine
    command: redis-sentinel /etc/sentinel.conf
    
  redis-sentinel-3:
    image: redis:7-alpine
    command: redis-sentinel /etc/sentinel.conf
```

### Qdrant Cluster

```yaml
# Qdrant distributed cluster
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: qdrant
spec:
  serviceName: qdrant
  replicas: 3
  selector:
    matchLabels:
      app: qdrant
  template:
    metadata:
      labels:
        app: qdrant
    spec:
      containers:
      - name: qdrant
        image: qdrant/qdrant:latest
        ports:
        - containerPort: 6333
        - containerPort: 6334
        volumeMounts:
        - name: storage
          mountPath: /qdrant/storage
  volumeClaimTemplates:
  - metadata:
      name: storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
```

---

## Scalability

### Horizontal Scaling

```python
# Scale application instances
from axon import MemorySystem

# Stateless application design
# Each instance uses shared Redis + Qdrant
class Application:
    def __init__(self):
        self.memory = MemorySystem(PRODUCTION_CONFIG)
    
    async def handle_request(self, user_id: str, query: str):
        """Handle request - works across multiple instances."""
        results = await self.memory.recall(
            query,
            user_id=user_id,
            k=10
        )
        return results

# Deploy multiple instances behind load balancer
# All share same memory backends
```

### Vertical Scaling

```yaml
# Increase resources for high load
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "8Gi"
    cpu: "4000m"
```

---

## Backup and Recovery

### Redis Backup

```bash
# Backup Redis data
#!/bin/bash

BACKUP_DIR="/backups/redis"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup
docker exec redis redis-cli SAVE
docker cp redis:/data/dump.rdb "$BACKUP_DIR/dump_$TIMESTAMP.rdb"

# Compress
gzip "$BACKUP_DIR/dump_$TIMESTAMP.rdb"

# Clean old backups (keep last 7 days)
find "$BACKUP_DIR" -name "dump_*.rdb.gz" -mtime +7 -delete
```

### Qdrant Backup

```bash
# Backup Qdrant data
#!/bin/bash

BACKUP_DIR="/backups/qdrant"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create snapshot
curl -X POST "http://qdrant:6333/collections/memories/snapshots"

# Download snapshot
SNAPSHOT_NAME=$(curl "http://qdrant:6333/collections/memories/snapshots" | jq -r '.result[0].name')
curl "http://qdrant:6333/collections/memories/snapshots/$SNAPSHOT_NAME" \
  -o "$BACKUP_DIR/snapshot_$TIMESTAMP.tar"

# Compress
gzip "$BACKUP_DIR/snapshot_$TIMESTAMP.tar"
```

### Automated Backups

```python
# scheduled_backups.py
import schedule
import subprocess
from datetime import datetime

def backup_redis():
    """Backup Redis data."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    subprocess.run(["/scripts/backup_redis.sh"])
    print(f"Redis backup completed: {timestamp}")

def backup_qdrant():
    """Backup Qdrant data."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    subprocess.run(["/scripts/backup_qdrant.sh"])
    print(f"Qdrant backup completed: {timestamp}")

# Schedule backups
schedule.every().day.at("02:00").do(backup_redis)
schedule.every().day.at("03:00").do(backup_qdrant)

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## Health Checks

### Application Health Endpoint

```python
# health.py
from fastapi import FastAPI, Response
from axon import MemorySystem

app = FastAPI()
memory = MemorySystem(PRODUCTION_CONFIG)

@app.get("/health")
async def health():
    """Basic health check."""
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    """Readiness check - verify dependencies."""
    try:
        # Test Redis connection
        await memory.store("health_check", tier="session", ttl=timedelta(seconds=5))
        
        # Test Qdrant connection
        await memory.recall("health", tier="persistent", k=1)
        
        return {"status": "ready", "dependencies": {"redis": "ok", "qdrant": "ok"}}
    
    except Exception as e:
        return Response(
            content={"status": "not_ready", "error": str(e)},
            status_code=503
        )
```

---

## Best Practices

### 1. Use Configuration Templates

```python
# ✓ Good: Use production template
from axon.core.templates import PRODUCTION_CONFIG

memory = MemorySystem(PRODUCTION_CONFIG)

# ✗ Bad: Development config in production
from axon.core.templates import DEVELOPMENT_CONFIG
memory = MemorySystem(DEVELOPMENT_CONFIG)
```

### 2. Enable Monitoring

```python
# ✓ Good: Structured logging + metrics
from axon.core.logging_config import configure_logging

configure_logging(
    level="INFO",
    structured=True,
    output_file="/var/log/axon.log"
)

# ✗ Bad: No logging
```

### 3. Implement Circuit Breakers

```python
# ✓ Good: Handle failures gracefully
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def store_with_circuit_breaker(memory, text: str):
    """Store with circuit breaker protection."""
    return await memory.store(text)

# ✗ Bad: No fault tolerance
```

### 4. Use Connection Pooling

```python
# ✓ Good: Connection pooling
config = MemoryConfig(
    session=SessionPolicy(
        adapter_type="redis",
        adapter_config={
            "url": REDIS_URL,
            "max_connections": 50  # Connection pool
        }
    )
)

# ✗ Bad: No pooling (1 connection per request)
```

---

## Troubleshooting

### Common Issues

**Issue: High Memory Usage**

```python
# Solution: Adjust compaction thresholds
config = MemoryConfig(
    persistent=PersistentPolicy(
        compaction_threshold=10000,  # Lower threshold
        compaction_batch_size=100
    )
)
```

**Issue: Slow Queries**

```python
# Solution: Add indexes and filters
results = await memory.recall(
    query,
    filter=Filter(tags=["specific"]),  # Narrow search
    k=10  # Limit results
)
```

**Issue: Connection Failures**

```python
# Solution: Implement retry logic
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def store_with_retry(memory, text: str):
    return await memory.store(text)
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-speedometer:{ .lg .middle } **Performance Tuning**

    ---

    Optimize for production performance.

    [:octicons-arrow-right-24: Performance Guide](performance.md)

-   :material-monitor:{ .lg .middle } **Monitoring**

    ---

    Set up monitoring and alerting.

    [:octicons-arrow-right-24: Monitoring Guide](monitoring.md)

-   :material-shield-check:{ .lg .middle } **Security**

    ---

    Secure your production deployment.

    [:octicons-arrow-right-24: Security Guide](security.md)

</div>
