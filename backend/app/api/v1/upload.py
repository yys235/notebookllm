"""File upload routes."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import CurrentUser
from app.services.storage import StorageService

router = APIRouter()


@router.post("/images", status_code=status.HTTP_201_CREATED)
async def upload_image(
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    """
    Upload an image file.

    Accepts: JPEG, PNG, GIF, WebP, SVG
    Max size: 5MB

    Returns the image URL that can be used in notes.
    """
    try:
        result = await StorageService.save_image(
            file=file,
            user_id=str(current_user.id),
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image",
        )


@router.delete("/images/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    filename: str,
    current_user: CurrentUser,
):
    """Delete an uploaded image."""
    deleted = StorageService.delete_image(
        user_id=str(current_user.id),
        filename=filename,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )
