# NotebookLLM 可观测性配置方案

## 1. 健康检查 (Health Check)

### 1.1 端点定义

| 端点 | 方法 | 描述 | 检查项 |
|------|------|------|--------|
| `/health` | GET | 基础健康检查 | 服务存活状态 |
| `/health/ready` | GET | 就绪探针 | 数据库、Redis、AI服务 |
| `/health/live` | GET | 存活探针 | 服务是否响应 |

### 1.2 响应格式

```json
// /health
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-03-02T10:00:00Z"
}

// /health/ready
{
  "status": "ready",
  "checks": {
    "database": {"status": "healthy", "latency_ms": 2.5},
    "redis": {"status": "healthy", "latency_ms": 0.8},
    "ai_service": {"status": "healthy", "latency_ms": 150.2}
  }
}

// /health/live
{
  "status": "alive"
}
```

### 1.3 需要添加的代码

**文件**: `app/api/v1/health.py` (新建)

```python
"""Health check endpoints with dependency status."""
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()
router = APIRouter()


async def check_database(db: AsyncSession) -> dict[str, Any]:
    """Check database connectivity."""
    start_time = datetime.now(UTC)
    try:
        result = await db.execute(text("SELECT 1"))
        result.fetchone()
        latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
        return {"status": "healthy", "latency_ms": round(latency_ms, 2)}
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


async def check_redis() -> dict[str, Any]:
    """Check Redis connectivity."""
    start_time = datetime.now(UTC)
    try:
        from app.core.redis import get_redis_client
        r = await get_redis_client()
        await r.ping()
        latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
        return {"status": "healthy", "latency_ms": round(latency_ms, 2)}
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


async def check_ai_service() -> dict[str, Any]:
    """Check AI service connectivity (optional)."""
    if not settings.AI_SERVICE_URL and not settings.AI_API_KEY:
        return {"status": "disabled", "message": "AI service not configured"}

    start_time = datetime.now(UTC)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            if settings.AI_API_KEY:
                # Test OpenAI API
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {settings.AI_API_KEY}"}
                )
                if response.status_code == 200:
                    latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
                    return {"status": "healthy", "latency_ms": round(latency_ms, 2)}
            raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception as e:
        logger.warning("AI service health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Readiness probe with dependency checks."""
    checks = {
        "database": await check_database(db),
        "redis": await check_redis(),
        "ai_service": await check_ai_service(),
    }

    overall_status = "ready" if all(
        c.get("status") in ("healthy", "disabled") for c in checks.values()
    ) else "not_ready"

    return {"status": overall_status, "checks": checks}


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """Liveness probe - returns alive if service is running."""
    return {"status": "alive"}
```

---

## 2. 日志规范 (Logging Standards)

### 2.1 结构化日志格式

```json
{
  "event": "User created note",
  "level": "info",
  "timestamp": "2026-03-02T10:00:00.123456Z",
  "logger": "app.services.note",
  "app": "Team1 Backend API",
  "version": "0.1.0",
  "env": "production",
  "correlation_id": "abc123-def456",
  "user_id": "user_123",
  "note_id": "note_456",
  "duration_ms": 45.2
}
```

### 2.2 日志级别定义

| 级别 | 用途 | 示例 |
|------|------|------|
| `DEBUG` | 开发调试信息 | 函数入参、中间变量 |
| `INFO` | 正常业务流程 | 用户操作、任务完成 |
| `WARNING` | 潜在问题 | 慢查询、重试发生 |
| `ERROR` | 错误但服务继续 | API调用失败、业务异常 |
| `CRITICAL` | 严重问题 | 服务不可用、数据损坏 |

### 2.3 敏感信息脱敏规则

```python
# 需要脱敏的字段
SENSITIVE_FIELDS = {
    "password", "token", "api_key", "secret", "authorization",
    "cookie", "session", "credit_card", "ssn", "email", "phone"
}

# 脱敏函数
def mask_sensitive_data(data: dict) -> dict:
    for key in SENSITIVE_FIELDS:
        if key in data:
            data[key] = "***REDACTED***"
    return data
```

### 2.4 关键业务日志

```python
# 用户认证
logger.info("User logged in", user_id=user.id, ip_address=request.client.host)
logger.warning("Failed login attempt", email=email, reason="invalid_password")

# 笔记操作
logger.info("Note created", user_id=user.id, note_id=note.id, title=note.title)
logger.info("Note shared", user_id=user.id, note_id=note.id, share_type=share_type)

# AI 检索
logger.info("AI search initiated", user_id=user.id, query_length=len(query))
logger.info("AI search completed", user_id=user.id, result_count=len(results), duration_ms=duration)
```

---

## 3. 监控指标 (Metrics)

### 3.1 Prometheus 指标定义

| 指标名称 | 类型 | 标签 | 描述 |
|----------|------|------|------|
| `http_requests_total` | Counter | method, path, status | 请求总数 |
| `http_request_duration_seconds` | Histogram | method, path | 请求延迟分布 |
| `http_requests_in_progress` | Gauge | method, path | 当前进行中的请求数 |
| `ai_requests_total` | Counter | provider, model, status | AI请求总数 |
| `ai_request_duration_seconds` | Histogram | provider, model | AI请求延迟 |
| `db_connections_active` | Gauge | state | 数据库连接数 |
| `db_query_duration_seconds` | Histogram | operation, table | 数据库查询延迟 |
| `redis_commands_total` | Counter | command, status | Redis命令总数 |
| `cache_hit_ratio` | Gauge | cache_type | 缓存命中率 |

### 3.2 需要添加的指标代码

**文件**: `app/core/metrics.py` (新建)

```python
"""Prometheus metrics definitions."""
from prometheus_client import Counter, Gauge, Histogram

# HTTP metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"]
)

http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "path"]
)

# AI service metrics
ai_requests_total = Counter(
    "ai_requests_total",
    "Total AI service requests",
    ["provider", "model", "status"]
)

ai_request_duration = Histogram(
    "ai_request_duration_seconds",
    "AI service request latency",
    ["provider", "model"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

ai_tokens_total = Counter(
    "ai_tokens_total",
    "Total AI tokens consumed",
    ["provider", "model", "type"]  # type: prompt|completion
)

# Database metrics
db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query latency",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

db_connections_active = Gauge(
    "db_connections_active",
    "Active database connections",
    ["state"]  # state: active|idle
)

# Redis metrics
redis_commands_total = Counter(
    "redis_commands_total",
    "Total Redis commands",
    ["command", "status"]
)

redis_request_duration = Histogram(
    "redis_request_duration_seconds",
    "Redis request latency",
    ["command"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1)
)

cache_operations_total = Counter(
    "cache_operations_total",
    "Total cache operations",
    ["cache_type", "operation", "result"]  # operation: get|set|delete, result: hit|miss
)

# Business metrics
notes_total = Gauge(
    "notes_total",
    "Total number of notes",
    ["user_id", "visibility"]
)

shares_total = Gauge(
    "shares_total",
    "Total number of active shares",
    ["visibility"]
)
```

---

## 4. 告警规则 (Alerting Rules)

### 4.1 Prometheus 告警规则

**文件**: `prometheus-alerts.yml` (新建)

```yaml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      # 服务可用性告警
      - alert: ServiceDown
        expr: up{job="team1-backend"} == 0
        for: 1m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "Service {{ $labels.instance }} is down"
          description: "Service has been down for more than 1 minute"

      # 高错误率告警
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status_code=~"5.."}[5m])) /
          sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} (>5%)"

      - alert: CriticalErrorRate
        expr: |
          sum(rate(http_requests_total{status_code=~"5.."}[5m])) /
          sum(rate(http_requests_total[5m])) > 0.2
        for: 2m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "Critical error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} (>20%)"

      # 高延迟告警
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le, path)
          ) > 2
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High latency on {{ $labels.path }}"
          description: "P95 latency is {{ $value }}s (>2s)"

      - alert: CriticalLatency
        expr: |
          histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le, path)
          ) > 5
        for: 2m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "Critical latency on {{ $labels.path }}"
          description: "P95 latency is {{ $value }}s (>5s)"

  - name: dependency_alerts
    interval: 30s
    rules:
      # 数据库告警
      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "Database is down"
          description: "PostgreSQL has been down for more than 1 minute"

      - alert: HighDatabaseLatency
        expr: |
          histogram_quantile(0.95,
            sum(rate(db_query_duration_seconds_bucket[5m])) by (le)
          ) > 1
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High database latency"
          description: "P95 DB query latency is {{ $value }}s (>1s)"

      # Redis 告警
      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "Redis is down"
          description: "Redis has been down for more than 1 minute"

      # AI 服务告警
      - alert: HighAIFailureRate
        expr: |
          sum(rate(ai_requests_total{status="error"}[5m])) /
          sum(rate(ai_requests_total[5m])) > 0.3
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High AI service failure rate"
          description: "AI service error rate is {{ $value | humanizePercentage }} (>30%)"

  - name: resource_alerts
    interval: 30s
    rules:
      # 内存告警
      - alert: HighMemoryUsage
        expr: process_resident_memory_bytes{job="team1-backend"} / 1024 / 1024 / 1024 > 2
        for: 10m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}GB (>2GB)"

      # 连接池告警
      - alert: DatabasePoolExhausted
        expr: db_connections_active{state="idle"} < 2
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "Database connection pool nearly exhausted"
          description: "Less than 2 idle connections available"
```

### 4.2 告警级别定义

| 级别 | 响应时间 | 示例 |
|------|----------|------|
| **P0 - Critical** | 15分钟内 | 服务完全不可用 |
| **P1 - High** | 1小时内 | 核心功能受损 |
| **P2 - Medium** | 4小时内 | 部分功能异常 |
| **P3 - Low** | 1天内 | 性能下降、非核心问题 |

---

## 5. 分布式追踪 (Distributed Tracing)

### 5.1 OpenTelemetry 配置

**文件**: `app/core/tracing.py` (新建)

```python
"""OpenTelemetry tracing configuration."""
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from app.core.config import get_settings

settings = get_settings()


def setup_tracing(app=None) -> None:
    """Configure OpenTelemetry tracing."""
    resource = Resource.create({
        "service.name": settings.OTEL_SERVICE_NAME,
        "service.version": settings.APP_VERSION,
        "deployment.environment": "production" if not settings.DEBUG else "development",
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    if app:
        FastAPIInstrumentor.instrument_app(app)

    # Instrument HTTP clients
    HTTPXClientInstrumentor().instrument()

    # Instrument SQLAlchemy (already configured in database.py)
    return provider
```

---

## 6. SLO/SLI 定义

### 6.1 服务等级目标 (SLO)

| 指标 | 目标 | 测量窗口 |
|------|------|----------|
| 可用性 | 99.9% | 30天 |
| API 正常运行时间 | 99.95% | 7天 |
| P95 延迟 | <500ms | 24小时 |
| P99 延迟 | <2s | 24小时 |
| 错误率 | <0.1% | 24小时 |

### 6.2 服务等级指标 (SLI)

```python
# 可用性 SLI
availability = (successful_requests / total_requests) * 100

# 延迟 SLI
latency_p95 = percentile(request_durations, 95)
latency_p99 = percentile(request_durations, 99)

# 错误率 SLI
error_rate = (error_requests / total_requests) * 100
```

### 6.3 错误预算计算

```
月度预算 = 30天 × 24小时 × 60分钟 × (1 - 0.999) = 43.2分钟/月
周度预算 = 7天 × 24小时 × 60分钟 × (1 - 0.9995) = 5.04分钟/周
```

---

## 7. Runbook 模板

### 7.1 故障处理流程

```
1. 告警触发 → 2. 确认影响范围 → 3. 定位根因 → 4. 实施修复 → 5. 验证恢复 → 6. 复盘改进
```

### 7.2 常见故障处理

| 故障类型 | 检查项 | 解决方案 |
|----------|--------|----------|
| 服务不可用 | `/health` 端点 | 重启服务、检查日志 |
| 数据库连接失败 | 连接池状态 | 检查 DB 服务、增加连接池 |
| 高延迟 | 慢查询日志 | 优化查询、增加索引 |
| AI 服务失败 | API 密钥、配额 | 切换提供商、启用降级 |

---

## 8. 部署清单

### 8.1 环境变量配置

```bash
# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json

# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_SERVICE_NAME=team1-backend
```

### 8.2 依赖项检查

```
[✓] prometheus-client>=0.21.0
[✓] structlog>=25.1.0
[✓] opentelemetry-api>=1.29.0
[✓] opentelemetry-sdk>=1.29.0
[✓] opentelemetry-instrumentation-fastapi>=0.50b0
```

---

## 9. 监控仪表板建议

### 9.1 Grafana 仪表板面板

1. **概览面板**
   - 请求速率 (QPS)
   - 错误率
   - P50/P95/P99 延迟
   - 服务健康状态

2. **依赖面板**
   - 数据库连接数
   - Redis 命令速率
   - AI 服务成功率

3. **业务面板**
   - 活跃用户数
   - 创建笔记数
   - 分享链接数
   - AI 检索调用数

---

## 10. 下一步行动

- [ ] 实现健康检查端点 (`/health/ready`, `/health/live`)
- [ ] 完善业务指标收集
- [ ] 配置 Prometheus 告警规则
- [ ] 搭建 Grafana 仪表板
- [ ] 编写故障处理 Runbook
- [ ] 进行负载测试建立性能基线
