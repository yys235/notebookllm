# NotebookLLM Security Design Document

**Version**: 1.0
**Date**: 2026-03-13
**Author**: Security Engineer
**Status**: Design Document

---

## 1. Security Overview

### 1.1 Current Security Posture

The NotebookLLM application currently implements basic security measures:

| Component | Status | Notes |
|-----------|--------|-------|
| Authentication | ✅ Implemented | JWT-based with access/refresh tokens |
| Password Hashing | ✅ Implemented | bcrypt with passlib |
| CORS | ✅ Implemented | Configurable origins |
| Rate Limiting | ⚠️ Partial | slowapi installed but not integrated |
| Input Validation | ⚠️ Partial | Pydantic models, needs XSS protection |
| Session Management | ✅ Implemented | RefreshToken model with device tracking |
| SQL Injection | ✅ Protected | SQLAlchemy ORM with parameterized queries |
| HTTPS Enforcement | ❌ Missing | No HSTS/CSP headers |
| Security Scanning | ❌ Missing | No automated security tools |
| Audit Logging | ❌ Missing | No security event logging |

### 1.2 Security Threat Model

```
┌─────────────────────────────────────────────────────────────────┐
│                         Threat Actors                           │
├─────────────────────────────────────────────────────────────────┤
│  External    │  Anonymous Internet Users                        │
│  Attacker    │  - Brute force login attempts                    │
│              │  - DDoS attacks                                  │
│              │  - XSS/CSRF exploitation                         │
├─────────────────────────────────────────────────────────────────┤
│  Authenticated│  Legitimate Users with Malicious Intent         │
│  Bad Actor   │  - Access other users' notes                     │
│              │  - Privilege escalation                          │
│              │  - Data exfiltration                             │
├─────────────────────────────────────────────────────────────────┤
│  Insider    │  Employees/Contractors with Access               │
│  Threat      │  - Misuse of administrative access               │
│              │  - Data theft                                    │
│              │  - Sabotage                                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Critical Assets                               │
├─────────────────────────────────────────────────────────────────┤
│  User Data      │  Email, password hashes, profile info         │
│  Notes          │  User-created content (potentially sensitive)  │
│  AI Data        │  Embeddings, chat history, API keys           │
│  Share Links    │  Access tokens for shared notes               │
│  API Keys       │  OpenAI/Ollama keys for AI services           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Threat Analysis

### 2.1 STRIDE Methodology

| Threat | Description | Impact | Mitigation |
|--------|-------------|--------|------------|
| **Spoofing** | Impersonating users or systems | High | MFA, JWT validation, certificate pinning |
| **Tampering** | Unauthorized data modification | High | HMAC signatures, audit logging, versioning |
| **Repudiation** | Denying actions | Medium | Comprehensive audit trails |
| **Information Disclosure** | Unauthorized data access | High | Encryption at rest/transit, access controls |
| **Denial of Service** | Service disruption | Medium | Rate limiting, request throttling, caching |
| **Elevation of Privilege** | Gaining unauthorized access | High | Role-based access control, principle of least privilege |

### 2.2 Attack Surface Analysis

```
┌─────────────────────────────────────────────────────────────────┐
│                      Attack Surface Map                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Web Application Layer                      │    │
│  │  • Authentication endpoints (/auth/*)                  │    │
│  │  • Note CRUD operations (/api/v1/notes)                │    │
│  │  • Share link access (/shares/public/*)                │    │
│  │  • File upload (/upload)                                │    │
│  │  • WebSocket connections (/ws/*)                        │    │
│  └────────────────────────────────────────────────────────┘    │
│                           │                                     │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              API Gateway / Reverse Proxy                │    │
│  │  • SSL/TLS termination                                 │    │
│  │  • Request routing                                     │    │
│  │  • Rate limiting                                       │    │
│  └────────────────────────────────────────────────────────┘    │
│                           │                                     │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Backend Services                           │    │
│  │  • FastAPI application                                 │    │
│  │  • PostgreSQL database                                  │    │
│  │  • Redis cache                                         │    │
│  │  • AI services (OpenAI/Ollama)                         │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Security Enhancements

### 3.1 Rate Limiting Implementation

**Current State**: slowapi installed but not integrated

**Implementation Plan**:

```python
# app/core/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
from app.core.redis import get_redis

def get_identifier(request: Request) -> str:
    """Get rate limit identifier (user ID if authenticated, IP otherwise)."""
    # Try to get user ID from token first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            from app.core.security import decode_token
            token = auth_header.split(" ")[1]
            payload = decode_token(token)
            if payload:
                return f"user:{payload.get('sub')}"
        except:
            pass
    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"

limiter = Limiter(
    key_func=get_identifier,
    storage_uri="redis://localhost:6379/1",
    default_limits=["60/minute"],
    headers_enabled=True,
)

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded."""
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "Rate limit exceeded",
            "retry_after": exc.retry_after,
        }
    )
```

**Usage in Routes**:

```python
from app.core.rate_limit import limiter

@router.post("/auth/login")
@limiter.limit("5/minute")  # Stricter limit for login
async def login(request: Request, ...):
    # Login logic
    pass

@router.get("/notes")
@limiter.limit("100/minute")  # Higher limit for reads
async def get_notes(request: Request, ...):
    # Get notes logic
    pass
```

### 3.2 Content Security Policy (CSP)

```python
# app/core/security.py (additions)
from fastapi import Response
from fastapi.responses import JSONResponse

class SecurityHeaders:
    """Security headers middleware."""

    @staticmethod
    def add_headers(response: Response) -> Response:
        """Add security headers to all responses."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' wss:// ws://; "
            "frame-ancestors 'none';"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=()"
        )
        return response

# In main.py
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    return SecurityHeaders.add_headers(response)
```

### 3.3 Input Sanitization (XSS Prevention)

```python
# app/core/sanitizer.py
from bs4 import BeautifulSoup
import html
from urllib.parse import urlparse

class ContentSanitizer:
    """Sanitize user-generated content to prevent XSS."""

    # Allowed HTML tags and attributes
    ALLOWED_TAGS = {
        'p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li',
        'blockquote', 'hr',
        'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'div', 'span',
    }

    ALLOWED_ATTRIBUTES = {
        'a': {'href', 'title', 'rel'},
        'img': {'src', 'alt', 'title', 'width', 'height'},
        'td': {'colspan', 'rowspan'},
        'th': {'colspan', 'rowspan'},
        'div': {'class', 'data-*'},  # For data attributes
        'span': {'class', 'data-*'},
    }

    @classmethod
    def sanitize_html(cls, html: str) -> str:
        """Sanitize HTML content to prevent XSS attacks."""
        if not html:
            return ""

        soup = BeautifulSoup(html, 'html.parser')

        # Remove all tags that aren't allowed
        for tag in soup.find_all(True):
            if tag.name not in cls.ALLOWED_TAGS:
                tag.unwrap()
            else:
                # Filter attributes
                allowed_attrs = cls.ALLOWED_ATTRIBUTES.get(tag.name, set())
                attrs_to_remove = []

                for attr_name in tag.attrs:
                    # Check if attribute is allowed
                    if attr_name not in allowed_attrs:
                        # Check for data-* attributes
                        if not attr_name.startswith('data-'):
                            attrs_to_remove.append(attr_name)
                        continue

                    # Validate specific attributes
                    if attr_name == 'href' and tag.name == 'a':
                        url = tag[attr_name]
                        if not cls._is_safe_url(url):
                            attrs_to_remove.append(attr_name)

                    if attr_name == 'src' and tag.name == 'img':
                        url = tag[attr_name]
                        if not cls._is_safe_url(url, allow_data=True):
                            attrs_to_remove.append(attr_name)

                for attr in attrs_to_remove:
                    del tag[attr]

        return str(soup)

    @classmethod
    def _is_safe_url(cls, url: str, allow_data: bool = False) -> bool:
        """Check if URL is safe (javascript: etc. are blocked)."""
        try:
            parsed = urlparse(url)

            # Block dangerous protocols
            if parsed.scheme in ['javascript', 'vbscript', 'data', 'file']:
                if allow_data and parsed.scheme == 'data' and url.startswith('data:image/'):
                    return True
                return False

            # Only allow http, https, and relative URLs
            if parsed.scheme not in ['', 'http', 'https', 'mailto']:
                return False

            return True
        except:
            return False

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Sanitize plain text (escape HTML)."""
        return html.escape(text)

    @classmethod
    def sanitize_json(cls, data: dict) -> dict:
        """Sanitize JSON data (string values only)."""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = cls.sanitize_text(value)
            elif isinstance(value, dict):
                result[key] = cls.sanitize_json(value)
            elif isinstance(value, list):
                result[key] = [
                    cls.sanitize_text(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result
```

### 3.4 SQL Injection Prevention

**Current**: Protected by SQLAlchemy ORM

**Additional Measures**:

```python
# app/core/database.py (additions)
from sqlalchemy import text
from typing import Any

class SafeQuery:
    """Safe query builder with additional protections."""

    @staticmethod
    def escape_identifier(identifier: str) -> str:
        """Safely escape SQL identifiers (table/column names)."""
        # Only allow alphanumeric and underscores
        if not identifier.replace('_', '').replace('-', '').isalnum():
            raise ValueError(f"Invalid identifier: {identifier}")
        return f'"{identifier}"'

    @staticmethod
    def validate_order_by(column: str, allowed_columns: set[str]) -> str:
        """Validate ORDER BY column to prevent SQL injection."""
        if column not in allowed_columns:
            raise ValueError(f"Invalid order column: {column}")
        return SafeQuery.escape_identifier(column)
```

### 3.5 API Security Checklist

```python
# app/core/api_security.py
from functools import wraps
from fastapi import Request, HTTPException, status
import time

async def check_request_size(request: Request, max_size: int = 10_000_000):
    """Check request size limit."""
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Request too large. Maximum size: {max_size} bytes"
        )

async def check_content_type(request: Request, allowed_types: list[str]):
    """Validate content type."""
    content_type = request.headers.get('content-type', '')
    if not any(content_type.startswith(t) for t in allowed_types):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Content type not allowed. Allowed: {', '.join(allowed_types)}"
        )

def validate_json_payload(*fields: str):
    """Decorator to validate JSON payload fields."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Pydantic models handle most validation
            # This adds additional checks for security-sensitive fields
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

---

## 4. Authentication & Authorization

### 4.1 Enhanced Token Security

```python
# app/core/security.py (enhancements)
import secrets
from datetime import datetime, timezone
from typing import Optional

class TokenManager:
    """Enhanced token management with security features."""

    @staticmethod
    def generate_token_id() -> str:
        """Generate a unique token identifier."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def create_access_token_with_jti(
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> tuple[str, str]:
        """
        Create access token with JTI (JWT ID) for revocation support.

        Returns:
            tuple: (token, jti)
        """
        jti = TokenManager.generate_token_id()
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({
            "exp": expire,
            "type": "access",
            "jti": jti,
            "iat": datetime.now(timezone.utc)
        })

        token = jwt.encode(to_encode, get_secret_key(), algorithm=settings.ALGORITHM)
        return token, jti

    @staticmethod
    def create_refresh_token_with_jti(
        data: dict,
        user_agent: str,
        ip_address: str
    ) -> tuple[str, str]:
        """
        Create refresh token with device fingerprinting.

        Returns:
            tuple: (token, jti)
        """
        jti = TokenManager.generate_token_id()
        to_encode = data.copy()

        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        # Create device fingerprint
        device_fingerprint = TokenManager._create_device_fingerprint(user_agent)

        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "jti": jti,
            "device": device_fingerprint,
            "iat": datetime.now(timezone.utc)
        })

        token = jwt.encode(to_encode, get_secret_key(), algorithm=settings.ALGORITHM)
        return token, jti

    @staticmethod
    def _create_device_fingerprint(user_agent: str) -> str:
        """Create a device fingerprint from user agent."""
        import hashlib
        # Simplified fingerprint - production should use more sophisticated method
        return hashlib.sha256(user_agent.encode()).hexdigest()[:16]

    @staticmethod
    def verify_token_integrity(token: str) -> bool:
        """Verify token hasn't been tampered with."""
        try:
            payload = jwt.decode(
                token,
                get_secret_key(),
                algorithms=[settings.ALGORITHM],
                options={"verify_signature": True}
            )
            return True
        except JWTError:
            return False
```

### 4.2 Role-Based Access Control (RBAC)

```python
# app/models/permission.py
import uuid
from enum import Enum
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

class Permission(str, Enum):
    """System permissions."""
    # Note permissions
    READ_NOTE = "note:read"
    WRITE_NOTE = "note:write"
    DELETE_NOTE = "note:delete"
    SHARE_NOTE = "note:share"

    # User permissions
    READ_USER = "user:read"
    WRITE_USER = "user:write"
    DELETE_USER = "user:delete"

    # Admin permissions
    MANAGE_USERS = "admin:manage_users"
    MANAGE_ROLES = "admin:manage_roles"
    VIEW_AUDIT_LOGS = "admin:view_audit_logs"
    MANAGE_SETTINGS = "admin:manage_settings"

class Role(Base):
    """Role model for RBAC."""

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    permissions: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )  # System roles cannot be deleted

class UserRole(Base):
    """User role assignment."""

    __tablename__ = "user_roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id")
    )

# Default roles
DEFAULT_ROLES = [
    {
        "name": "user",
        "description": "Default user role",
        "permissions": [
            Permission.READ_NOTE,
            Permission.WRITE_NOTE,
            Permission.DELETE_NOTE,
            Permission.SHARE_NOTE,
        ]
    },
    {
        "name": "admin",
        "description": "Administrator with full access",
        "permissions": [p.value for p in Permission],
        "is_system": True
    }
]
```

### 4.3 Authorization Middleware

```python
# app/core/authorization.py
from functools import wraps
from fastapi import HTTPException, status
from app.models.permission import Permission

def require_permissions(*required_permissions: Permission):
    """Decorator to require specific permissions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(
            current_user: CurrentUser,
            *args,
            **kwargs
        ):
            # Get user permissions from roles
            from app.services.permission import PermissionService
            perm_service = PermissionService(db)
            user_permissions = await perm_service.get_user_permissions(current_user.id)

            # Check if user has all required permissions
            has_permission = all(
                perm.value in user_permissions
                for perm in required_permissions
            )

            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {[p.value for p in required_permissions]}"
                )

            return await func(current_user, *args, **kwargs)
        return wrapper
    return decorator

# Usage example
@router.delete("/notes/{note_id}")
@require_permissions(Permission.DELETE_NOTE)
async def delete_note(
    note_id: str,
    current_user: CurrentUser,
    db: DBSession
):
    # Delete logic
    pass
```

---

## 5. Audit Logging

```python
# app/models/audit.py
import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import String, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

class AuditEventType(str, Enum):
    """Audit event types."""
    # Authentication events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILED = "auth.login.failed"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGE = "auth.password.change"
    PASSWORD_RESET = "auth.password.reset"

    # Authorization events
    ACCESS_DENIED = "auth.access.denied"
    PERMISSION_GRANTED = "auth.permission.granted"
    PERMISSION_REVOKED = "auth.permission.revoked"

    # Data events
    NOTE_CREATE = "note.create"
    NOTE_READ = "note.read"
    NOTE_UPDATE = "note.update"
    NOTE_DELETE = "note.delete"
    NOTE_SHARE = "note.share"

    # Administrative events
    ROLE_CREATE = "admin.role.create"
    ROLE_UPDATE = "admin.role.update"
    ROLE_DELETE = "admin.role.delete"
    USER_CREATE = "admin.user.create"
    USER_UPDATE = "admin.user.update"
    USER_DELETE = "admin.user.delete"

    # Security events
    RATE_LIMIT_EXCEEDED = "security.rate_limit.exceeded"
    SUSPICIOUS_ACTIVITY = "security.suspicious"
    MALICIOUS_PAYLOAD = "security.malicious_payload"

class AuditLog(Base):
    """Security audit log."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45))  # IPv6 compatible
    user_agent: Mapped[str | None] = mapped_column(String(500))
    resource_type: Mapped[str | None] = mapped_column(String(50), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), index=True)
    outcome: Mapped[str] = mapped_column(String(20))  # success, failure, partial
    details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

# Audit logging service
# app/services/audit.py
from app.models.audit import AuditLog, AuditEventType

class AuditService:
    """Service for logging security events."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        outcome: str = "success",
        details: dict | None = None
    ) -> AuditLog:
        """Log a security event."""
        log_entry = AuditLog(
            event_type=event_type.value,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            details=details
        )

        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)

        return log_entry

    async def log_security_event(
        self,
        event_type: AuditEventType,
        request: Request,
        outcome: str = "success",
        details: dict | None = None
    ):
        """Log a security event from HTTP request."""
        # Try to get user from token
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                user_id = payload.get("sub")
            except:
                pass

        await self.log_event(
            event_type=event_type,
            user_id=user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            outcome=outcome,
            details=details
        )
```

---

## 6. Key & Certificate Management

### 6.1 Secret Management Strategy

```python
# app/core/secrets.py
import os
import secrets
from pathlib import Path
from typing import Optional
import json
from cryptography.fernet import Fernet

class SecretManager:
    """Secure secret management."""

    @staticmethod
    def generate_secret_key(length: int = 64) -> str:
        """Generate a cryptographically secure secret key."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def get_or_create_secret_key(path: str = ".secrets/jwt_key") -> str:
        """Get or create a persistent secret key."""
        secret_path = Path(path)

        if secret_path.exists():
            return secret_path.read_text().strip()

        # Generate new key
        key = SecretManager.generate_secret_key()

        # Create directory if needed
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        secret_path.parent.chmod(0o600)

        # Write key
        secret_path.write_text(key)
        secret_path.chmod(0o400)  # Read-only for owner

        return key

    @staticmethod
    def encrypt_sensitive_data(data: str, encryption_key: str) -> str:
        """Encrypt sensitive data for storage."""
        f = Fernet(encryption_key.encode())
        return f.encrypt(data.encode()).decode()

    @staticmethod
    def decrypt_sensitive_data(encrypted_data: str, encryption_key: str) -> str:
        """Decrypt sensitive data."""
        f = Fernet(encryption_key.encode())
        return f.decrypt(encrypted_data.encode()).decode()

# Environment-specific secret loading
class EnvironmentSecrets:
    """Load secrets from environment or secret management service."""

    @staticmethod
    def get_database_url() -> str:
        """Get database URL from environment."""
        url = os.getenv("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL not set")
        return url

    @staticmethod
    def get_ai_api_key(provider: str) -> str:
        """Get AI service API key from environment."""
        key = os.getenv(f"{provider.upper()}_API_KEY")
        if not key:
            raise ValueError(f"{provider.upper()}_API_KEY not set")
        return key

    @staticmethod
    def get_redis_url() -> str:
        """Get Redis URL from environment."""
        url = os.getenv("REDIS_URL")
        if not url:
            raise ValueError("REDIS_URL not set")
        return url
```

### 6.2 API Key Management

```python
# app/models/api_key.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

class APIKey(Base):
    """API key for external integrations."""

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)  # First 8 chars for display
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    scopes: Mapped[list[str]] = mapped_column(String(500), default="read,write")  # Comma-separated
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

# app/services/api_key.py
import hashlib
from app.core.security import get_password_hash

class APIKeyService:
    """Service for managing API keys."""

    @staticmethod
    async def create_api_key(
        user_id: uuid.UUID,
        name: str,
        scopes: list[str],
        expires_days: int | None = None,
        db: AsyncSession
    ) -> tuple[str, APIKey]:
        """Create a new API key."""
        # Generate key
        raw_key = f"nbllm_{secrets.token_urlsafe(32)}"
        key_hash = get_password_hash(raw_key)
        key_prefix = raw_key[:10]

        # Create expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)

        # Store in database
        api_key = APIKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            user_id=user_id,
            scopes=",".join(scopes),
            expires_at=expires_at
        )

        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)

        # Return raw key (only time it's shown)
        return raw_key, api_key

    @staticmethod
    async def validate_api_key(api_key: str, db: AsyncSession) -> APIKey | None:
        """Validate an API key."""
        # Hash and lookup
        key_hash = get_password_hash(api_key)

        result = await db.execute(
            select(APIKey).where(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True
            )
        )
        key_obj = result.scalar_one_or_none()

        if not key_obj:
            return None

        # Check expiration
        if key_obj.expires_at and key_obj.expires_at < datetime.now(timezone.utc):
            return None

        # Update last used
        key_obj.last_used_at = datetime.now(timezone.utc)
        await db.commit()

        return key_obj
```

---

## 7. Security Scanning Implementation

### 7.1 Dependency Scanning

```bash
# .github/workflows/security-scan.yml
name: Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Weekly on Monday at 6 AM

jobs:
  dependency-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Safety Check
        run: |
          pip install safety
          safety check --json --output safety-report.json || true

      - name: Run Bandit
        run: |
          pip install bandit[toml]
          bandit -r backend/ -f json -o bandit-report.json || true

      - name: Run Pip-audit
        run: |
          pip install pip-audit
          pip-audit --format json --output pip-audit-report.json || true

      - name: Upload Reports
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: |
            safety-report.json
            bandit-report.json
            pip-audit-report.json

  sast-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Semgrep
        run: |
          docker run --rm -v "$PWD:/src" returntocorp/semgrep:latest \
            semgrep scan --config=auto --json --output=semgrep-report.json /src

      - name: Upload Semgrep Report
        uses: actions/upload-artifact@v3
        with:
          name: semgrep-report
          path: semgrep-report.json
```

### 7.2 Local Security Testing

```python
# tests/security/test_security_headers.py
import pytest
from httpx import AsyncClient

async def test_security_headers(client: AsyncClient):
    """Test that security headers are present."""
    response = await client.get("/")

    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "Strict-Transport-Security" in response.headers.get("strict-transport-security", "")
    assert response.headers.get("Content-Security-Policy") is not None

async def test_cors_headers(client: AsyncClient):
    """Test CORS headers."""
    response = await client.options(
        "/api/v1/notes",
        headers={"Origin": "http://localhost:3000"}
    )

    assert "access-control-allow-origin" in response.headers

async def test_rate_limiting(client: AsyncClient):
    """Test rate limiting is enforced."""
    # Make multiple requests
    for i in range(100):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@test.com", "password": "wrong"},
        )

    # Should eventually get 429
    assert response.status_code == 429

# tests/security/test_xss.py
async def test_xss_prevention(client: AsyncClient, auth_headers):
    """Test XSS prevention in note content."""
    xss_payload = '<script>alert("XSS")</script>'

    response = await client.post(
        "/api/v1/notes",
        json={"title": "Test", "content": xss_payload},
        headers=auth_headers
    )

    assert response.status_code == 200

    # Get the note
    note_id = response.json()["id"]
    response = await client.get(f"/api/v1/notes/{note_id}")

    # Script tags should be sanitized
    content = response.json()["content"]
    assert "<script>" not in content
    assert "alert" not in content

# tests/security/test_sql_injection.py
async def test_sql_injection_prevention(client: AsyncClient):
    """Test SQL injection prevention."""
    sql_injection = "'; DROP TABLE users; --"

    response = await client.get(f"/api/v1/notes/{sql_injection}")

    # Should return 404 or 400, not 500
    assert response.status_code in [400, 404, 422]
```

### 7.3 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]
        additional_dependencies: ["bandit[toml]"]

  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black

  - repo: https://github.com/PyCQA/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        additional_dependencies: ["flake8-bugbear", "flake8-security"]

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ["--baseline", ".secrets.baseline"]

  - repo: local
    hooks:
      - id: safety
        name: Safety check
        entry: safety check
        language: system
        pass_filenames: false
```

---

## 8. Security Monitoring & Incident Response

### 8.1 Security Metrics

```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Security metrics
security_events_total = Counter(
    'security_events_total',
    'Total security events',
    ['event_type', 'outcome']
)

failed_logins_total = Counter(
    'failed_logins_total',
    'Total failed login attempts',
    ['ip_address']
)

rate_limit_violations_total = Counter(
    'rate_limit_violations_total',
    'Total rate limit violations',
    ['endpoint']
)

active_sessions = Gauge(
    'active_sessions',
    'Currently active user sessions',
    ['user_id']
)

suspicious_activities_total = Counter(
    'suspicious_activities_total',
    'Total suspicious activities detected',
    ['activity_type']
)
```

### 8.2 Anomaly Detection

```python
# app/services/anomaly_detection.py
from datetime import datetime, timedelta
from typing import List

class AnomalyDetector:
    """Detect suspicious user behavior."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_login_anomalies(
        self,
        user_id: uuid.UUID,
        ip_address: str,
        user_agent: str
    ) -> List[str]:
        """Check for login anomalies."""
        anomalies = []

        # Check for multiple failed attempts from same IP
        recent_failures = await self.db.execute(
            select(AuditLog).where(
                AuditLog.event_type == AuditEventType.LOGIN_FAILED.value,
                AuditLog.ip_address == ip_address,
                AuditLog.created_at > datetime.now(timezone.utc) - timedelta(minutes=15)
            )
        )

        if len(recent_failures.all()) > 5:
            anomalies.append("Multiple failed logins from same IP")

        # Check for login from unusual location
        # (Implementation would involve IP geolocation)

        # Check for new device
        previous_logins = await self.db.execute(
            select(AuditLog).where(
                AuditLog.user_id == user_id,
                AuditLog.event_type == AuditEventType.LOGIN_SUCCESS.value,
                AuditLog.created_at > datetime.now(timezone.utc) - timedelta(days=30)
            )
        )

        seen_devices = set()
        for log in previous_logins.scalars():
            if log.details and 'device_fingerprint' in log.details:
                seen_devices.add(log.details['device_fingerprint'])

        current_device = self._create_device_fingerprint(user_agent)
        if current_device not in seen_devices and len(seen_devices) > 0:
            anomalies.append("Login from new device")

        return anomalies

    async def check_data_access_anomalies(
        self,
        user_id: uuid.UUID
    ) -> List[str]:
        """Check for unusual data access patterns."""
        anomalies = []

        # Check for rapid access to multiple notes
        recent_access = await self.db.execute(
            select(AuditLog).where(
                AuditLog.user_id == user_id,
                AuditLog.event_type == AuditEventType.NOTE_READ.value,
                AuditLog.created_at > datetime.now(timezone.utc) - timedelta(minutes=1)
            )
        )

        if len(recent_access.all()) > 50:
            anomalies.append("Unusual rate of note access")

        return anomalies
```

### 8.3 Incident Response Playbook

```markdown
# Security Incident Response Playbook

## 1. Detection
- Automated alerts from security monitoring
- User reports of suspicious activity
- Security scan findings

## 2. Classification
| Severity | Response Time | Examples |
|----------|---------------|----------|
| Critical | Immediate | Active exploit, data breach |
| High | 1 hour | Privilege escalation attempt |
| Medium | 4 hours | Brute force attack |
| Low | 24 hours | Policy violation |

## 3. Containment
- Disable compromised accounts
- Block malicious IP addresses
- Isolate affected systems

## 4. Eradication
- Remove malware
- Patch vulnerabilities
- Update security rules

## 5. Recovery
- Restore from clean backups
- Reset compromised credentials
- Monitor for recurrence

## 6. Post-Incident
- Root cause analysis
- Update security policies
- Improve detection rules
```

---

## 9. Security Configuration Checklist

### 9.1 Production Checklist

```yaml
# config/security_checklist.yml
production_security:
  authentication:
    - [x] JWT with HS256 or RS256
    - [ ] MFA for admin accounts
    - [ ] Password complexity requirements
    - [ ] Account lockout after failed attempts
    - [ ] Session timeout after inactivity

  authorization:
    - [x] Role-based access control
    - [ ] Resource-level permissions
    - [ ] API key authentication

  data_protection:
    - [x] Password hashing with bcrypt
    - [x] Encryption at rest (database)
    - [ ] Encryption in transit (TLS 1.3)
    - [ ] PII data classification
    - [ ] Data retention policies

  network_security:
    - [ ] WAF configuration
    - [ ] DDoS protection
    - [ ] IP whitelisting for admin
    - [ ] VPN for admin access

  application_security:
    - [x] Input validation
    - [x] XSS prevention
    - [ ] CSRF tokens
    - [x] SQL injection protection
    - [x] Rate limiting
    - [ ] File upload restrictions

  monitoring:
    - [ ] Security event logging
    - [ ] Anomaly detection
    - [ ] Intrusion detection
    - [ ] Real-time alerts

  compliance:
    - [ ] GDPR compliance
    - [ ] SOC 2 preparation
    - [ ] Penetration testing
```

---

## 10. Implementation Roadmap

### Phase 1: Immediate (Week 1)
- [ ] Implement rate limiting with slowapi
- [ ] Add security headers middleware
- [ ] Implement input sanitization
- [ ] Set up security scanning in CI/CD

### Phase 2: Short-term (Weeks 2-4)
- [ ] Implement RBAC system
- [ ] Add audit logging
- [ ] API key management
- [ ] Enhanced token management

### Phase 3: Medium-term (Weeks 5-8)
- [ ] Anomaly detection
- [ ] Security monitoring dashboard
- [ ] Incident response procedures
- [ ] Penetration testing

### Phase 4: Long-term (Weeks 9+)
- [ ] MFA implementation
- [ ] Advanced threat detection
- [ ] Security analytics
- [ ] Compliance certifications

---

**Document History**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-13 | Security Engineer | Initial security design document |
