from django.utils import timezone

from .catalog import CURRICULUM_MODULES, tasks_for_module
from .models import ModuleProgress


MINIMUM_MASTERY_ATTEMPTS = 6
MODULE_MASTERY_THRESHOLD = 75.0
MODULE_FRICTION_THRESHOLD = 40.0
RECENT_MCQ_WINDOW = 3
RECENT_MCQ_CORRECT_REQUIRED = 2


def initialize_module_progress(session, active_module_id):
    ModuleProgress.objects.bulk_create(
        [
            ModuleProgress(
                session=session,
                module_id=module["id"],
                status=(
                    ModuleProgress.STATUS_ACTIVE
                    if module["id"] == active_module_id
                    else ModuleProgress.STATUS_NOT_STARTED
                ),
            )
            for module in CURRICULUM_MODULES
        ]
    )


def ensure_module_progress(session):
    existing_ids = set(
        session.module_progress.values_list("module_id", flat=True)
    )
    missing = [
        ModuleProgress(
            session=session,
            module_id=module["id"],
            status=(
                ModuleProgress.STATUS_ACTIVE
                if module["id"] == session.current_module_id
                else ModuleProgress.STATUS_NOT_STARTED
            ),
        )
        for module in CURRICULUM_MODULES
        if module["id"] not in existing_ids
    ]
    if missing:
        ModuleProgress.objects.bulk_create(missing)


def get_module_progress(session, module_id, for_update=False):
    ensure_module_progress(session)
    queryset = session.module_progress
    if for_update:
        queryset = queryset.select_for_update()
    return queryset.get(module_id=module_id)


def module_progress_payload(progress):
    return {
        "moduleId": progress.module_id,
        "moduleMastery": round(progress.aggregate_mastery, 2),
        "moduleFriction": round(progress.aggregate_friction, 2),
        "attemptedTaskCount": progress.attempted_task_count,
        "status": progress.status,
        "exitReason": progress.exit_reason or None,
        "terminal": progress.status in ModuleProgress.TERMINAL_STATUSES,
        "completedAt": (
            progress.completed_at.isoformat()
            if progress.completed_at is not None
            else None
        ),
    }


def session_module_progress_payload(session):
    ensure_module_progress(session)
    return [
        module_progress_payload(progress)
        for progress in session.module_progress.order_by("module_id")
    ]


def curriculum_complete(session):
    ensure_module_progress(session)
    terminal_count = session.module_progress.filter(
        status__in=ModuleProgress.TERMINAL_STATUSES
    ).count()
    return terminal_count == len(CURRICULUM_MODULES)


def activate_module(session, module_id):
    progress = get_module_progress(session, module_id)
    if progress.status not in ModuleProgress.TERMINAL_STATUSES:
        progress.status = ModuleProgress.STATUS_ACTIVE
        progress.save(update_fields=["status", "updated_at"])
    return progress


def next_unfinished_module_id(session, current_module_id):
    ensure_module_progress(session)
    module_ids = [module["id"] for module in CURRICULUM_MODULES]
    current_position = module_ids.index(current_module_id)
    ordered_ids = module_ids[current_position + 1 :] + module_ids[:current_position]
    statuses = {
        progress.module_id: progress.status
        for progress in session.module_progress.all()
    }
    return next(
        (
            module_id
            for module_id in ordered_ids
            if statuses[module_id] not in ModuleProgress.TERMINAL_STATUSES
        ),
        None,
    )


def update_module_progress(progress, fuzzy_result):
    progress.attempted_task_count += 1
    progress.aggregate_mastery = round(
        (progress.aggregate_mastery * 0.65)
        + (fuzzy_result["knowledgeMastery"] * 0.35),
        2,
    )
    progress.aggregate_friction = round(
        (progress.aggregate_friction * 0.65)
        + (fuzzy_result["systemCognitiveFriction"] * 0.35),
        2,
    )


def evaluate_module_exit(session, progress):
    recent_mcq_results = list(
        session.submissions.filter(
            module_id=progress.module_id,
            task_type="mcq",
        )
        .order_by("-created_at", "-id")
        .values_list("is_correct", flat=True)[:RECENT_MCQ_WINDOW]
    )
    recent_correct = sum(result is True for result in recent_mcq_results)
    enough_mcq_evidence = len(recent_mcq_results) == RECENT_MCQ_WINDOW
    mastery_threshold_met = (
        progress.attempted_task_count >= MINIMUM_MASTERY_ATTEMPTS
        and progress.aggregate_mastery >= MODULE_MASTERY_THRESHOLD
        and progress.aggregate_friction < MODULE_FRICTION_THRESHOLD
        and enough_mcq_evidence
        and recent_correct >= RECENT_MCQ_CORRECT_REQUIRED
    )

    if mastery_threshold_met:
        outcome = "mastery_exit"
        progress.status = ModuleProgress.STATUS_MASTERED
        progress.exit_reason = outcome
        progress.completed_at = timezone.now()
    elif progress.attempted_task_count >= len(tasks_for_module(progress.module_id)):
        outcome = "bank_exhausted"
        progress.status = ModuleProgress.STATUS_COMPLETED_BANK
        progress.exit_reason = outcome
        progress.completed_at = timezone.now()
    else:
        outcome = "continue"
        progress.status = ModuleProgress.STATUS_ACTIVE

    progress.save(
        update_fields=[
            "attempted_task_count",
            "aggregate_mastery",
            "aggregate_friction",
            "status",
            "exit_reason",
            "completed_at",
            "updated_at",
        ]
    )
    return {
        "moduleId": progress.module_id,
        "outcome": outcome,
        "attemptedTaskCount": progress.attempted_task_count,
        "moduleMastery": round(progress.aggregate_mastery, 2),
        "moduleFriction": round(progress.aggregate_friction, 2),
        "minimumAttempts": MINIMUM_MASTERY_ATTEMPTS,
        "recentMcqResults": recent_mcq_results,
        "recentMcqCorrectCount": recent_correct,
        "masteryThresholdMet": mastery_threshold_met,
        "nextModuleId": None,
    }
