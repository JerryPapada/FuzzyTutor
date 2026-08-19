from .anfis_training import (
    DEFAULT_CONSEQUENT_WEIGHTS,
    RULE_NAMES,
    consequent_output,
    feature_vector,
    load_trained_parameters,
    performance_evidence,
)
from .utils import clamp, left_shoulder, right_shoulder, triangular, weighted_average

def correctness_signal(is_correct, completion_ratio):
    return performance_evidence(is_correct, completion_ratio)


def memberships(task_weight, historical_grade, completion_ratio, correctness_score):
    """Fuzzify the four learner signals used by the mastery rules."""
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


def rule_strengths(membership_values):
    """Return the five ANFIS consequent strengths with complete input coverage."""
    history = membership_values["history"]
    completion = membership_values["completion"]
    correctness = membership_values["correctness"]
    challenge = membership_values["challenge"]
    strengths = {
        "secure_prior_mastery": min(
            history["high"],
            completion["high"],
            correctness["strong"],
        ),
        "developing_mastery": max(
            min(history["medium"], completion["high"]),
            min(history["high"], correctness["emerging"]),
        ),
        "productive_challenge": min(
            challenge["advanced"],
            completion["high"],
            correctness["strong"],
        ),
        "fragile_progress": max(
            min(history["medium"], completion["medium"]),
            min(correctness["emerging"], completion["medium"]),
        ),
        "knowledge_gap": max(
            min(history["low"], correctness["weak"]),
            min(completion["low"], correctness["weak"]),
        ),
    }

    coverage_guard_used = not any(strength > 0 for strength in strengths.values())
    if coverage_guard_used:
        # The named pedagogical rules intentionally form a compact rule base rather
        # than a full Cartesian product. Route a mixed but valid combination through
        # the trained developing-mastery consequent, and expose that decision in the
        # trace instead of silently returning a non-fuzzy fallback.
        strengths["developing_mastery"] = min(
            max(challenge.values()),
            max(history.values()),
            max(completion.values()),
            max(correctness.values()),
        )

    return strengths, coverage_guard_used


def predict_mastery(
    task_weight,
    historical_grade,
    completion_ratio,
    task_type,
    is_correct=None,
):
    """Predict mastery and return enough intermediate state to explain it."""
    correctness_score = correctness_signal(is_correct, completion_ratio)
    membership_values = memberships(
        task_weight,
        historical_grade,
        completion_ratio,
        correctness_score,
    )
    trained_parameters = load_trained_parameters()
    consequent_weights = (
        trained_parameters.get("consequentWeights")
        if trained_parameters
        else DEFAULT_CONSEQUENT_WEIGHTS
    )
    features = feature_vector(
        task_weight,
        historical_grade,
        completion_ratio,
        correctness_score,
        task_type,
    )
    strengths, coverage_guard_used = rule_strengths(membership_values)
    rule_specs = [
        (
            rule_name,
            strengths[rule_name],
            consequent_output(consequent_weights[rule_name], features),
        )
        for rule_name in RULE_NAMES
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
        fallback=consequent_output(DEFAULT_CONSEQUENT_WEIGHTS["developing_mastery"], features),
    )

    return {
        "score": clamp(mastery),
        "memberships": membership_values,
        "rules": active_rules,
        "correctnessSignal": round(correctness_score, 2),
        "coverageGuardUsed": coverage_guard_used,
        "contributionWeights": consequent_weights,
        "modelType": "trained_anfis" if trained_parameters else "transparent_rule_weighted_anfis_style",
        "trainingMetadata": trained_parameters.get("metadata") if trained_parameters else None,
    }
