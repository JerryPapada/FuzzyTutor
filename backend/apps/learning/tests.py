from django.test import TestCase
from rest_framework.test import APIClient

from .catalog import get_task
from .models import LearnerSession, TaskSubmission


class LearningApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def create_session(self, **payload):
        response = self.client.post("/api/learning/sessions/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        return response.json()

    def submit_current_task(self, token):
        session = LearnerSession.objects.get(token=token)
        task = get_task(session.current_task_id)
        payload = {
            "sessionToken": token,
            "taskId": task["id"],
            "elapsedTimeSeconds": task["baselineTimeSeconds"],
            "assistanceInteractions": 0,
            "completionRatio": 1.0,
        }
        if task["type"] == "mcq":
            payload["selectedChoice"] = task["correctChoice"]
        else:
            payload["answerText"] = "completed code response"
        response = self.client.post("/api/learning/submissions/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.json())
        return response.json()

    def test_public_tasks_do_not_expose_solutions(self):
        response = self.client.get("/api/learning/tasks/")

        self.assertEqual(response.status_code, 200)
        for task in response.json()["tasks"]:
            self.assertNotIn("correctChoice", task)
            self.assertNotIn("answerGuide", task)

    def test_invalid_module_queries_return_400(self):
        self.assertEqual(self.client.get("/api/learning/tasks/?moduleId=999").status_code, 400)
        self.assertEqual(self.client.get("/api/learning/tasks/?moduleId=bad").status_code, 400)
        self.assertEqual(
            self.client.get("/api/learning/next-task/?direction=sideways").status_code,
            400,
        )

    def test_submission_rejects_client_correctness_and_non_current_task(self):
        state = self.create_session()
        base_payload = {
            "sessionToken": state["sessionToken"],
            "taskId": state["currentTaskId"],
            "elapsedTimeSeconds": 10,
            "completionRatio": 1,
            "selectedChoice": "Adds an item to the end",
            "isCorrect": True,
        }
        self.assertEqual(
            self.client.post("/api/learning/submissions/", base_payload, format="json").status_code,
            400,
        )

        base_payload.pop("isCorrect")
        base_payload["taskId"] = "arrays-mcq-001"
        self.assertEqual(
            self.client.post("/api/learning/submissions/", base_payload, format="json").status_code,
            400,
        )

    def test_code_completion_is_not_stored_as_correctness(self):
        state = self.create_session(taskId="lists-code-001")
        result = self.submit_current_task(state["sessionToken"])

        submission = TaskSubmission.objects.get(pk=result["submissionId"])
        self.assertIsNone(submission.is_correct)

    def test_adaptation_does_not_repeat_tasks_and_advances_modules(self):
        state = self.create_session()
        token = state["sessionToken"]
        submitted_task_ids = []

        for _index in range(6):
            session = LearnerSession.objects.get(token=token)
            submitted_task_ids.append(session.current_task_id)
            self.submit_current_task(token)

        self.assertEqual(len(submitted_task_ids), len(set(submitted_task_ids)))
        self.assertGreater(LearnerSession.objects.get(token=token).current_module_id, 1)

    def test_survey_milestone_clears_and_cannot_be_duplicated(self):
        state = self.create_session()
        token = state["sessionToken"]
        result = None
        for _index in range(5):
            result = self.submit_current_task(token)

        self.assertTrue(result["surveyDue"])
        survey_payload = {
            "sessionToken": token,
            "satisfactionScore": 4,
            "perceivedDifficulty": 3,
            "confidenceScore": 4,
        }
        survey = self.client.post("/api/learning/micro-surveys/", survey_payload, format="json")
        self.assertEqual(survey.status_code, 201)
        self.assertEqual(survey.json()["milestoneTaskCount"], 5)
        self.assertFalse(survey.json()["surveyDue"])
        self.assertFalse(self.client.get(f"/api/learning/sessions/{token}/").json()["surveyDue"])
        self.assertEqual(
            self.client.post("/api/learning/micro-surveys/", survey_payload, format="json").status_code,
            400,
        )
