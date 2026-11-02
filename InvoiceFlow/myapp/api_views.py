from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def api_health_check(request):
    """
    Health check endpoint to verify Django REST Framework and frontend connectivity.
    Does not interfere with any existing template views.
    """
    return Response(
        {
            "status": "ok",
            "message": "InvoiceFlow API is running",
            "version": "1.0",
        }
    )

