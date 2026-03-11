"""Authentication routes."""
from datetime import timedelta, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logger import get_logger
from app.core.security import create_access_token
from app.dependencies import CurrentUser
from app.schemas.user import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    SessionInfo,
    TokenResponse,
    UserCreate,
    UserRead,
)
from app.services.auth import AuthService
from app.services.user import UserService

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()

# Type aliases
DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    request: Request,
    db: DBSession,
):
    """Register a new user account.

    Validates password confirmation and creates a new user.
    """
    # Validate password confirmation
    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    # Create user (password confirmation excluded)
    user_data = UserCreate(
        email=data.email,
        username=data.username,
        full_name=data.full_name,
        password=data.password,
    )

    user_service = UserService(db)
    try:
        user = await user_service.create(user_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    logger.info(
        "User registered",
        user_id=str(user.id),
        email=user.email,
        ip=request.client.host,
    )

    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    db: DBSession,
):
    """Authenticate user and return tokens.

    Accepts either username or email in the username field.
    """
    user_service = UserService(db)
    auth_service = AuthService(db)

    user = await user_service.authenticate(data.username, data.password)

    if user is None:
        logger.warning(
            "Failed login attempt",
            username=data.username,
            ip=request.client.host,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # Create refresh token
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host
    refresh_token_record = await auth_service.create_refresh_token(
        user_id=user.id,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    logger.info(
        "User logged in",
        user_id=str(user.id),
        ip=request.client.host,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_record.token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login/oauth2", response_model=TokenResponse)
async def login_oauth2(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    db: DBSession,
):
    """OAuth2 compatible login endpoint.

    Useful for OpenAPI documentation integration and OAuth2 clients.
    """
    user_service = UserService(db)
    auth_service = AuthService(db)

    user = await user_service.authenticate(form_data.username, form_data.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # Create tokens
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host
    refresh_token_record = await auth_service.create_refresh_token(
        user_id=user.id,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    logger.info(
        "User logged in via OAuth2",
        user_id=str(user.id),
        ip=request.client.host,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_record.token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    request: Request,
    db: DBSession,
):
    """Refresh access token using refresh token.

    Validates the refresh token and returns a new access token.
    The refresh token is rotated (old one revoked, new one issued).
    """
    auth_service = AuthService(db)
    user_service = UserService(db)

    # Verify refresh token
    token_record, error_msg = await auth_service.verify_refresh_token(data.refresh_token)

    if token_record is None:
        logger.warning("Invalid refresh token attempt", ip=request.client.host)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg or "Invalid refresh token",
        )

    # Get user
    user = await user_service.get_by_id(token_record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new access token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # Rotate refresh token
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host
    new_refresh_token = await auth_service.rotate_refresh_token(
        old_token=token_record,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    logger.info(
        "Token refreshed",
        user_id=str(user.id),
        ip=request.client.host,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token.token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: RefreshTokenRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Logout user by revoking their refresh token.

    The access token will remain valid until it expires.
    """
    auth_service = AuthService(db)

    # Revoke the refresh token
    token_record = await auth_service.get_refresh_token(data.refresh_token)

    if token_record and token_record.user_id == current_user.id:
        await auth_service.revoke_refresh_token(token_record)
        logger.info("User logged out", user_id=str(current_user.id))
    else:
        # Token might be invalid, but that's okay for logout
        logger.info(
            "Logout with invalid token",
            user_id=str(current_user.id),
        )


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    current_user: CurrentUser,
    db: DBSession,
):
    """Logout from all devices by revoking all refresh tokens."""
    auth_service = AuthService(db)

    count = await auth_service.revoke_user_tokens(user_id=current_user.id)

    logger.info(
        "User logged out from all devices",
        user_id=str(current_user.id),
        revoked_count=count,
    )


@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: CurrentUser,
):
    """Get current authenticated user information."""
    return UserRead.model_validate(current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Change current user password.

    Requires the old password for verification.
    All existing refresh tokens will be revoked.
    """
    auth_service = AuthService(db)

    try:
        await auth_service.change_password(
            user_id=current_user.id,
            hashed_password=current_user.hashed_password,
            data=data,
        )

        logger.info(
            "Password changed",
            user_id=str(current_user.id),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(
    current_user: CurrentUser,
    request: Request,
    db: DBSession,
):
    """List all active sessions for the current user.

    Returns information about all devices/sessions with active tokens.
    """
    auth_service = AuthService(db)

    sessions = await auth_service.get_user_sessions(user_id=current_user.id)

    # Try to identify current session by matching user agent and IP
    current_user_agent = request.headers.get("user-agent", "")[:100]
    current_ip = request.client.host

    result = []
    for session in sessions:
        is_current = (
            session.user_agent == current_user_agent and session.ip_address == current_ip
        )
        result.append(
            SessionInfo(
                id=str(session.id),
                created_at=session.created_at,
                expires_at=session.expires_at,
                user_agent=session.user_agent,
                ip_address=session.ip_address,
                is_current=is_current,
            )
        )

    return result


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Revoke a specific session.

    Cannot revoke the current session.
    """
    from app.models.user import RefreshToken
    from sqlalchemy import select

    # Verify session belongs to user
    query = select(RefreshToken).where(
        and_(
            RefreshToken.id == session_id,
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked_at == None,
        )
    )

    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Revoke session
    session.revoked_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(
        "Session revoked",
        user_id=str(current_user.id),
        session_id=session_id,
    )


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
async def send_verification_email(
    current_user: CurrentUser,
):
    """Send email verification link.

    TODO: Implement email service integration.
    """
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified",
        )

    # TODO: Send verification email
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Email service not yet implemented",
    )


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    email: str,
):
    """Initiate password reset.

    TODO: Implement password reset email flow.
    """
    # TODO: Send password reset email
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password reset not yet implemented",
    )


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    token: str,
    new_password: str,
    db: DBSession,
):
    """Complete password reset with token.

    TODO: Implement password reset completion.
    """
    # TODO: Verify reset token and update password
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password reset not yet implemented",
    )
