from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import serializers

@extend_schema(
    tags=["core"],
    summary="Health check",
    responses=inline_serializer(
        name="HealthResponse",
        fields={
            "status": serializers.CharField(),
            "service": serializers.CharField(),
            "framework": serializers.CharField(),
        },
    ),
)
@api_view(["GET"])
def health(request):
    return Response(
        {
            "status": "ok",
            "service": "FuzzyTutor backend",
            "framework": "Django REST Framework",
        }
    )
