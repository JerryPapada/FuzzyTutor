import uuid
from django.db import models

# session token gen
def generate_session_token():
    return uuid.uuid4().hex

# Session model to track progress
class LearnerSession(models.Model):
    token = models.CharField(max_length=64, unique=True, default=generate_session_token)
    current_module_id = models.PositiveIntegerField(default=1)
    current_task_id = models.CharField(max_length=80, blank=True)
    aggregate_mastery = models.FloatField(default=70.0)
    aggregate_friction = models.FloatField(default=25.0)
    completed_task_count = models.PositiveIntegerField(default=0)
    latest_recommendation = models.CharField(max_length=80, default="hold_current_tier")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.token

    def pending_survey_milestone(self):
        """Return the oldest unanswered five-task survey milestone."""
        answered = set(
            self.micro_surveys.exclude(milestone_task_count=0).values_list(
                "milestone_task_count", flat=True
            )
        )
        for milestone in range(5, self.completed_task_count + 1, 5):
            if milestone not in answered:
                return milestone
        return None


class ModuleProgress(models.Model):
    STATUS_NOT_STARTED = "not_started"
    STATUS_ACTIVE = "active"
    STATUS_MASTERED = "mastered"
    STATUS_COMPLETED_BANK = "completed_bank"
    STATUS_LEGACY_COMPLETED = "legacy_completed"
    STATUS_CHOICES = (
        (STATUS_NOT_STARTED, "Not started"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_MASTERED, "Mastered"),
        (STATUS_COMPLETED_BANK, "Completed task bank"),
        (STATUS_LEGACY_COMPLETED, "Legacy completed"),
    )
    TERMINAL_STATUSES = {
        STATUS_MASTERED,
        STATUS_COMPLETED_BANK,
        STATUS_LEGACY_COMPLETED,
    }

    session = models.ForeignKey(
        LearnerSession,
        related_name="module_progress",
        on_delete=models.CASCADE,
    )
    module_id = models.PositiveSmallIntegerField()
    aggregate_mastery = models.FloatField(default=50.0)
    aggregate_friction = models.FloatField(default=25.0)
    attempted_task_count = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(
        max_length=24,
        choices=STATUS_CHOICES,
        default=STATUS_NOT_STARTED,
    )
    exit_reason = models.CharField(max_length=40, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["module_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "module_id"],
                name="unique_session_module_progress",
            ),
            models.CheckConstraint(
                condition=models.Q(module_id__gte=1, module_id__lte=7),
                name="module_progress_id_between_one_and_seven",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    aggregate_mastery__gte=0.0,
                    aggregate_mastery__lte=100.0,
                ),
                name="module_progress_mastery_between_zero_and_one_hundred",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    aggregate_friction__gte=0.0,
                    aggregate_friction__lte=100.0,
                ),
                name="module_progress_friction_between_zero_and_one_hundred",
            ),
        ]


# Task submission model to track performance
class TaskSubmission(models.Model):
    session = models.ForeignKey(
        LearnerSession,
        related_name="submissions",
        on_delete=models.CASCADE,
    )
    task_id = models.CharField(max_length=80)
    module_id = models.PositiveIntegerField()
    task_type = models.CharField(max_length=20)
    difficulty = models.CharField(max_length=20)
    difficulty_level = models.PositiveSmallIntegerField()
    task_metric_weight = models.FloatField()
    baseline_time_seconds = models.PositiveIntegerField()
    elapsed_time_seconds = models.FloatField()
    relative_response_time = models.FloatField()
    assistance_interactions = models.PositiveIntegerField(default=0)
    max_hint_level = models.PositiveSmallIntegerField(default=0)
    module_mastery_before = models.FloatField(default=50.0)
    module_friction_before = models.FloatField(default=25.0)
    module_exit_outcome = models.CharField(max_length=40, default="continue")
    completion_ratio = models.FloatField(default=1.0)
    is_correct = models.BooleanField(null=True, blank=True)
    answer_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session", "created_at"]),
            models.Index(fields=["task_id"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_hint_level__gte=0, max_hint_level__lte=3),
                name="submission_hint_level_between_zero_and_three",
            ),
        ]


# Immutable record of each progressive hint revealed during the current task.
class HintEvent(models.Model):
    session = models.ForeignKey(
        LearnerSession,
        related_name="hint_events",
        on_delete=models.CASCADE,
    )
    task_id = models.CharField(max_length=80)
    level = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=30)
    label = models.CharField(max_length=50)
    text = models.TextField()
    elapsed_time_seconds = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["level", "created_at"]
        indexes = [
            models.Index(fields=["session", "task_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "task_id", "level"],
                name="unique_session_task_hint_level",
            ),
            models.CheckConstraint(
                condition=models.Q(level__gte=1, level__lte=3),
                name="hint_level_between_one_and_three",
            ),
        ]


# Fuzzy evaluation log model to store fuzzy engine results
class FuzzyEvaluationLog(models.Model):
    session = models.ForeignKey(
        LearnerSession,
        related_name="fuzzy_logs",
        on_delete=models.CASCADE,
    )
    submission = models.OneToOneField(
        TaskSubmission,
        related_name="fuzzy_log",
        on_delete=models.CASCADE,
    )
    input_snapshot = models.JSONField(default=dict)
    engine_trace = models.JSONField(default=dict)
    knowledge_mastery = models.FloatField()
    system_cognitive_friction = models.FloatField()
    focus_state = models.CharField(max_length=80)
    recommendation = models.CharField(max_length=80)
    support_message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session", "created_at"]),
            models.Index(fields=["recommendation"]),
        ]

# Micro-survey response model to capture learner feedback
class MicroSurveyResponse(models.Model):
    session = models.ForeignKey(
        LearnerSession,
        related_name="micro_surveys",
        on_delete=models.CASCADE,
    )
    submission = models.ForeignKey(
        TaskSubmission,
        related_name="micro_surveys",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    satisfaction_score = models.PositiveSmallIntegerField()
    perceived_difficulty = models.PositiveSmallIntegerField()
    confidence_score = models.PositiveSmallIntegerField()
    milestone_task_count = models.PositiveIntegerField(default=0)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "milestone_task_count"],
                name="unique_session_survey_milestone",
            )
        ]
