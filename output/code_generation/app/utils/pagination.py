from math import ceil
from typing import Tuple, TypeVar, List

from app.schemas.recordings import PaginationParams

T = TypeVar("T")

def calculate_pagination_params(
    total_items: int,
    pagination_params: PaginationParams
) -> Tuple[int, int, int]:
    """
    Calculates total pages, offset, and limit for pagination.

    Args:
        total_items: The total number of items available.
        pagination_params: An instance of PaginationParams containing page and size.

    Returns:
        A tuple containing (total_pages, offset, limit).
    """
    page = pagination_params.page
    size = pagination_params.size

    total_pages = ceil(total_items / size) if total_items > 0 else 0
    offset = (page - 1) * size
    limit = size

    # Ensure offset does not exceed total items if page is too high
    if offset >= total_items and total_items > 0:
        offset = max(0, (total_pages - 1) * size)
        page = total_pages
    elif total_items == 0:
        offset = 0
        page = 1

    return total_pages, offset, limit

def paginate_query(
    query,
    pagination_params: PaginationParams
):
    """
    Applies pagination (offset and limit) to a SQLAlchemy query.

    Args:
        query: The SQLAlchemy query object.
        pagination_params: An instance of PaginationParams.

    Returns:
        The SQLAlchemy query with offset and limit applied.
    """
    offset = (pagination_params.page - 1) * pagination_params.size
    limit = pagination_params.size
    return query.offset(offset).limit(limit)