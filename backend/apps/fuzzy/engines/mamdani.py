from .utils import clamp, left_shoulder, right_shoulder, triangular


OUTPUT_SETS = {
    "low": {"shape": "left_shoulder", "parameters": [15.0, 35.0]},
    "moderate": {"shape": "triangular", "parameters": [20.0, 42.0, 64.0]},
    "high": {"shape": "triangular", "parameters": [48.0, 72.0, 90.0]},
    "severe": {"shape": "right_shoulder", "parameters": [72.0, 92.0]},
}


def _output_membership(consequent, value):
    output_set = OUTPUT_SETS[consequent]
    parameters = output_set["parameters"]
    if output_set["shape"] == "left_shoulder":
        return left_shoulder(value, *parameters)
    if output_set["shape"] == "right_shoulder":
        return right_shoulder(value, *parameters)
    return triangular(value, *parameters)


def _centroid_of_aggregated_output(active_rules, resolution=0.25, fallback=25.0):
    """Clip consequent sets, aggregate them with max, and calculate area centroid."""
    universe = [index * resolution for index in range(int(100 / resolution) + 1)]
    aggregated = []
    for value in universe:
        membership = max(
            (
                min(rule["strength"], _output_membership(rule["consequent"], value))
                for rule in active_rules
            ),
            default=0.0,
        )
        aggregated.append(membership)

    denominator = sum(aggregated)
    if denominator <= 0:
        return fallback, 0.0
    centroid = sum(value * membership for value, membership in zip(universe, aggregated)) / denominator
    return centroid, denominator * resolution

# Compute membership values for each linguistic variable
def _memberships(relative_response_time, assistance_interactions, completion_ratio):
    time_pressure = {
        "low": left_shoulder(relative_response_time, 0.45, 0.95),
        "normal": triangular(relative_response_time, 0.65, 1.0, 1.45),
        "high": right_shoulder(relative_response_time, 1.15, 2.1),
    }
    assistance = {
        "low": left_shoulder(assistance_interactions, 0.0, 1.5),
        "medium": triangular(assistance_interactions, 0.5, 2.0, 3.5),
        "high": right_shoulder(assistance_interactions, 2.5, 5.0),
    }
    completion = {
        "incomplete": left_shoulder(completion_ratio, 0.15, 0.55),
        "partial": triangular(completion_ratio, 0.25, 0.6, 0.95),
        "complete": right_shoulder(completion_ratio, 0.7, 1.0),
    }
    return {
        "timePressure": time_pressure,
        "assistance": assistance,
        "completion": completion,
    }

# Compute the predicted cognitive friction score using fuzzy inference
def infer_cognitive_friction(
    relative_response_time,
    assistance_interactions,
    completion_ratio,
    task_type,
):
    memberships = _memberships(
        relative_response_time,
        assistance_interactions,
        completion_ratio,
    )
    time_pressure = memberships["timePressure"]
    assistance = memberships["assistance"]
    completion = memberships["completion"]
    is_code_task = str(task_type).lower() == "code"

    rule_specs = [
        (
            "steady_complete",
            min(time_pressure["low"], assistance["low"], completion["complete"]),
            "low",
        ),
        (
            "normal_complete",
            min(time_pressure["normal"], completion["complete"]),
            "low",
        ),
        (
            "minor_delay_or_hint",
            max(
                min(time_pressure["normal"], assistance["medium"]),
                min(time_pressure["high"], completion["complete"]),
            ),
            "moderate",
        ),
        (
            "partial_progress",
            min(completion["partial"], max(time_pressure["normal"], assistance["medium"])),
            "moderate",
        ),
        (
            "slow_with_support",
            min(time_pressure["high"], max(assistance["medium"], assistance["high"])),
            "high",
        ),
        (
            "blocked_incomplete",
            max(
                min(completion["incomplete"], time_pressure["high"]),
                min(completion["incomplete"], assistance["high"]),
            ),
            "severe",
        ),
    ]

    if is_code_task:
        rule_specs.append(("code_workspace_load", 0.35, "moderate"))

    active_rules = [
        {
            "rule": rule_name,
            "strength": round(clamp(strength, 0.0, 1.0), 4),
            "consequent": consequent,
        }
        for rule_name, strength, consequent in rule_specs
        if strength > 0
    ]

    friction, aggregated_area = _centroid_of_aggregated_output(
        active_rules,
        fallback=42.0 if is_code_task else 25.0,
    )

    return {
        "score": clamp(friction),
        "memberships": memberships,
        "rules": active_rules,
        "outputSets": OUTPUT_SETS,
        "aggregatedArea": round(aggregated_area, 4),
        "defuzzification": "centroid_of_aggregated_output_area",
    }
