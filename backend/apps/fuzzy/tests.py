import tempfile
from pathlib import Path
from django.core.management import call_command
from django.test import SimpleTestCase
from django.test import TestCase
from apps.learning.models import FuzzyEvaluationLog, LearnerSession
from apps.learning.adaptation import adaptation_reason, target_difficulty
from .engines.anfis import correctness_signal, predict_mastery
from .engines.anfis_training import generate_synthetic_training_rows, load_trained_parameters
from .engines.controller import focus_state_for, recommendation_for, support_message_for
from .engines.mamdani import infer_cognitive_friction


class AnfisMasteryTests(SimpleTestCase):
    def test_performance_evidence_is_conservative_for_ungraded_code(self):
        self.assertEqual(correctness_signal(None, 0), 40)
        self.assertEqual(correctness_signal(None, 1), 65)
        self.assertEqual(correctness_signal(False, 1), 20)
        self.assertEqual(correctness_signal(True, 0), 100)

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

    def test_returned_rule_trace_reproduces_mastery(self):
        result = predict_mastery(
            task_weight=55,
            historical_grade=72,
            completion_ratio=1.0,
            task_type="mcq",
            is_correct=True,
        )
        total_strength = sum(rule["strength"] for rule in result["rules"])
        traced_score = sum(
            rule["strength"] * rule["output"] for rule in result["rules"]
        ) / total_strength

        self.assertAlmostEqual(traced_score, result["score"], places=2)

    def test_synthetic_rows_include_target_mastery_label(self):
        rows = generate_synthetic_training_rows(count=10, seed=5)

        self.assertEqual(len(rows), 10)
        self.assertIn("targetMastery", rows[0])
        self.assertGreaterEqual(rows[0]["targetMastery"], 0)
        self.assertLessEqual(rows[0]["targetMastery"], 100)

    def test_synthetic_code_rows_never_fabricate_correctness(self):
        rows = generate_synthetic_training_rows(count=180, seed=42)
        code_rows = [row for row in rows if row["taskType"] == "code"]

        self.assertTrue(code_rows)
        self.assertTrue(all(row["isCorrect"] is None for row in code_rows))
        self.assertTrue(
            all(isinstance(row["isCorrect"], bool) for row in rows if row["taskType"] == "mcq")
        )

    def test_operational_inputs_always_activate_an_anfis_rule(self):
        for task_weight in (35, 55, 75):
            for historical_grade in (0, 35, 50, 68, 80, 90, 100):
                for completion_ratio in (0.0, 0.5, 1.0):
                    for task_type in ("mcq", "code"):
                        for is_correct in (None, False, True):
                            with self.subTest(
                                task_weight=task_weight,
                                historical_grade=historical_grade,
                                completion_ratio=completion_ratio,
                                task_type=task_type,
                                is_correct=is_correct,
                            ):
                                result = predict_mastery(
                                    task_weight=task_weight,
                                    historical_grade=historical_grade,
                                    completion_ratio=completion_ratio,
                                    task_type=task_type,
                                    is_correct=is_correct,
                                )
                                self.assertTrue(result["rules"])
                                self.assertGreater(
                                    sum(rule["strength"] for rule in result["rules"]),
                                    0,
                                )

    def test_mixed_evidence_uses_visible_coverage_guard(self):
        result = predict_mastery(
            task_weight=55,
            historical_grade=90,
            completion_ratio=1.0,
            task_type="mcq",
            is_correct=False,
        )

        self.assertTrue(result["coverageGuardUsed"])
        self.assertEqual(
            [rule["rule"] for rule in result["rules"]],
            ["developing_mastery"],
        )


class ControllerPolicyTests(SimpleTestCase):
    def test_recommendation_threshold_matrix(self):
        cases = (
            (75.0, 34.99, "increase_or_hold_high_tier"),
            (74.99, 34.99, "hold_current_tier"),
            (45.0, 54.99, "hold_current_tier"),
            (44.99, 0.0, "reduce_difficulty_and_show_support"),
            (100.0, 55.0, "reduce_difficulty_and_show_support"),
        )
        for mastery, friction, expected in cases:
            with self.subTest(mastery=mastery, friction=friction):
                self.assertEqual(recommendation_for(mastery, friction), expected)

    def test_support_message_combines_focus_and_requested_action(self):
        focus = focus_state_for(30, 80)
        recommendation = recommendation_for(80, 30)

        self.assertEqual(focus, "Needs Support")
        self.assertEqual(recommendation, "increase_or_hold_high_tier")
        self.assertIn("Advance", support_message_for(focus, recommendation))

    def test_difficulty_boundaries_expose_constraints(self):
        advanced = {"difficultyLevel": 3}
        foundation = {"difficultyLevel": 1}

        self.assertEqual(
            target_difficulty(
                advanced,
                {"recommendation": "increase_or_hold_high_tier"},
            ),
            (3, "increase", "High mastery with low friction supports a harder or equivalent task.", "difficulty_ceiling"),
        )
        self.assertEqual(
            target_difficulty(
                foundation,
                {"recommendation": "reduce_difficulty_and_show_support"},
            ),
            (1, "decrease", "High friction or low mastery calls for an easier supported task.", "difficulty_floor"),
        )
        self.assertIn(
            "difficulty ceiling",
            adaptation_reason(
                "increase",
                "hold",
                "difficulty_ceiling",
                "unused",
                "module",
            ),
        )


class MamdaniFrictionTests(SimpleTestCase):
    def test_stalled_incomplete_behavior_has_more_friction_than_steady_completion(self):
        steady = infer_cognitive_friction(0.9, 0, 1.0, "mcq")
        stalled = infer_cognitive_friction(2.3, 6, 0.2, "mcq")

        self.assertLess(steady["score"], stalled["score"])
        self.assertEqual(steady["defuzzification"], "centroid_of_aggregated_output_area")
        self.assertGreater(steady["aggregatedArea"], 0)
        self.assertGreater(stalled["aggregatedArea"], 0)

    def test_three_hint_levels_reach_high_assistance_membership(self):
        no_hints = infer_cognitive_friction(1.0, 0, 1.0, "mcq")
        all_hints = infer_cognitive_friction(1.0, 3, 1.0, "mcq")

        self.assertEqual(all_hints["memberships"]["assistance"]["high"], 1.0)
        self.assertGreater(all_hints["score"], no_hints["score"])

    def test_returned_rule_trace_reproduces_centroid(self):
        result = infer_cognitive_friction(3.0, 3, 1.0, "mcq")

        def triangular_membership(value, left, peak, right):
            if value <= left or value >= right:
                return 0.0
            if value < peak:
                return (value - left) / (peak - left)
            return (right - value) / (right - peak)

        memberships = []
        for index in range(401):
            value = index * 0.25
            memberships.append(
                max(
                    min(
                        rule["strength"],
                        triangular_membership(
                            value,
                            *result["outputSets"][rule["consequent"]]["parameters"],
                        ),
                    )
                    for rule in result["rules"]
                )
            )
        traced_score = sum(
            index * 0.25 * membership
            for index, membership in enumerate(memberships)
        ) / sum(memberships)

        self.assertAlmostEqual(traced_score, result["score"], places=6)
        self.assertAlmostEqual(sum(memberships) * 0.25, result["aggregatedArea"], places=4)

    def test_operational_inputs_always_produce_aggregated_fuzzy_area(self):
        for relative_time in (0.0, 0.5, 1.0, 1.5, 2.5, 5.0):
            for assistance in (0, 1, 2, 3, 6):
                for completion in (0.0, 0.25, 0.5, 0.75, 1.0):
                    for task_type in ("mcq", "code"):
                        with self.subTest(
                            relative_time=relative_time,
                            assistance=assistance,
                            completion=completion,
                            task_type=task_type,
                        ):
                            result = infer_cognitive_friction(
                                relative_time,
                                assistance,
                                completion,
                                task_type,
                            )
                            self.assertTrue(result["rules"])
                            self.assertGreater(result["aggregatedArea"], 0)

    def test_uncovered_mixed_signals_use_visible_mamdani_guard(self):
        result = infer_cognitive_friction(0.5, 3, 1.0, "mcq")

        self.assertTrue(result["coverageGuardUsed"])
        self.assertEqual(result["rules"][0]["rule"], "mixed_signal_coverage")
        self.assertEqual(result["rules"][0]["consequent"], "moderate")
        self.assertGreater(result["aggregatedArea"], 0)


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
                include_synthetic_only=True,
                output=str(output_path),
            )

            self.assertTrue(output_path.exists())
            parameters = load_trained_parameters(output_path)
            self.assertEqual(parameters["modelType"], "trained_anfis")
            self.assertEqual(parameters["metadata"]["sampleCount"], 40)
            self.assertEqual(parameters["metadata"]["trainingSampleCount"], 32)
            self.assertEqual(parameters["metadata"]["validationSampleCount"], 8)
            self.assertEqual(parameters["metadata"]["trainingMode"], "synthetic_only")
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
                include_synthetic_only=True,
                output=str(output_path),
            )
            call_command(
                "evaluate_anfis",
                parameters=str(output_path),
                min_samples=20,
                include_synthetic_only=True,
            )
