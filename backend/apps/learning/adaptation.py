from .catalog import TASK_BANK, get_task, tasks_for_module

# Find the task closest to the target difficulty level
def _nearest_task(candidates, target_level, current_task_id):
    ordered = sorted(
        candidates,
        key=lambda task: (
            abs(task["difficultyLevel"] - target_level),
            task["id"] == current_task_id,
            task["difficultyLevel"],
            task["id"],
        ),
    )
    return ordered[0] if ordered else None

# Select the next task based on the fuzzy engine result
def select_next_task(session, current_task, fuzzy_result):
    # parameters of the fuzzy engine result
    mastery = fuzzy_result["knowledgeMastery"]
    friction = fuzzy_result["systemCognitiveFriction"]
    recommendation = fuzzy_result["recommendation"]
    current_level = current_task["difficultyLevel"]

    # recommendation logic
    if recommendation == "increase_or_hold_high_tier" or (mastery >= 75 and friction < 35):
        target_level = min(3, current_level + 1)
        direction = "increase"
        reason = "High mastery with low friction supports a harder or equivalent task."
    elif recommendation == "reduce_difficulty_and_show_support" or friction >= 55 or mastery < 45:
        target_level = max(1, current_level - 1)
        direction = "decrease"
        reason = "High friction or low mastery calls for an easier supported task."
    else:
        target_level = current_level
        direction = "hold"
        reason = "Signals are mixed, so the tutor keeps the current difficulty band."

    module_tasks = tasks_for_module(current_task["moduleId"])
    same_module_candidates = [
        task
        for task in module_tasks
        if task["id"] != current_task["id"] and task["difficultyLevel"] == target_level
    ]
    next_task = _nearest_task(same_module_candidates, target_level, current_task["id"])
    scope = "module"

    # Edge case of no available or properly reccomended task
    if next_task is None:
        wider_module_candidates = [
            task for task in module_tasks if task["id"] != current_task["id"]
        ]
        next_task = _nearest_task(wider_module_candidates, target_level, current_task["id"])

    if next_task is None:
        global_candidates = [
            task for task in TASK_BANK if task["id"] != current_task["id"]
        ]
        next_task = _nearest_task(global_candidates, target_level, current_task["id"])
        scope = "catalog"

    if next_task is None:
        next_task = current_task
        scope = "current_task"

    session.current_module_id = next_task["moduleId"]
    session.current_task_id = next_task["id"]

    return {
        "nextTask": next_task,
        "adaptation": {
            "direction": direction,
            "targetDifficultyLevel": target_level,
            "selectedDifficulty": next_task["difficulty"],
            "selectedScope": scope,
            "reason": reason,
            "signals": {
                "knowledgeMastery": mastery,
                "systemCognitiveFriction": friction,
                "recommendation": recommendation,
            },
        },
    }

# Preview the next task based on the current session state and optional current task ID
def preview_adaptation(session, current_task_id=None):
    current_task = get_task(current_task_id or session.current_task_id)
    if current_task is None:
        current_task = get_task(session.current_task_id)
    fuzzy_result = {
        "knowledgeMastery": session.aggregate_mastery,
        "systemCognitiveFriction": session.aggregate_friction,
        "recommendation": session.latest_recommendation,
    }
    return select_next_task(session, current_task, fuzzy_result)
