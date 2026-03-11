"""Validation utilities."""
import uuid
from fastapi import HTTPException, status


def validate_uuid(value: str, field_name: str = "ID") -> uuid.UUID:
    """Validate and parse UUID string.

    Args:
        value: UUID string to validate
        field_name: Field name for error message

    Returns:
        UUID: Parsed UUID object

    Raises:
        HTTPException: If value is not a valid UUID
    """
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {field_name}: must be a valid UUID",
        )
