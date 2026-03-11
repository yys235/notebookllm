"""File storage service for handling image uploads."""
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.core.logger import get_logger

logger = get_logger(__name__)

# Allowed image types
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}

# Max file size: 5MB
MAX_FILE_SIZE = 5 * 1024 * 1024

# Upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class StorageService:
    """Service for handling file uploads and storage."""

    @staticmethod
    def _get_upload_path(user_id: str) -> Path:
        """Get upload directory for a user."""
        user_dir = UPLOAD_DIR / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    @staticmethod
    async def save_image(
        file: UploadFile,
        user_id: str,
    ) -> dict:
        """
        Save an uploaded image file.

        Args:
            file: The uploaded file
            user_id: The user's ID

        Returns:
            dict with file info including URL

        Raises:
            ValueError: If file type not allowed or file too large
        """
        # Validate file type
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError(
                f"Invalid file type: {file.content_type}. "
                f"Allowed types: {', '.join(ALLOWED_IMAGE_TYPES.keys())}"
            )

        # Read file content
        content = await file.read()

        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            raise ValueError(
                f"File too large: {len(content) / 1024 / 1024:.2f}MB. "
                f"Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
            )

        # Generate unique filename
        file_ext = ALLOWED_IMAGE_TYPES[file.content_type]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        filename = f"{timestamp}_{unique_id}{file_ext}"

        # Get user upload directory
        user_dir = StorageService._get_upload_path(user_id)
        file_path = user_dir / filename

        # Save file
        file_path.write_bytes(content)

        # Generate URL
        file_url = f"/uploads/{user_id}/{filename}"

        logger.info(
            "Image saved",
            user_id=user_id,
            filename=filename,
            size=file_path.stat().st_size,
        )

        return {
            "url": file_url,
            "filename": filename,
            "size": file_path.stat().st_size,
            "content_type": file.content_type,
        }

    @staticmethod
    def delete_image(user_id: str, filename: str) -> bool:
        """
        Delete an uploaded image.

        Args:
            user_id: The user's ID
            filename: The filename to delete

        Returns:
            True if deleted, False if not found
        """
        user_dir = StorageService._get_upload_path(user_id)
        file_path = user_dir / filename

        if file_path.exists() and file_path.is_file():
            # Security check: ensure file is in user's directory
            if str(file_path.resolve()).startswith(str(user_dir.resolve())):
                file_path.unlink()
                logger.info("Image deleted", user_id=user_id, filename=filename)
                return True

        return False

    @staticmethod
    def get_image_path(user_id: str, filename: str) -> Optional[Path]:
        """
        Get the path to an uploaded image.

        Args:
            user_id: The user's ID
            filename: The filename

        Returns:
            Path to the file or None if not found
        """
        user_dir = StorageService._get_upload_path(user_id)
        file_path = user_dir / filename

        if file_path.exists() and file_path.is_file():
            # Security check
            if str(file_path.resolve()).startswith(str(user_dir.resolve())):
                return file_path

        return None
