"""Pagination utilities."""
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import PaginatedResponse

T = TypeVar("T", bound=BaseModel)


async def paginate_query(
    db: AsyncSession,
    query: Select,
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100,
) -> tuple[list, int]:
    """Execute paginated query.

    Args:
        db: Database session
        query: SQLAlchemy select query
        page: Page number (1-indexed)
        page_size: Items per page
        max_page_size: Maximum allowed page size

    Returns:
        tuple: (items, total_count)

    Raises:
        ValueError: If page number is less than 1
    """
    if page < 1:
        raise ValueError("Page number must be >= 1")
    if page_size < 1:
        raise ValueError("Page size must be >= 1")

    # Limit page size
    page_size = min(page_size, max_page_size)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get paginated items
    offset = (page - 1) * page_size
    items_query = query.offset(offset).limit(page_size)
    items = (await db.execute(items_query)).scalars().all()

    return list(items), total


def create_pagination_response(
    items: list[T],
    total: int,
    page: int,
    page_size: int,
    schema_class: type[T],
) -> PaginatedResponse:
    """Create paginated response.

    Args:
        items: List of ORM models
        total: Total number of items
        page: Current page number
        page_size: Items per page
        schema_class: Pydantic schema class for serialization

    Returns:
        PaginatedResponse: Paginated response
    """
    serialized_items = [schema_class.model_validate(item) for item in items]
    return PaginatedResponse.create(
        items=serialized_items,
        total=total,
        page=page,
        page_size=page_size,
    )
