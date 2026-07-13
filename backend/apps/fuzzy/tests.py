import tempfile
from pathlib import Path
from django.core.management import call_command
from django.test import SimpleTestCase
from django.test import TestCase
from apps.learning.models import FuzzyEvaluationLog, LearnerSession
from .engines.anfis import predict_mastery
from .engines.anfis_training import generate_synthetic_training_rows, load_trained_parameters
from .engines.mamdani import infer_cognitive_friction


class AnfisMasteryTests(SimpleTestCase):
    def test_strong_evidence_produces_higher_mastery_than_weak_evidence(self):
        strong = predict_mastery(
            task_weight=75,
            historical_grade=88,
            completion_ratio=1.0,
            task_type="mcq",
            is_correct=True,
        )
        weak = predict_mastery(
            task_weight=75,
            historical_grade=35,
            completion_ratio=0.1,
            task_type="mcq",
            is_correct=False,
        )

        self.assertGreater(strong["score"], weak["score"])
        self.assertGreater(strong["score"], 75)
        self.assertLess(weak["score"], 45)

    def test_mastery_output_is_clamped(self):
        result = predict_mastery(
            task_weight=100,
            historical_grade=100,
            completion_ratio=1.0,
            task_type="mcq",
            is_correct=True,
        )

        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    def test_synthetic_rows_include_target_mastery_label(self):
        rows = generate_synthetic_training_rows(count=10, seed=5)

        self.assertEqual(len(rows), 10)
        self.assertIn("targetMastery", rows[0])
        self.assertGreaterEqual(rows[0]["targetMastery"], 0)
        self.assertLessEqual(rows[0]["targetMastery"], 100)


class MamdaniFrictionTests(SimpleTestCase):
    def test_stalled_incomplete_behavior_has_more_friction_than_steady_completion(self):
        steady = infer_cognitive_friction(0.9, 0, 1.0, "mcq")
        stalled = infer_cognitive_friction(2.3, 6, 0.2, "mcq")

        self.assertLess(steady["score"], stalled["score"])
        self.assertEqual(steady["defuzzification"], "centroid_of_aggregated_output_area")
        self.assertGreater(steady["aggregatedArea"], 0)
        self.assertGreater(stalled["aggregatedArea"], 0)


class AnfisTrainingCommandTests(TestCase):
    def test_seed_command_creates_synthetic_training_logs(self):
        call_command("seed_anfis_training_data", count=12, seed=9, clear_existing=True)

        self.assertEqual(LearnerSession.objects.filter(token__startswith="synthetic-anfis-").count(), 12)
        self.assertEqual(FuzzyEvaluationLog.objects.count(), 12)
        first_log = FuzzyEvaluationLog.objects.select_related("submission").first()
        self.assertTrue(first_log.submission.answer_payload["synthetic"])
        self.assertIn("targetMastery", first_log.submission.answer_payload)

    def test_train_command_writes_parameter_file(self):
        call_command("seed_anfis_training_data", count=40, seed=11, clear_existing=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "anfis_parameters.json"
            call_command(
                "train_anfis",
                epochs=8,
                min_samples=20,
                output=str(output_path),
            )

            self.assertTrue(output_path.exists())
            parameters = load_trained_parameters(output_path)
            self.assertEqual(parameters["modelType"], "trained_anfis")
            self.assertEqual(parameters["metadata"]["sampleCount"], 40)
            self.assertEqual(parameters["metadata"]["trainingSampleCount"], 32)
            self.assertEqual(parameters["metadata"]["validationSampleCount"], 8)
            self.assertIn("holdoutMetrics", parameters["metadata"])
            self.assertIn("secure_prior_mastery", parameters["consequentWeights"])

    def test_evaluate_command_reports_metrics_for_trained_parameters(self):
        call_command("seed_anfis_training_data", count=40, seed=12, clear_existing=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "anfis_parameters.json"
            call_command(
                "train_anfis",
                epochs=8,
                min_samples=20,
                output=str(output_path),
            )
            call_command(
                "evaluate_anfis",
                parameters=str(output_path),
                min_samples=20,
            )
