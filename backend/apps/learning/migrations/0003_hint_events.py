from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0002_micro_survey_milestone"),
    ]

    operations = [
        migrations.AddField(
            model_name="tasksubmission",
            name="max_hint_level",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddConstraint(
            model_name="tasksubmission",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("max_hint_level__gte", 0),
                    ("max_hint_level__lte", 3),
                ),
                name="submission_hint_level_between_zero_and_three",
            ),
        ),
        migrations.CreateModel(
            name="HintEvent",
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
                ("task_id", models.CharField(max_length=80)),
                ("level", models.PositiveSmallIntegerField()),
                ("kind", models.CharField(max_length=30)),
                ("label", models.CharField(max_length=50)),
                ("text", models.TextField()),
                ("elapsed_time_seconds", models.FloatField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hint_events",
                        to="learning.learnersession",
                    ),
                ),
            ],
            options={
                "ordering": ["level", "created_at"],
                "indexes": [
                    models.Index(
                        fields=["session", "task_id"],
                        name="learning_hi_session_cdf850_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("session", "task_id", "level"),
                        name="unique_session_task_hint_level",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("level__gte", 1), ("level__lte", 3)),
                        name="hint_level_between_one_and_three",
                    ),
                ],
            },
        ),
    ]
