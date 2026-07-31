from django.core.management.base import BaseCommand, CommandError

from apps.fuzzy.engines.anfis import correctness_signal, memberships, rule_strengths
from apps.fuzzy.engines.anfis_training import (
    feature_vector,
    predict_sample_mastery,
    regression_metrics,
    save_trained_parameters,
    split_training_samples,
    synthetic_target_mastery,
    train_consequent_parameters,
)
from apps.learning.models import FuzzyEvaluationLog

def target_for(log, survey):
    answer_payload = log.submission.answer_payload
    stored_target = answer_payload.get("targetMastery")
    is_synthetic_bootstrap = (
        log.session.token.startswith("synthetic-anfis-")
        and answer_payload.get("synthetic") is True
    )
    if is_synthetic_bootstrap and stored_target is not None:
        return float(stored_target)
    row = {
        "historicalGradeAverage": log.input_snapshot.get("historicalGradeAverage", 70.0),
        "relativeResponseTime": log.submission.relative_response_time,
        "completionRatio": log.submission.completion_ratio,
        "isCorrect": log.submission.is_correct,
        "confidenceScore": survey.confidence_score if survey else 3,
        "perceivedDifficulty": survey.perceived_difficulty if survey else 3,
    }
    return synthetic_target_mastery(row)


def sample_from_log(log):
    submission = log.submission
    survey = submission.micro_surveys.order_by("-created_at").first()
    historical_grade = log.input_snapshot.get("historicalGradeAverage", 70.0)
    correctness_score = correctness_signal(submission.is_correct, submission.completion_ratio)
    membership_values = memberships(
        submission.task_metric_weight,
        historical_grade,
        submission.completion_ratio,
        correctness_score,
    )
    strengths, _coverage_guard_used = rule_strengths(membership_values)
    return {
        "features": feature_vector(
            submission.task_metric_weight,
            historical_grade,
            submission.completion_ratio,
            correctness_score,
            submission.task_type,
        ),
        "ruleStrengths": strengths,
        "targetMastery": target_for(log, survey),
    }


class Command(BaseCommand):
    help = "Train ANFIS consequent parameters from stored learner telemetry."

    def add_arguments(self, parser):
        parser.add_argument("--epochs", type=int, default=650)
        parser.add_argument("--learning-rate", type=float, default=0.00002)
        parser.add_argument("--min-samples", type=int, default=30)
        parser.add_argument("--output", type=str, default=None)
        parser.add_argument("--validation-fraction", type=float, default=0.2)
        parser.add_argument("--split-seed", type=int, default=42)
        source_group = parser.add_mutually_exclusive_group()
        source_group.add_argument(
            "--include-real-only",
            action="store_true",
            help="Ignore synthetic bootstrap sessions and train only from non-synthetic logs.",
        )
        source_group.add_argument(
            "--include-synthetic-only",
            action="store_true",
            help="Train only from deterministic synthetic bootstrap sessions.",
        )

    def handle(self, *args, **options):
        if not 0.0 < options["validation_fraction"] < 1.0:
            raise CommandError("--validation-fraction must be greater than 0 and less than 1.")
        logs = FuzzyEvaluationLog.objects.select_related("submission", "session").all()
        if options["include_real_only"]:
            logs = logs.exclude(session__token__startswith="synthetic-anfis-")
            training_source = "stored non-synthetic learner telemetry"
            training_mode = "real_only"
        elif options["include_synthetic_only"]:
            logs = logs.filter(session__token__startswith="synthetic-anfis-")
            training_source = "stored deterministic synthetic bootstrap telemetry"
            training_mode = "synthetic_only"
        else:
            training_source = "stored learner telemetry with synthetic bootstrap rows allowed"
            training_mode = "mixed"

        samples = [sample_from_log(log) for log in logs]
        if len(samples) < options["min_samples"]:
            raise CommandError(
                f"Need at least {options['min_samples']} samples to train; found {len(samples)}."
            )

        training_samples, validation_samples = split_training_samples(
            samples,
            validation_fraction=options["validation_fraction"],
            seed=options["split_seed"],
        )
        weights, losses = train_consequent_parameters(
            training_samples,
            epochs=options["epochs"],
            learning_rate=options["learning_rate"],
        )
        holdout_metrics = regression_metrics(
            [sample["targetMastery"] for sample in validation_samples],
            [predict_sample_mastery(sample, weights) for sample in validation_samples],
        )
        parameters = {
            "modelType": "trained_anfis",
            "consequentWeights": weights,
            "metadata": {
                "sampleCount": len(samples),
                "trainingSampleCount": len(training_samples),
                "validationSampleCount": len(validation_samples),
                "validationFraction": options["validation_fraction"],
                "splitSeed": options["split_seed"],
                "epochs": options["epochs"],
                "learningRate": options["learning_rate"],
                "initialLoss": round(losses[0], 4),
                "finalLoss": round(losses[-1], 4),
                "trainingSource": training_source,
                "trainingMode": training_mode,
                "holdoutMetrics": {
                    key: round(value, 4) if isinstance(value, float) else value
                    for key, value in holdout_metrics.items()
                },
            },
        }
        output_path = save_trained_parameters(parameters, options["output"])
        self.stdout.write(
            self.style.SUCCESS(
                "Trained ANFIS parameters with "
                f"{len(training_samples)} training and {len(validation_samples)} holdout samples. "
                f"Loss {losses[0]:.4f} -> {losses[-1]:.4f}; "
                f"holdout RMSE {holdout_metrics['rmse']:.4f}. "
                f"Saved to {output_path}."
            )
        )
