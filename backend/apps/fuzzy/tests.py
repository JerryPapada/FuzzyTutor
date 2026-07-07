from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APITestCase

from .engines.anfis import predict_mastery
from .engines.controller import focus_state_for, recommendation_for
from .engines.mamdani import infer_cognitive_friction


class MamdaniFrictionTests(SimpleTestCase):
    def test_low_time_low_assistance_complete_task_produces_low_friction(self):
        result = infer_cognitive_friction(
            relative_response_time=0.8,
            assistance_interactions=0,
            completion_ratio=1.0,
            task_type="mcq",
        )

        self.assertLess(result["score"], 30)
        self.assertEqual(result["defuzzification"], "centroid_weighted_average")
        self.assertTrue(result["rules"])

    def test_high_time_high_assistance_incomplete_task_produces_high_friction(self):
        result = infer_cognitive_friction(
            relative_response_time=2.4,
            assistance_interactions=5,
            completion_ratio=0.1,
            task_type="code",
        )

        self.assertGreater(result["score"], 70)

    def test_friction_output_is_clamped(self):
        result = infer_cognitive_friction(
            relative_response_time=50,
            assistance_interactions=50,
            completion_ratio=0,
            task_type="code",
        )

        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)


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


class AdaptationControllerTests(SimpleTestCase):
    def test_recommendation_thresholds_are_stable(self):
        self.assertEqual(focus_state_for(20, 80), "Focused & Steady")
        self.assertEqual(
            recommendation_for(80, 20),
            "increase_or_hold_high_tier",
        )
        self.assertEqual(focus_state_for(60, 35), "Frustrated")
        self.assertEqual(
            recommendation_for(35, 60),
            "reduce_difficulty_and_show_support",
        )
        self.assertEqual(recommendation_for(60, 40), "hold_current_tier")


class FuzzyEvaluationApiTests(APITestCase):
    def test_valid_mcq_payload_returns_stable_response_shape(self):
        response = self.client.post(
            "/api/fuzzy/evaluate/",
            {
                "taskMetricWeight": 55,
                "historicalGradeAverage": 76,
                "relativeResponseTime": 0.9,
                "assistanceInteractions": 0,
                "completionRatio": 1,
                "taskType": "mcq",
                "isCorrect": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("knowledgeMastery", response.data)
        self.assertIn("systemCognitiveFriction", response.data)
        self.assertIn("focusState", response.data)
        self.assertIn("recommendation", response.data)
        self.assertIn("supportMessage", response.data)
        self.assertIn("inputSnapshot", response.data)
        self.assertIn("engineTrace", response.data)

    def test_code_payload_uses_completion_behavior_and_task_type(self):
        response = self.client.post(
            "/api/fuzzy/evaluate/",
            {
                "taskMetricWeight": 75,
                "historicalGradeAverage": 50,
                "relativeResponseTime": 2.0,
                "assistanceInteractions": 4,
                "completionRatio": 0.2,
                "taskType": "code",
                "answerText": "def example(): pass",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["inputSnapshot"]["taskType"], "code")
        self.assertGreater(response.data["systemCognitiveFriction"], 55)

    def test_missing_optional_fields_use_defaults(self):
        response = self.client.post("/api/fuzzy/evaluate/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["inputSnapshot"]["taskMetricWeight"], 50.0)
        self.assertEqual(response.data["inputSnapshot"]["historicalGradeAverage"], 70.0)
        self.assertEqual(response.data["inputSnapshot"]["relativeResponseTime"], 1.0)
        self.assertEqual(response.data["inputSnapshot"]["assistanceInteractions"], 0)
        self.assertEqual(response.data["inputSnapshot"]["completionRatio"], 1.0)
        self.assertEqual(response.data["inputSnapshot"]["taskType"], "mcq")

    def test_invalid_numeric_fields_return_400(self):
        response = self.client.post(
            "/api/fuzzy/evaluate/",
            {
                "taskMetricWeight": 101,
                "completionRatio": 1.5,
                "relativeResponseTime": -1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
