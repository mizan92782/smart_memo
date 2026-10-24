from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import exception_handler
from rest_framework.exceptions import Throttled


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if isinstance(exc, Throttled):
        wait = exc.wait
        if wait is not None:
            minutes = int(wait // 60)
            seconds = int(wait % 60)
            if minutes > 0:
                time_msg = f"{minutes} minute{'s' if minutes > 1 else ''}"
            else:
                time_msg = f"{seconds} second{'s' if seconds > 1 else ''}"
            message = f"Too many attempts. Please try again after {time_msg}."
        else:
            message = "Too many attempts. Please try again after 5 minutes."
        response.data = {"error": True, "message": message, "data": None, "success": False}
    return response


def custome_success_response( data_title="data", data=None, message="Success", status_code=status.HTTP_200_OK
):
    return Response(
        {"success": True,"message": message, data_title: data,"error": False, },
        status=status_code,
    )
    
def custome_error_response(message="Error", status_code=status.HTTP_400_BAD_REQUEST, data=None):
    return Response(
        {"error": True, "message": message, "data": data, "success": False},
        status=status_code,
    )