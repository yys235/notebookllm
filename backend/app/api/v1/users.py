"""User management routes."""
from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, DBSession
from app.schemas.user import UserRead, UserUpdate
from app.services.user import UserService

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def get_current_user(
    current_user: CurrentUser,
):
    """Get current authenticated user.

    Args:
        current_user: Current user from token

    Returns:
        UserRead: Current user
    """
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
async def update_current_user(
    data: UserUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Update current user profile.

    Args:
        data: Update data
        current_user: Current user from token
        db: Database session

    Returns:
        UserRead: Updated user
    """
    service = UserService(db)
    try:
        updated = await service.update(current_user, data)
        return UserRead.model_validate(updated)
    except ValueError as e:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
