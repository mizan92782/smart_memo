"""
Shared Base Views — Base ViewSet classes for DRY patterns.
"""
from rest_framework import viewsets
from rest_framework.response import Response
from shared.responses.responses import custome_success_response


class BaseViewSet(viewsets.GenericViewSet):
    """
    Base ViewSet providing common response helpers.
    All custom ViewSets should inherit from this.
    """

    def success(self, data=None, message="Success", status_code=200):
        return custome_success_response(data=data, message=message, status_code=status_code)


class BaseModelViewSet(viewsets.ModelViewSet):
    """
    Base ModelViewSet for CRUD operations.
    Override create/update to use standardized responses.
    """
    pass
