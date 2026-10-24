"""
Shared Pagination — Custom pagination classes for project-wide use.
"""
from rest_framework.pagination import PageNumberPagination, CursorPagination
from rest_framework.response import Response


class StandardResultsPagination(PageNumberPagination):
    """
    Standard page-number pagination.
    Usage: Set pagination_class = StandardResultsPagination on any ViewSet.
    
    Query params:
        ?page=2&page_size=20
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response({
            "success": True,
            "message": "Data retrieved successfully",
            "data": data,
            "pagination": {
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "has_next": self.page.has_next(),
                "has_previous": self.page.has_previous(),
            },
            "errors": None,
        })

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'count': {'type': 'integer'},
                'total_pages': {'type': 'integer'},
                'current_page': {'type': 'integer'},
                'next': {'type': 'string', 'nullable': True},
                'previous': {'type': 'string', 'nullable': True},
                'results': schema,
            },
        }


class SmallResultsPagination(StandardResultsPagination):
    """
    Small page size (5 items per page).
    Use for endpoints that return large data per item.
    """
    page_size = 5
    max_page_size = 50


class LargeResultsPagination(StandardResultsPagination):
    """
    Larger page size (25 items per page).
    Use for lightweight list endpoints.
    """
    page_size = 25
    max_page_size = 200


class TimestampCursorPagination(CursorPagination):
    """
    Cursor-based pagination ordered by created_at.
    Ideal for real-time feeds and infinite scroll.
    More efficient than offset pagination for large datasets.
    """
    page_size = 20
    ordering = '-created_at'
    cursor_query_param = 'cursor'
