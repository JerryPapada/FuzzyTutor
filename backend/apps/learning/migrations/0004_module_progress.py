from django.db import migrations, models
import django.db.models.deletion


LEGACY_TASK_IDS = {
    1: {"lists-mcq-001", "lists-code-001", "lists-code-002"},
    2: {"arrays-mcq-001", "arrays-code-001", "arrays-mcq-002"},
    3: {"dicts-mcq-001", "dicts-code-001", "dicts-code-002"},
    4: {"classes-mcq-001", "classes-code-001", "classes-code-002"},
    5: {"inheritance-mcq-001", "inheritance-mcq-002", "inheritance-code-001"},
    6: {"exceptions-mcq-001", "exceptions-code-001", "exceptions-code-002"},
    7: {"control-mcq-001", "control-code-001", "control-code-002"},
}


def backfill_module_progress(apps, schema_editor):
    LearnerSession = apps.get_model("learning", "LearnerSession")
    ModuleProgress = apps.get_model("learning", "ModuleProgress")
    FuzzyEvaluationLog = apps.get_model("learning", "FuzzyEvaluationLog")

    for session in LearnerSession.objects.all().iterator():
        submissions = list(session.submissions.order_by("created_at", "id"))
        logs = {
            log.submission_id: log
            for log in FuzzyEvaluationLog.objects.filter(session_id=session.id)
        }
        snapshots = {
            module_id: {
                "mastery": 50.0,
                "friction": 25.0,
                "count": 0,
                "task_ids": set(),
                "latest_submission": None,
            }
            for module_id in range(1, 8)
        }

        for submission in submissions:
            snapshot = snapshots[submission.module_id]
            submission.module_mastery_before = round(snapshot["mastery"], 2)
            submission.module_friction_before = round(snapshot["friction"], 2)
            submission.save(
                update_fields=["module_mastery_before", "module_friction_before"]
            )
            snapshot["count"] += 1
            snapshot["task_ids"].add(submission.task_id)
            snapshot["latest_submission"] = submission
            log = logs.get(submission.id)
            if log is not None:
                snapshot["mastery"] = round(
                    (snapshot["mastery"] * 0.65)
                    + (log.knowledge_mastery * 0.35),
                    2,
                )
                snapshot["friction"] = round(
                    (snapshot["friction"] * 0.65)
                    + (log.system_cognitive_friction * 0.35),
                    2,
                )

        for module_id, snapshot in snapshots.items():
            legacy_complete = LEGACY_TASK_IDS[module_id].issubset(snapshot["task_ids"])
            if legacy_complete:
                status = "legacy_completed"
                exit_reason = "legacy_completed"
                completed_at = snapshot["latest_submission"].created_at
                snapshot["latest_submission"].module_exit_outcome = "legacy_completed"
                snapshot["latest_submission"].save(
                    update_fields=["module_exit_outcome"]
                )
            elif module_id == session.current_module_id:
                status = "active"
                exit_reason = ""
                completed_at = None
            else:
                status = "not_started"
                exit_reason = ""
                completed_at = None

            ModuleProgress.objects.create(
                session_id=session.id,
                module_id=module_id,
                aggregate_mastery=snapshot["mastery"],
                aggregate_friction=snapshot["friction"],
                attempted_task_count=snapshot["count"],
                status=status,
                exit_reason=exit_reason,
                completed_at=completed_at,
            )


def remove_backfilled_progress(apps, schema_editor):
    apps.get_model("learning", "ModuleProgress").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0003_hint_events"),
    ]

    operations = [
        migrations.AddField(
            model_name="tasksubmission",
            name="module_exit_outcome",
            field=models.CharField(default="continue", max_length=40),
        ),
        migrations.AddField(
            model_name="tasksubmission",
            name="module_friction_before",
            field=models.FloatField(default=25.0),
        ),
        migrations.AddField(
            model_name="tasksubmission",
            name="module_mastery_before",
            field=models.FloatField(default=50.0),
        ),
        migrations.CreateModel(
            name="ModuleProgress",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("module_id", models.PositiveSmallIntegerField()),
                ("aggregate_mastery", models.FloatField(default=50.0)),
                ("aggregate_friction", models.FloatField(default=25.0)),
                ("attempted_task_count", models.PositiveSmallIntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("not_started", "Not started"),
                            ("active", "Active"),
                            ("mastered", "Mastered"),
                            ("completed_bank", "Completed task bank"),
                            ("legacy_completed", "Legacy completed"),
                        ],
                        default="not_started",
                        max_length=24,
                    ),
                ),
                ("exit_reason", models.CharField(blank=True, max_length=40)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="module_progress",
                        to="learning.learnersession",
                    ),
                ),
            ],
            options={
                "ordering": ["module_id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("session", "module_id"),
                        name="unique_session_module_progress",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("module_id__gte", 1), ("module_id__lte", 7)),
                        name="module_progress_id_between_one_and_seven",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("aggregate_mastery__gte", 0.0),
                            ("aggregate_mastery__lte", 100.0),
                        ),
                        name="module_progress_mastery_between_zero_and_one_hundred",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("aggregate_friction__gte", 0.0),
                            ("aggregate_friction__lte", 100.0),
                        ),
                        name="module_progress_friction_between_zero_and_one_hundred",
                    ),
                ],
            },
        ),
        migrations.RunPython(
            backfill_module_progress,
            remove_backfilled_progress,
        ),
    ]
