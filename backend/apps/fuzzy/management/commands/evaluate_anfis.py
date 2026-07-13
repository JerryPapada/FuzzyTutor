from django.core.management.base import BaseCommand, CommandError

from apps.fuzzy.engines.anfis_training import (
    DEFAULT_CONSEQUENT_WEIGHTS,
    load_trained_parameters,
    predict_sample_mastery,
    regression_metrics,
    split_training_samples,
)
from apps.fuzzy.management.commands.train_anfis import sample_from_log
from apps.learning.models import FuzzyEvaluationLog


def format_metrics(label, metrics):
    return (
        f"{label}: samples={metrics['count']} "
        f"MAE={metrics['mae']:.3f} "
        f"RMSE={metrics['rmse']:.3f} "
        f"R2={metrics['r2']:.3f}"
    )


class Command(BaseCommand):
    help = "Evaluate trained ANFIS parameters against stored learner telemetry."

    def add_arguments(self, parser):
        parser.add_argument("--parameters", type=str, default=None)
        parser.add_argument("--min-samples", type=int, default=1)
        parser.add_argument(
            "--include-real-only",
            action="store_true",
            help="Ignore synthetic bootstrap sessions and evaluate only non-synthetic logs.",
        )

    def handle(self, *args, **options):
        parameters = load_trained_parameters(options["parameters"])
        if not parameters:
            raise CommandError(
                "No trained ANFIS parameter file found. Run train_anfis first or pass --parameters."
            )

        logs = FuzzyEvaluationLog.objects.select_related("submission", "session").all()
        if options["include_real_only"]:
            logs = logs.exclude(session__token__startswith="synthetic-anfis-")

        samples = [sample_from_log(log) for log in logs]
        if len(samples) < options["min_samples"]:
            raise CommandError(
                f"Need at least {options['min_samples']} samples to evaluate; found {len(samples)}."
            )

        metadata = parameters.get("metadata") or {}
        _training_samples, evaluation_samples = split_training_samples(
            samples,
            validation_fraction=metadata.get("validationFraction", 0.2),
            seed=metadata.get("splitSeed", 42),
        )
        if not evaluation_samples:
            evaluation_samples = samples

        targets = [sample["targetMastery"] for sample in evaluation_samples]
        trained_predictions = [
            predict_sample_mastery(sample, parameters["consequentWeights"])
            for sample in evaluation_samples
        ]
        baseline_predictions = [
            predict_sample_mastery(sample, DEFAULT_CONSEQUENT_WEIGHTS)
            for sample in evaluation_samples
        ]

        trained_metrics = regression_metrics(targets, trained_predictions)
        baseline_metrics = regression_metrics(targets, baseline_predictions)
        improvement = baseline_metrics["rmse"] - trained_metrics["rmse"]

        self.stdout.write(format_metrics("Default ANFIS baseline", baseline_metrics))
        self.stdout.write(format_metrics("Trained ANFIS", trained_metrics))
        self.stdout.write(f"RMSE improvement: {improvement:.3f}")
        if metadata:
            self.stdout.write(
                "Training metadata: "
                f"samples={metadata.get('sampleCount')} "
                f"epochs={metadata.get('epochs')} "
                f"loss={metadata.get('initialLoss')}->{metadata.get('finalLoss')}"
            )
