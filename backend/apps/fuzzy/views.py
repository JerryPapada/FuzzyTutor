from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .engines import evaluate_learning_state
from .serializers import FuzzyEvaluationInputSerializer, FuzzyEvaluationOutputSerializer


@extend_schema(
    tags=["fuzzy"],
    summary="Evaluate learner state with ANFIS and Mamdani engines",
    description=(
        "Runs the trained ANFIS mastery model and Mamdani cognitive-friction model "
        "for a standalone payload. Learning submissions should usually use "
        "/api/learning/submissions/ so the backend can persist telemetry."
    ),
    request=FuzzyEvaluationInputSerializer,
    responses={200: FuzzyEvaluationOutputSerializer},
)
@api_view(["POST"])
def evaluate(request):
    serializer = FuzzyEvaluationInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    result = evaluate_learning_state(serializer.validated_data)
    return Response(FuzzyEvaluationOutputSerializer(result).data)
