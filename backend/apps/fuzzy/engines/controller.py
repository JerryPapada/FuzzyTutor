from .anfis import predict_mastery
from .mamdani import infer_cognitive_friction
from .utils import clamp


FOCUS_THRESHOLDS = {
    "steady_friction_max": 25.0,
    "steady_mastery_min": 65.0,
    "support_friction_max": 55.0,
    "high_mastery_min": 75.0,
    "low_mastery_max": 45.0,
}

def focus_state_for(friction, mastery):
    """Translate the two numeric outputs into a calm learner-facing state."""
    if (friction < FOCUS_THRESHOLDS["steady_friction_max"]
        and mastery >= FOCUS_THRESHOLDS["steady_mastery_min"]
    ):
        return "Focused & Steady"
    if friction < FOCUS_THRESHOLDS["support_friction_max"]:
        return "Needs Support"
    return "Frustrated"


def recommendation_for(mastery, friction):
    """Choose the requested adaptation; the catalog applies floor/ceiling limits."""
    if (
        mastery >= FOCUS_THRESHOLDS["high_mastery_min"]
        and friction < 35.0
    ):
        return "increase_or_hold_high_tier"
    # Either low mastery or high friction is enough to request the safer path.
    if (
        mastery < FOCUS_THRESHOLDS["low_mastery_max"]
        or friction >= FOCUS_THRESHOLDS["support_friction_max"]
    ):
        return "reduce_difficulty_and_show_support"
    return "hold_current_tier"

def support_message_for(focus_state, recommendation):
    """Explain the action without treating every non-steady state as failure."""
    if recommendation == "increase_or_hold_high_tier":
        if focus_state == "Focused & Steady":
            return "The learner looks ready for the next challenge."
        return "Advance while keeping a hint or short explanation available."
    if recommendation == "reduce_difficulty_and_show_support":
        return "Offer a guided prompt and additional support for the next task."
    if focus_state == "Focused & Steady":
        return "Continue in the current band and reinforce this steady progress."
    return "Continue in the current band with an optional hint or short explanation."

def evaluate_learning_state(inputs):
    """Run both engines and return their combined decision and audit trace."""
    task_weight = clamp(inputs["taskMetricWeight"])
    historical_grade = clamp(inputs["historicalGradeAverage"])
    relative_time = max(0.0, float(inputs["relativeResponseTime"]))
    assistance = max(0, int(inputs["assistanceInteractions"]))
    completion_ratio = clamp(inputs["completionRatio"], 0.0, 1.0)
    task_type = str(inputs["taskType"]).lower()

    mastery_result = predict_mastery(
        task_weight=task_weight,
        historical_grade=historical_grade,
        completion_ratio=completion_ratio,
        task_type=task_type,
        is_correct=inputs.get("isCorrect"),
    )
    friction_result = infer_cognitive_friction(
        relative_response_time=relative_time,
        assistance_interactions=assistance,
        completion_ratio=completion_ratio,
        task_type=task_type,
    )

    mastery = mastery_result["score"]
    friction = friction_result["score"]
    focus_state = focus_state_for(friction, mastery)
    recommendation = recommendation_for(mastery, friction)

    return {
        "knowledgeMastery": round(mastery, 2),
        "systemCognitiveFriction": round(friction, 2),
        "focusState": focus_state,
        "recommendation": recommendation,
        "supportMessage": support_message_for(focus_state, recommendation),
        "inputSnapshot": {
            "taskMetricWeight": round(task_weight, 2),
            "historicalGradeAverage": round(historical_grade, 2),
            "relativeResponseTime": round(relative_time, 2),
            "assistanceInteractions": assistance,
            "completionRatio": round(completion_ratio, 2),
            "taskType": task_type,
        },
        "engineTrace": {
            "anfis": mastery_result,
            "mamdani": friction_result,
            "thresholds": FOCUS_THRESHOLDS,
        },
    }
