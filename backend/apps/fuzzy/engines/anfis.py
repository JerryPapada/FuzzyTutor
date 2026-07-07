from .utils import clamp, left_shoulder, right_shoulder, triangular, weighted_average


def _correctness_signal(is_correct, completion_ratio):
    if is_correct is True:
        return 100.0
    if is_correct is False:
        return 20.0
    return 45.0 + (completion_ratio * 35.0)


def _memberships(task_weight, historical_grade, completion_ratio, correctness_score):
    return {
        "challenge": {
            "foundation": left_shoulder(task_weight, 35.0, 60.0),
            "intermediate": triangular(task_weight, 35.0, 58.0, 82.0),
            "advanced": right_shoulder(task_weight, 65.0, 85.0),
        },
        "history": {
            "low": left_shoulder(historical_grade, 35.0, 60.0),
            "medium": triangular(historical_grade, 45.0, 68.0, 86.0),
            "high": right_shoulder(historical_grade, 72.0, 90.0),
        },
        "completion": {
            "low": left_shoulder(completion_ratio, 0.2, 0.65),
            "medium": triangular(completion_ratio, 0.35, 0.7, 0.98),
            "high": right_shoulder(completion_ratio, 0.75, 1.0),
        },
        "correctness": {
            "weak": left_shoulder(correctness_score, 35.0, 65.0),
            "emerging": triangular(correctness_score, 45.0, 70.0, 90.0),
            "strong": right_shoulder(correctness_score, 75.0, 95.0),
        },
    }


def predict_mastery(
    task_weight,
    historical_grade,
    completion_ratio,
    task_type,
    is_correct=None,
):
    correctness_score = _correctness_signal(is_correct, completion_ratio)
    memberships = _memberships(
        task_weight,
        historical_grade,
        completion_ratio,
        correctness_score,
    )
    history = memberships["history"]
    completion = memberships["completion"]
    correctness = memberships["correctness"]
    challenge = memberships["challenge"]

    code_penalty = 3.0 if str(task_type).lower() == "code" and completion_ratio < 1 else 0.0

    def consequent(history_weight, completion_weight, correctness_weight, challenge_weight):
        value = (
            (history_weight * historical_grade)
            + (completion_weight * completion_ratio * 100.0)
            + (correctness_weight * correctness_score)
            + (challenge_weight * task_weight)
            - code_penalty
        )
        return clamp(value)

    rule_specs = [
        (
            "secure_prior_mastery",
            min(history["high"], completion["high"], correctness["strong"]),
            consequent(0.48, 0.22, 0.22, 0.08),
        ),
        (
            "developing_mastery",
            max(
                min(history["medium"], completion["high"]),
                min(history["high"], correctness["emerging"]),
            ),
            consequent(0.52, 0.24, 0.18, 0.06),
        ),
        (
            "productive_challenge",
            min(challenge["advanced"], completion["high"], correctness["strong"]),
            consequent(0.42, 0.23, 0.25, 0.10),
        ),
        (
            "fragile_progress",
            max(
                min(history["medium"], completion["medium"]),
                min(correctness["emerging"], completion["medium"]),
            ),
            consequent(0.58, 0.23, 0.15, 0.04),
        ),
        (
            "knowledge_gap",
            max(
                min(history["low"], correctness["weak"]),
                min(completion["low"], correctness["weak"]),
            ),
            consequent(0.60, 0.20, 0.16, 0.04),
        ),
    ]

    active_rules = [
        {
            "rule": rule_name,
            "strength": round(clamp(strength, 0.0, 1.0), 4),
            "output": round(output, 4),
        }
        for rule_name, strength, output in rule_specs
        if strength > 0
    ]

    mastery = weighted_average(
        [(rule["strength"], rule["output"]) for rule in active_rules],
        fallback=consequent(0.55, 0.22, 0.18, 0.05),
    )

    return {
        "score": clamp(mastery),
        "memberships": memberships,
        "rules": active_rules,
        "correctnessSignal": round(correctness_score, 2),
        "contributionWeights": {
            "historicalGradeAverage": 0.55,
            "completionRatio": 0.22,
            "correctnessOrCompletionSignal": 0.18,
            "taskMetricWeight": 0.05,
        },
        "modelType": "transparent_rule_weighted_anfis_style",
    }
