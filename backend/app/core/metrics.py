"""Prometheus metrics definitions for application monitoring.

This module defines all custom metrics exported by the application.
Metrics are automatically exposed via the /metrics endpoint mounted in main.py.
"""
from prometheus_client import Counter, Gauge, Histogram

# ============================================================================
# HTTP Metrics
# ============================================================================

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["method", "path", "status_code"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "path"]
)

# ============================================================================
# AI Service Metrics
# ============================================================================

ai_requests_total = Counter(
    "ai_requests_total",
    "Total AI service requests made",
    ["provider", "model", "operation", "status"]
)

ai_request_duration_seconds = Histogram(
    "ai_request_duration_seconds",
    "AI service request latency in seconds",
    ["provider", "model", "operation"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

ai_tokens_total = Counter(
    "ai_tokens_total",
    "Total AI tokens consumed",
    ["provider", "model", "token_type"]  # token_type: prompt|completion
)

ai_embeddings_total = Counter(
    "ai_embeddings_total",
    "Total embedding operations performed",
    ["provider", "model", "status"]
)

# ============================================================================
# Database Metrics
# ============================================================================

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query latency in seconds",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

db_connections_active = Gauge(
    "db_connections_active",
    "Active database connections",
    ["state"]  # state: active|idle
)

db_queries_total = Counter(
    "db_queries_total",
    "Total database queries executed",
    ["operation", "table", "status"]
)

# ============================================================================
# Redis/Cache Metrics
# ============================================================================

redis_commands_total = Counter(
    "redis_commands_total",
    "Total Redis commands executed",
    ["command", "status"]
)

redis_request_duration_seconds = Histogram(
    "redis_request_duration_seconds",
    "Redis request latency in seconds",
    ["command"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1)
)

cache_operations_total = Counter(
    "cache_operations_total",
    "Total cache operations",
    ["cache_type", "operation", "result"]  # operation: get|set|delete, result: hit|miss
)

# ============================================================================
# Business Metrics
# ============================================================================

notes_total = Gauge(
    "notes_total",
    "Total number of notes",
    ["visibility"]  # visibility: private|public|shared
)

shares_total = Gauge(
    "shares_total",
    "Total number of active shares",
    ["visibility"]
)

users_total = Gauge(
    "users_total",
    "Total number of registered users",
    []
)

search_queries_total = Counter(
    "search_queries_total",
    "Total search queries performed",
    ["query_type", "result_count_bucket"]
)

# ============================================================================
# Authentication Metrics
# ============================================================================

auth_attempts_total = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["method", "status"]  # method: login|register, status: success|failure
)

active_sessions_total = Gauge(
    "active_sessions_total",
    "Current number of active sessions",
    []
)

# ============================================================================
# Error Metrics
# ============================================================================

errors_total = Counter(
    "errors_total",
    "Total application errors",
    ["error_type", "component"]
)

exceptions_total = Counter(
    "exceptions_total",
    "Total unhandled exceptions",
    ["exception_type", "endpoint"]
)

# ============================================================================
# Utility Functions
# ============================================================================

def init_metrics() -> None:
    """Initialize metrics (called during application startup).

    This function can be used to set initial gauge values or perform
    any other metrics initialization.
    """
    pass
