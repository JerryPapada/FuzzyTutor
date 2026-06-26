from rest_framework.decorators import api_view
from rest_framework.response import Response


def clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(maximum, float(value)))


@api_view(["POST"])
def evaluate(request):
    payload = request.data
    task_weight = clamp(payload.get("taskMetricWeight", 50))
    historical_grade = clamp(payload.get("historicalGradeAverage", 70))
    relative_time = max(0.0, float(payload.get("relativeResponseTime", 1.0)))
    assistance = max(0, int(payload.get("assistanceInteractions", 0)))

    # Temporary deterministic approximation. Replace with ANFIS + Mamdani engines.
    mastery = clamp((0.42 * historical_grade) + (0.38 * (100 - task_weight)) + 20)
    friction = clamp((abs(relative_time - 1.0) * 45) + (assistance * 12))

    if friction < 30:
        focus_state = "Focused & Steady"
    elif friction < 65:
        focus_state = "Needs Support"
    else:
        focus_state = "Frustrated"

    if mastery >= 70 and friction < 35:
        recommendation = "increase_or_hold_high_tier"
    elif mastery < 50 and friction >= 60:
        recommendation = "reduce_difficulty_and_show_support"
    else:
        recommendation = "hold_current_tier"

    return Response(
        {
            "knowledgeMastery": round(mastery, 2),
            "systemCognitiveFriction": round(friction, 2),
            "focusState": focus_state,
            "recommendation": recommendation,
        }
    )
