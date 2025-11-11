# Monitoring & Observability

Monitor Axon memory systems in production with metrics, logs, and alerts.

---

## Overview

Comprehensive monitoring ensures your Axon-based applications run smoothly in production. This guide covers metrics collection, logging, alerting, and observability best practices.

**Key Topics:**
- ✓ Metrics collection
- ✓ Logging aggregation
- ✓ Distributed tracing
- ✓ Alerting rules
- ✓ Dashboards
- ✓ Troubleshooting

---

## Metrics

### Key Metrics to Track

| Metric | Type | Description | Alert Threshold |
|--------|------|-------------|-----------------|
| **Request Rate** | Counter | Operations/second | < 10 or > 10,000 |
| **Latency (p50)** | Histogram | Median response time | > 200ms |
| **Latency (p95)** | Histogram | 95th percentile | > 1000ms |
| **Error Rate** | Counter | Errors/total requests | > 1% |
| **Memory Usage** | Gauge | RAM consumption | > 80% |
| **Entry Count** | Gauge | Entries per tier | > threshold |
| **Compaction Rate** | Counter | Compactions/hour | Track trends |

### Prometheus Integration

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Define metrics
request_total = Counter(
    'axon_requests_total',
    'Total requests',
    ['operation', 'tier', 'status']
)

request_duration = Histogram(
    'axon_request_duration_seconds',
    'Request duration',
    ['operation', 'tier']
)

memory_entries = Gauge(
    'axon_memory_entries',
    'Number of entries',
    ['tier']
)

memory_usage_bytes = Gauge(
    'axon_memory_usage_bytes',
    'Memory usage in bytes'
)

# Instrumentation wrapper
async def track_operation(operation: str, tier: str, func, *args, **kwargs):
    """Track operation metrics."""
    start = time.time()
    status = "success"
    
    try:
        result = await func(*args, **kwargs)
        return result
    except Exception as e:
        status = "error"
        raise
    finally:
        duration = time.time() - start
        request_total.labels(operation=operation, tier=tier, status=status).inc()
        request_duration.labels(operation=operation, tier=tier).observe(duration)

# Use in application
from axon import MemorySystem

class MonitoredMemorySystem:
    """Memory system with metrics."""
    
    def __init__(self, config):
        self.memory = MemorySystem(config)
    
    async def store(self, text: str, tier: str = None, **kwargs):
        """Store with metrics tracking."""
        return await track_operation(
            "store", tier or "auto",
            self.memory.store, text, tier=tier, **kwargs
        )
    
    async def recall(self, query: str, tier: str = None, **kwargs):
        """Recall with metrics tracking."""
        return await track_operation(
            "recall", tier or "auto",
            self.memory.recall, query, tier=tier, **kwargs
        )
```

### Expose Metrics Endpoint

```python
# app.py
from fastapi import FastAPI
from prometheus_client import make_asgi_app

app = FastAPI()

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Example endpoint
@app.post("/store")
async def store_endpoint(text: str):
    memory_system = MonitoredMemorySystem(config)
    entry_id = await memory_system.store(text)
    return {"entry_id": entry_id}
```

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'axon-app'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
```

---

## Logging

### Structured Logging Setup

```python
# logging_setup.py
from axon.core.logging_config import configure_logging
import logging

# Configure structured logging
configure_logging(
    level="INFO",
    structured=True,
    output_file="/var/log/axon.log"
)

logger = logging.getLogger(__name__)

# Log with context
logger.info("Operation completed", extra={
    "operation": "store",
    "user_id": "user_123",
    "duration_ms": 42.5,
    "tier": "persistent",
    "entry_count": 1
})
```

### Log Aggregation (ELK Stack)

```yaml
# docker-compose.yml (ELK)
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
  
  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
      - /var/log/axon.log:/var/log/axon.log:ro
    ports:
      - "5000:5000"
    depends_on:
      - elasticsearch
  
  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

volumes:
  es_data:
```

```conf
# logstash/pipeline/axon.conf
input {
  file {
    path => "/var/log/axon.log"
    codec => json
    type => "axon"
  }
}

filter {
  if [type] == "axon" {
    mutate {
      add_field => { "[@metadata][index]" => "axon-logs" }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "%{[@metadata][index]}-%{+YYYY.MM.dd}"
  }
}
```

### CloudWatch Logs

```python
# cloudwatch_logging.py
import boto3
import watchtower
import logging

# Setup CloudWatch handler
cloudwatch_handler = watchtower.CloudWatchLogHandler(
    log_group="axon-production",
    stream_name="app-logs",
    boto3_client=boto3.client('logs', region_name='us-east-1')
)

logger = logging.getLogger(__name__)
logger.addHandler(cloudwatch_handler)

# Logs automatically sent to CloudWatch
logger.info("Application started")
```

---

## Distributed Tracing

### OpenTelemetry Integration

```python
# tracing.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup tracer
resource = Resource(attributes={"service.name": "axon-app"})
provider = TracerProvider(resource=resource)
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831
)
provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

# Trace operations
async def traced_store(memory, text: str):
    """Store with distributed tracing."""
    with tracer.start_as_current_span("store_operation") as span:
        span.set_attribute("text_length", len(text))
        span.set_attribute("operation", "store")
        
        entry_id = await memory.store(text)
        
        span.set_attribute("entry_id", entry_id)
        return entry_id
```

---

## Dashboards

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Axon Memory System",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(axon_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Latency (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, axon_request_duration_seconds_bucket)"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(axon_requests_total{status='error'}[5m]) / rate(axon_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Memory Entries by Tier",
        "targets": [
          {
            "expr": "axon_memory_entries"
          }
        ]
      }
    ]
  }
}
```

---

## Alerting

### Alert Rules

```yaml
# prometheus_alerts.yml
groups:
  - name: axon_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(axon_requests_total{status="error"}[5m]) / rate(axon_requests_total[5m]) > 0.01
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for {{ $labels.operation }}"
      
      # High latency
      - alert: HighLatency
        expr: histogram_quantile(0.95, axon_request_duration_seconds_bucket) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P95 latency is {{ $value }}s for {{ $labels.operation }}"
      
      # Memory threshold
      - alert: HighMemoryUsage
        expr: axon_memory_entries{tier="ephemeral"} > 10000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory entry count"
          description: "Ephemeral tier has {{ $value }} entries"
      
      # Low request rate (possible outage)
      - alert: LowRequestRate
        expr: rate(axon_requests_total[5m]) < 1
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Very low request rate"
          description: "Request rate is {{ $value }} ops/sec"
```

### Alertmanager Configuration

```yaml
# alertmanager.yml
global:
  slack_api_url: 'YOUR_SLACK_WEBHOOK_URL'

route:
  receiver: 'slack-notifications'
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 3h
  
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
    
    - match:
        severity: warning
      receiver: 'slack-notifications'

receivers:
  - name: 'slack-notifications'
    slack_configs:
      - channel: '#axon-alerts'
        title: 'Axon Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
  
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

---

## Health Checks

### Application Health

```python
# health.py
from fastapi import FastAPI, Response
from axon import MemorySystem
import time

app = FastAPI()
memory = MemorySystem(config)

@app.get("/health")
async def health():
    """Basic liveness check."""
    return {
        "status": "ok",
        "timestamp": time.time()
    }

@app.get("/ready")
async def readiness():
    """Readiness check with dependency validation."""
    checks = {}
    overall_status = "ready"
    
    # Check Redis
    try:
        await memory.store("health_check", tier="session", ttl=timedelta(seconds=5))
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"
        overall_status = "not_ready"
    
    # Check Qdrant
    try:
        await memory.recall("health", tier="persistent", k=1)
        checks["qdrant"] = "ok"
    except Exception as e:
        checks["qdrant"] = f"error: {str(e)}"
        overall_status = "not_ready"
    
    status_code = 200 if overall_status == "ready" else 503
    
    return Response(
        content={"status": overall_status, "checks": checks},
        status_code=status_code
    )

@app.get("/metrics/summary")
async def metrics_summary():
    """Application metrics summary."""
    stats = await memory.get_stats()
    
    return {
        "entries_by_tier": {
            "ephemeral": stats.get("ephemeral_count", 0),
            "session": stats.get("session_count", 0),
            "persistent": stats.get("persistent_count", 0)
        },
        "memory_usage_mb": stats.get("memory_usage_mb", 0),
        "uptime_seconds": stats.get("uptime_seconds", 0)
    }
```

---

## Troubleshooting

### Debug Logging

```python
# Enable debug logging for troubleshooting
import logging

logging.getLogger("axon").setLevel(logging.DEBUG)
logging.getLogger("axon.core.memory_system").setLevel(logging.DEBUG)
logging.getLogger("axon.adapters").setLevel(logging.DEBUG)
```

### Performance Profiling

```python
# profile.py
import cProfile
import pstats
from io import StringIO

async def profile_operation():
    """Profile a specific operation."""
    pr = cProfile.Profile()
    pr.enable()
    
    # Your operation
    await memory.store("Test data")
    
    pr.disable()
    
    # Print stats
    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(20)  # Top 20 functions
    print(s.getvalue())
```

---

## Best Practices

### 1. Monitor Key Metrics

```python
# ✓ Good: Comprehensive monitoring
- Request rate
- Latency (p50, p95, p99)
- Error rate
- Memory usage
- Entry counts

# ✗ Bad: No monitoring
```

### 2. Set Up Alerts

```python
# ✓ Good: Proactive alerts
- High error rate (> 1%)
- High latency (> 1s p95)
- Low request rate (< 1/sec)
- High memory usage (> 80%)

# ✗ Bad: No alerts
```

### 3. Use Structured Logging

```python
# ✓ Good: Machine-readable logs
logger.info("Operation complete", extra={
    "operation": "store",
    "duration_ms": 42,
    "user_id": "user_123"
})

# ✗ Bad: String logs
logger.info("Operation store took 42ms for user_123")
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Production**

    ---

    Deploy with monitoring enabled.

    [:octicons-arrow-right-24: Production Guide](production.md)

-   :material-speedometer:{ .lg .middle } **Performance**

    ---

    Optimize based on metrics.

    [:octicons-arrow-right-24: Performance Guide](performance.md)

-   :material-shield-check:{ .lg .middle } **Security**

    ---

    Secure your deployment.

    [:octicons-arrow-right-24: Security Guide](security.md)

</div>
