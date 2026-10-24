from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


def swagger_documentation(
    *,
    title: str,
    description: str,
    serializer=None,
    tags=None,
    status_code: int = 200,
    method: str | None = None,
):
    """
    Custom reusable swagger decorator
    Works for ViewSet methods and @action methods
    """

    responses = {
        status_code: openapi.Response(
            description="Success",
            schema=serializer
        ),
        400: "Validation error",
        401: "Unauthorized",
        404: "Not found",
    }

    kwargs = {
        "operation_summary": title,
        "operation_description": description,
        "responses": responses,
        "tags": tags or [],
    }

    #  ADD request_body ONLY for write methods
    write_methods = ["post", "put", "patch"]

    if serializer:
        if method and method.lower() in write_methods:
            kwargs["request_body"] = serializer
        elif method is None:
            # default ViewSet write actions (create / update / partial_update)
            kwargs["request_body"] = serializer

    # ADD method ONLY for @action
    if method:
        kwargs["method"] = method.lower()

    return swagger_auto_schema(**kwargs)
    