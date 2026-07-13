import uuid

from django.core.management.base import BaseCommand

from apps.fuzzy.engines import evaluate_learning_state
from apps.fuzzy.engines.anfis_training import generate_synthetic_training_rows
from apps.learning.catalog import TASK_BANK
from apps.learning.models import FuzzyEvaluationLog, LearnerSession, MicroSurveyResponse, TaskSubmission


def _task_for_row(row, index):
    candidates = [
        task
        for task in TASK_BANK
        if task["taskMetricWeight"] == row["taskMetricWeight"] and task["type"] == row["taskType"]
    ]
    if not candidates:
        candidates = [task for task in TASK_BANK if task["taskMetricWeight"] == row["taskMetricWeight"]]
    if not candidates:
        candidates = TASK_BANK
    return candidates[index % len(candidates)]


class Command(BaseCommand):
    help = "Seed synthetic learner telemetry for ANFIS bootstrap training."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=180)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Delete previous synthetic sessions before seeding new data.",
        )

    def handle(self, *args, **options):
        if options["clear_existing"]:
            LearnerSession.objects.filter(token__startswith="synthetic-anfis-").delete()

        rows = generate_synthetic_training_rows(
            count=options["count"],
            seed=options["seed"],
        )
        created = 0
        for index, row in enumerate(rows):
            task = _task_for_row(row, index)
            session = LearnerSession.objects.create(
                token=f"synthetic-anfis-{uuid.uuid4().hex}",
                current_module_id=task["moduleId"],
                current_task_id=task["id"],
                aggregate_mastery=row["historicalGradeAverage"],
                aggregate_friction=25.0,
                completed_task_count=1,
            )
            elapsed = row["relativeResponseTime"] * task["baselineTimeSeconds"]
            fuzzy_inputs = {
                "taskMetricWeight": row["taskMetricWeight"],
                "historicalGradeAverage": row["historicalGradeAverage"],
                "relativeResponseTime": row["relativeResponseTime"],
                "assistanceInteractions": row["assistanceInteractions"],
                "completionRatio": row["completionRatio"],
                "taskType": row["taskType"],
                "isCorrect": row["isCorrect"],
            }
            fuzzy_result = evaluate_learning_state(fuzzy_inputs)
            submission = TaskSubmission.objects.create(
                session=session,
                task_id=task["id"],
                module_id=task["moduleId"],
                task_type=task["type"],
                difficulty=task["difficulty"],
                difficulty_level=task["difficultyLevel"],
                task_metric_weight=task["taskMetricWeight"],
                baseline_time_seconds=task["baselineTimeSeconds"],
                elapsed_time_seconds=elapsed,
                relative_response_time=row["relativeResponseTime"],
                assistance_interactions=row["assistanceInteractions"],
                completion_ratio=row["completionRatio"],
                is_correct=row["isCorrect"],
                answer_payload={
                    "synthetic": True,
                    "syntheticProfile": row["syntheticProfile"],
                    "targetMastery": row["targetMastery"],
                },
            )
            FuzzyEvaluationLog.objects.create(
                session=session,
                submission=submission,
                input_snapshot=fuzzy_result["inputSnapshot"],
                engine_trace=fuzzy_result["engineTrace"],
                knowledge_mastery=fuzzy_result["knowledgeMastery"],
                system_cognitive_friction=fuzzy_result["systemCognitiveFriction"],
                focus_state=fuzzy_result["focusState"],
                recommendation=fuzzy_result["recommendation"],
                support_message=fuzzy_result["supportMessage"],
            )
            MicroSurveyResponse.objects.create(
                session=session,
                submission=submission,
                satisfaction_score=max(1, min(5, row["confidenceScore"])),
                perceived_difficulty=max(1, min(5, row["perceivedDifficulty"])),
                confidence_score=max(1, min(5, row["confidenceScore"])),
                milestone_task_count=0,
                comment="Synthetic bootstrap ANFIS training row.",
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {created} synthetic ANFIS training rows.")
        )
