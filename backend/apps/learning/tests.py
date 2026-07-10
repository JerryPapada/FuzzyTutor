from types import SimpleNamespace
from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APITestCase
from .adaptation import select_next_task
from .catalog import get_task
from .models import FuzzyEvaluationLog, MicroSurveyResponse, TaskSubmission

## Test cases for the learning app
class LearningApiTests(APITestCase):
    def _create_session(self):
        response = self.client.post("/api/learning/sessions/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data["sessionToken"]

    def _submit(self, session_token, task_id="arrays-mcq-001", elapsed=45, is_correct=True):
        return self.client.post(
            "/api/learning/submissions/",
            {
                "sessionToken": session_token,
                "taskId": task_id,
                "elapsedTimeSeconds": elapsed,
                "assistanceInteractions": 0,
                "completionRatio": 1.0,
                "isCorrect": is_correct,
                "selectedChoice": get_task(task_id).get("correctChoice", ""),
            },
            format="json",
        )

    def test_session_creation_returns_token_and_default_state(self):
        response = self.client.post("/api/learning/sessions/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("sessionToken", response.data)
        self.assertEqual(response.data["aggregateMastery"], 70.0)
        self.assertEqual(response.data["completedTaskCount"], 0)
        self.assertIn("currentTask", response.data)

    def test_task_list_includes_difficulty_and_adaptation_metadata(self):
        response = self.client.get("/api/learning/tasks/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first_task = response.data["tasks"][0]
        self.assertIn("difficultyLevel", first_task)
        self.assertIn("taskMetricWeight", first_task)
        self.assertIn("estimatedCognitiveLoad", first_task)
        self.assertIn("adaptationSignals", first_task)

    def test_submission_creates_submission_and_fuzzy_log_records(self):
        session_token = self._create_session()
        response = self._submit(session_token)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TaskSubmission.objects.count(), 1)
        self.assertEqual(FuzzyEvaluationLog.objects.count(), 1)
        self.assertIn("knowledgeMastery", response.data)
        self.assertIn("systemCognitiveFriction", response.data)

    def test_submission_response_includes_next_task_adaptation_and_survey_state(self):
        session_token = self._create_session()
        response = self._submit(session_token)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("nextTask", response.data)
        self.assertIn("adaptation", response.data)
        self.assertIn("surveyDue", response.data)
        self.assertIn("reason", response.data["adaptation"])

    def test_every_fifth_submission_marks_survey_due(self):
        session_token = self._create_session()

        response = None
        for _index in range(5):
            response = self._submit(session_token)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["surveyDue"])
        self.assertEqual(response.data["session"]["completedTaskCount"], 5)

    def test_micro_survey_endpoint_stores_model_useful_feedback(self):
        session_token = self._create_session()
        self._submit(session_token)

        response = self.client.post(
            "/api/learning/micro-surveys/",
            {
                "sessionToken": session_token,
                "satisfactionScore": 4,
                "perceivedDifficulty": 3,
                "confidenceScore": 4,
                "comment": "Useful hint pacing.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MicroSurveyResponse.objects.count(), 1)
        survey = MicroSurveyResponse.objects.first()
        self.assertEqual(survey.satisfaction_score, 4)
        self.assertIsNotNone(survey.submission)

    def test_training_data_export_returns_model_rows(self):
        session_token = self._create_session()
        self._submit(session_token)
        self.client.post(
            "/api/learning/micro-surveys/",
            {
                "sessionToken": session_token,
                "satisfactionScore": 5,
                "perceivedDifficulty": 2,
                "confidenceScore": 5,
            },
            format="json",
        )

        response = self.client.get("/api/learning/export/training-data/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        row = response.data["rows"][0]
        self.assertIn("taskMetricWeight", row)
        self.assertIn("relativeResponseTime", row)
        self.assertIn("knowledgeMastery", row)
        self.assertEqual(row["satisfactionScore"], 5)


class AdaptationServiceTests(SimpleTestCase):
    def _session(self):
        return SimpleNamespace(
            current_module_id=2,
            current_task_id="arrays-mcq-001",
            aggregate_mastery=70,
            aggregate_friction=25,
            latest_recommendation="hold_current_tier",
        )

    def test_high_mastery_low_friction_selects_same_or_harder_task(self):
        current_task = get_task("arrays-mcq-001")
        result = select_next_task(
            self._session(),
            current_task,
            {
                "knowledgeMastery": 88,
                "systemCognitiveFriction": 15,
                "recommendation": "increase_or_hold_high_tier",
            },
        )

        self.assertEqual(result["adaptation"]["direction"], "increase")
        self.assertGreaterEqual(result["nextTask"]["difficultyLevel"], current_task["difficultyLevel"])
        self.assertEqual(result["nextTask"]["moduleId"], current_task["moduleId"])

    def test_low_mastery_or_high_friction_selects_easier_task(self):
        current_task = get_task("arrays-mcq-002")
        result = select_next_task(
            self._session(),
            current_task,
            {
                "knowledgeMastery": 35,
                "systemCognitiveFriction": 70,
                "recommendation": "reduce_difficulty_and_show_support",
            },
        )

        self.assertEqual(result["adaptation"]["direction"], "decrease")
        self.assertLess(result["nextTask"]["difficultyLevel"], current_task["difficultyLevel"])
        self.assertEqual(result["nextTask"]["moduleId"], current_task["moduleId"])

    def test_hold_recommendation_stays_within_module_when_possible(self):
        current_task = get_task("dicts-code-001")
        result = select_next_task(
            self._session(),
            current_task,
            {
                "knowledgeMastery": 62,
                "systemCognitiveFriction": 42,
                "recommendation": "hold_current_tier",
            },
        )

        self.assertEqual(result["adaptation"]["direction"], "hold")
        self.assertEqual(result["nextTask"]["moduleId"], current_task["moduleId"])

    def test_fallback_returns_a_task_when_exact_level_is_unavailable(self):
        current_task = get_task("lists-code-002")
        result = select_next_task(
            self._session(),
            current_task,
            {
                "knowledgeMastery": 90,
                "systemCognitiveFriction": 10,
                "recommendation": "increase_or_hold_high_tier",
            },
        )

        self.assertIsNotNone(result["nextTask"])
        self.assertIn(result["adaptation"]["selectedScope"], ["module", "catalog", "current_task"])
