from django.db import migrations, models


def backfill_survey_milestones(apps, schema_editor):
    LearnerSession = apps.get_model("learning", "LearnerSession")
    for session in LearnerSession.objects.all().iterator():
        surveys = session.micro_surveys.order_by("created_at", "id")
        for index, survey in enumerate(surveys, start=1):
            milestone = 0 if session.token.startswith("synthetic-anfis-") else index * 5
            survey.milestone_task_count = milestone
            survey.save(update_fields=["milestone_task_count"])


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="microsurveyresponse",
            name="milestone_task_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(backfill_survey_milestones, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="microsurveyresponse",
            constraint=models.UniqueConstraint(
                fields=("session", "milestone_task_count"),
                name="unique_session_survey_milestone",
            ),
        ),
    ]
