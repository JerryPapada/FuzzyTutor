from .catalog import get_task, tasks_for_module
from .progress import (
    activate_module,
    curriculum_complete,
    get_module_progress,
    next_unfinished_module_id,
)


def target_difficulty(current_task, fuzzy_result):
    mastery = fuzzy_result["knowledgeMastery"]
    friction = fuzzy_result["systemCognitiveFriction"]
    recommendation = fuzzy_result["recommendation"]
    current_level = current_task["difficultyLevel"]

    if recommendation == "increase_or_hold_high_tier" or (
        mastery >= 75 and friction < 35
    ):
        return (
            min(3, current_level + 1),
            "increase",
            "High mastery with low friction supports a harder or equivalent task.",
        )
    if (
        recommendation == "reduce_difficulty_and_show_support"
        or friction >= 55
        or mastery < 45
    ):
        return (
            max(1, current_level - 1),
            "decrease",
            "High friction or low mastery calls for an easier supported task.",
        )
    return (
        current_level,
        "hold",
        "Signals are mixed, so the tutor keeps the current difficulty band.",
    )


def preferred_task_type(session, module_id):
    task_types = list(
        session.submissions.filter(module_id=module_id).values_list(
            "task_type", flat=True
        )
    )
    mcq_count = task_types.count("mcq")
    code_count = task_types.count("code")
    return "code" if mcq_count > code_count else "mcq"


def choose_task(session, module_id, target_level, completed_task_ids):
    candidates = [
        task
        for task in tasks_for_module(module_id)
        if task["id"] not in completed_task_ids
    ]
    if not candidates:
        return None

    progress = get_module_progress(session, module_id)
    if progress.attempted_task_count < 6:
        preferred_type = preferred_task_type(session, module_id)
        preferred_candidates = [
            task for task in candidates if task["type"] == preferred_type
        ]
        if preferred_candidates:
            candidates = preferred_candidates

    return min(
        candidates,
        key=lambda task: (
            abs(task["difficultyLevel"] - target_level),
            task["difficultyLevel"],
            task["id"],
        ),
    )


def select_next_task(
    session,
    current_task,
    fuzzy_result,
    module_decision,
):
    target_level, direction, reason = target_difficulty(
        current_task,
        fuzzy_result,
    )
    completed_task_ids = set(
        session.submissions.values_list("task_id", flat=True)
    )
    module_outcome = module_decision["outcome"]
    next_task = None
    scope = "module"

    if module_outcome == "continue":
        next_task = choose_task(
            session,
            current_task["moduleId"],
            target_level,
            completed_task_ids,
        )

    if next_task is None:
        next_module_id = next_unfinished_module_id(
            session,
            current_task["moduleId"],
        )
        module_decision["nextModuleId"] = next_module_id
        if next_module_id is not None:
            activate_module(session, next_module_id)
            next_task = choose_task(
                session,
                next_module_id,
                target_level,
                completed_task_ids,
            )
            scope = "next_module"

    is_curriculum_complete = curriculum_complete(session)
    if next_task is None:
        next_task = current_task
        scope = "curriculum_complete"

    session.current_module_id = next_task["moduleId"]
    session.current_task_id = next_task["id"]
    return {
        "nextTask": next_task,
        "moduleDecision": module_decision,
        "adaptation": {
            "direction": direction,
            "targetDifficultyLevel": target_level,
            "selectedDifficulty": next_task["difficulty"],
            "selectedScope": scope,
            "curriculumComplete": is_curriculum_complete,
            "reason": reason,
            "signals": {
                "knowledgeMastery": fuzzy_result["knowledgeMastery"],
                "systemCognitiveFriction": fuzzy_result[
                    "systemCognitiveFriction"
                ],
                "recommendation": fuzzy_result["recommendation"],
            },
        },
    }


def preview_adaptation(session, current_task_id=None):
    current_task = get_task(current_task_id or session.current_task_id)
    progress = get_module_progress(session, current_task["moduleId"])
    fuzzy_result = {
        "knowledgeMastery": progress.aggregate_mastery,
        "systemCognitiveFriction": progress.aggregate_friction,
        "recommendation": session.latest_recommendation,
    }
    return select_next_task(
        session,
        current_task,
        fuzzy_result,
        {
            "moduleId": current_task["moduleId"],
            "outcome": "continue",
            "attemptedTaskCount": progress.attempted_task_count,
            "moduleMastery": progress.aggregate_mastery,
            "moduleFriction": progress.aggregate_friction,
            "minimumAttempts": 6,
            "recentMcqResults": [],
            "recentMcqCorrectCount": 0,
            "masteryThresholdMet": False,
            "nextModuleId": None,
        },
    )
