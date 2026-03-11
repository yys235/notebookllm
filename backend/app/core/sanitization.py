"""Log data sanitization utilities for sensitive information protection.

This module provides functions to redact sensitive data from logs
before they are written to outputs.
"""
import re
from typing import Any

# Fields that should be redacted in logs
SENSITIVE_FIELDS = {
    "password",
    "token",
    "api_key",
    "apikey",
    "api-key",
    "secret",
    "authorization",
    "cookie",
    "session",
    "session_id",
    "sessionid",
    "credit_card",
    "ssn",
    "social_security",
    "pin",
    "cvv",
    "cvc",
    "private_key",
    "privatekey",
    # Email and phone are often PII - redact by default
    "email",
    "phone",
    "telephone",
    "mobile",
}

# Patterns for detecting sensitive values
SENSITIVE_PATTERNS = [
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "***@***.***"),
    # API keys (common formats)
    (re.compile(r"\b(sk-|pk-|api_key|apikey)[A-Za-z0-9_-]{20,}\b", re.IGNORECASE), "***REDACTED_API_KEY***"),
    # Bearer tokens
    (re.compile(r"Bearer\s+[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "Bearer ***REDACTED***"),
    # Credit card numbers (basic pattern)
    (re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"), "***-****-****-****"),
    # SSN-like numbers
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "***-**-****"),
]


def redact_value(value: Any) -> Any:
    """Redact sensitive values from a single value.

    Args:
        value: The value to check and potentially redact

    Returns:
        The original value or a redacted placeholder
    """
    if value is None:
        return None

    if isinstance(value, str):
        # Apply pattern-based redaction
        for pattern, replacement in SENSITIVE_PATTERNS:
            if pattern.search(value):
                return replacement

        # Check if the string looks like a sensitive value
        if len(value) > 20 and value.replace("-", "").replace("_", "").isalnum():
            # Long alphanumeric strings might be tokens/keys
            return "***REDACTED_LONG_STRING***"

    return value


def sanitize_log_data(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize a dictionary for logging.

    This function removes or redacts sensitive information from dictionaries
    before they are logged.

    Args:
        data: Dictionary to sanitize

    Returns:
        Sanitized dictionary with sensitive data redacted

    Example:
        >>> data = {"user": "john", "password": "secret123", "email": "john@example.com"}
        >>> sanitize_log_data(data)
        {"user": "john", "password": "***REDACTED***", "email": "***@***.***"}
    """
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        # Check if this is a sensitive field name
        key_lower = key.lower().replace("-", "").replace("_", "")

        if key_lower in SENSITIVE_FIELDS or key.replace("-", "").replace("_", "").lower() in SENSITIVE_FIELDS:
            # Redact the entire value
            sanitized[key] = "***REDACTED***"
            continue

        # Recursively sanitize nested structures
        if isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_log_data(item) if isinstance(item, dict) else redact_value(item)
                for item in value
            ]
        else:
            sanitized[key] = redact_value(value)

    return sanitized


class SanitizedLog:
    """Wrapper for log data that auto-sanitizes on string conversion."""

    def __init__(self, data: dict[str, Any]):
        """Initialize with potentially sensitive data.

        Args:
            data: Dictionary containing potentially sensitive information
        """
        self._data = data
        self._sanitized = None

    @property
    def sanitized(self) -> dict[str, Any]:
        """Get sanitized data (cached)."""
        if self._sanitized is None:
            self._sanitized = sanitize_log_data(self._data)
        return self._sanitized

    def __str__(self) -> str:
        """Return sanitized string representation."""
        return str(self.sanitized)

    def __repr__(self) -> str:
        """Return sanitized representation."""
        return repr(self.sanitized)

    def to_dict(self) -> dict[str, Any]:
        """Get the sanitized dictionary."""
        return self.sanitized


def sanitize_request_data(
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Sanitize HTTP request data for logging.

    Args:
        method: HTTP method
        path: Request path
        headers: Request headers
        params: Query parameters
        body: Request body

    Returns:
        Sanitized dictionary safe for logging
    """
    data = {
        "method": method,
        "path": path,
    }

    if headers:
        # Always redact authorization headers
        safe_headers = {}
        for k, v in headers.items():
            if k.lower() in {"authorization", "cookie", "x-api-key"}:
                safe_headers[k] = "***REDACTED***"
            else:
                safe_headers[k] = v
        data["headers"] = safe_headers

    if params:
        data["params"] = sanitize_log_data(params)

    if body:
        data["body"] = sanitize_log_data(body)

    return data
