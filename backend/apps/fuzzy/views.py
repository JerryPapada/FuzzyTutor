from rest_framework.decorators import api_view
from rest_framework.response import Response


def clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(maximum, float(value)))


def bounded_ratio(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def focus_state_for(friction, mastery):
    if friction < 25 and mastery >= 65:
        return "Focused & Steady"
    if friction < 55:
        return "Needs Support"
    return "Frustrated"


def recommendation_for(mastery, friction):
    if mastery >= 75 and friction < 35:
        return "increase_or_hold_high_tier"
    if mastery < 45 and friction >= 55:
        return "reduce_difficulty_and_show_support"
    return "hold_current_tier"


@api_view(["POST"])
def evaluate(request):
    payload = request.data
    task_weight = clamp(payload.get("taskMetricWeight", 50))
    historical_grade = clamp(payload.get("historicalGradeAverage", 70))
    relative_time = max(0.0, float(payload.get("relativeResponseTime", 1.0)))
    assistance = max(0, int(payload.get("assistanceInteractions", 0)))
    completion_ratio = bounded_ratio(payload.get("completionRatio", 1.0))
    task_type = str(payload.get("taskType", "mcq"))
    is_correct = payload.get("isCorrect")

    mastery = clamp(
        (0.45 * historical_grade)
        + (0.30 * (100 - task_weight))
        + (0.25 * (completion_ratio * 100))
    )
    if is_correct is True:
        mastery = clamp(mastery + 6)
    elif is_correct is False:
        mastery = clamp(mastery - 4)

    friction = clamp(
        (abs(relative_time - 1.0) * 45)
        + (assistance * 12)
        + (10 if task_type == "code" else 0)
        - (completion_ratio * 10)
    )

    focus_state = focus_state_for(friction, mastery)
    recommendation = recommendation_for(mastery, friction)

    if focus_state == "Focused & Steady":
        support_message = "The student looks ready for the next challenge."
    elif focus_state == "Needs Support":
        support_message = "Keep the tier steady and add a short explanation."
    else:
        support_message = "Reduce the difficulty and offer a guided prompt."

    return Response(
        {
            "knowledgeMastery": round(mastery, 2),
            "systemCognitiveFriction": round(friction, 2),
            "focusState": focus_state,
            "recommendation": recommendation,
            "supportMessage": support_message,
            "inputSnapshot": {
                "taskMetricWeight": task_weight,
                "historicalGradeAverage": historical_grade,
                "relativeResponseTime": round(relative_time, 2),
                "assistanceInteractions": assistance,
                "completionRatio": round(completion_ratio, 2),
                "taskType": task_type,
            },
        }
    )
