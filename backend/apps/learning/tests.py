from django.test import TestCase
from rest_framework.test import APIClient

from .catalog import TASK_BANK, get_task
from .models import HintEvent, LearnerSession, TaskSubmission


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
            self.assertNotIn("hints", task)

    def test_every_task_has_three_distinct_progressive_hints(self):
        for task in TASK_BANK:
            hints = task["hints"]
            self.assertEqual([hint["level"] for hint in hints], [1, 2, 3])
            self.assertEqual(
                [hint["kind"] for hint in hints],
                ["conceptual", "strategy", "scaffold"],
            )
            self.assertEqual(len({hint["text"] for hint in hints}), 3)

    def test_hints_reveal_progressively_and_restore_with_session(self):
        state = self.create_session()
        payload = {
            "sessionToken": state["sessionToken"],
            "taskId": state["currentTaskId"],
            "elapsedTimeSeconds": 12,
        }

        for expected_level, expected_kind in (
            (1, "conceptual"),
            (2, "strategy"),
            (3, "scaffold"),
        ):
            response = self.client.post("/api/learning/hints/", payload, format="json")
            self.assertEqual(response.status_code, 201, response.json())
            self.assertEqual(response.json()["hint"]["level"], expected_level)
            self.assertEqual(response.json()["hint"]["kind"], expected_kind)
            self.assertEqual(
                response.json()["hintState"]["assistanceInteractions"],
                expected_level,
            )

        restored = self.client.get(
            f"/api/learning/sessions/{state['sessionToken']}/"
        ).json()
        self.assertEqual(
            [hint["level"] for hint in restored["hintState"]["revealedHints"]],
            [1, 2, 3],
        )
        self.assertTrue(restored["hintState"]["exhausted"])
        self.assertIsNone(restored["hintState"]["nextLevel"])
        self.assertEqual(
            self.client.post("/api/learning/hints/", payload, format="json").status_code,
            400,
        )

    def test_hints_are_restricted_to_the_current_task(self):
        state = self.create_session()
        response = self.client.post(
            "/api/learning/hints/",
            {
                "sessionToken": state["sessionToken"],
                "taskId": "arrays-mcq-001",
                "elapsedTimeSeconds": 5,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(HintEvent.objects.count(), 0)

    def test_submission_derives_assistance_from_recorded_hints(self):
        state = self.create_session()
        for elapsed in (10, 20):
            response = self.client.post(
                "/api/learning/hints/",
                {
                    "sessionToken": state["sessionToken"],
                    "taskId": state["currentTaskId"],
                    "elapsedTimeSeconds": elapsed,
                },
                format="json",
            )
            self.assertEqual(response.status_code, 201)

        result = self.submit_current_task(state["sessionToken"])
        submission = TaskSubmission.objects.get(pk=result["submissionId"])
        self.assertEqual(submission.assistance_interactions, 2)
        self.assertEqual(submission.max_hint_level, 2)
        self.assertEqual(result["inputSnapshot"]["assistanceInteractions"], 2)
        self.assertEqual(
            result["hintUsage"],
            {
                "assistanceInteractions": 2,
                "maxHintLevel": 2,
                "revealedLevels": [1, 2],
            },
        )

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
        base_payload["assistanceInteractions"] = 3
        self.assertEqual(
            self.client.post("/api/learning/submissions/", base_payload, format="json").status_code,
            400,
        )

        base_payload.pop("assistanceInteractions")
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

    def test_skip_records_an_incomplete_attempt_and_advances_the_session(self):
        state = self.create_session()
        response = self.client.post(
            "/api/learning/submissions/",
            {
                "sessionToken": state["sessionToken"],
                "taskId": state["currentTaskId"],
                "elapsedTimeSeconds": 3,
                "skipped": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.json())
        submission = TaskSubmission.objects.get(pk=response.json()["submissionId"])
        self.assertEqual(submission.completion_ratio, 0)
        self.assertIsNone(submission.is_correct)
        self.assertTrue(submission.answer_payload["skipped"])
        self.assertEqual(response.json()["session"]["completedTaskCount"], 1)
        self.assertNotEqual(response.json()["nextTask"]["id"], state["currentTaskId"])

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
