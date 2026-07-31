from collections import Counter
from importlib import import_module

from django.apps import apps as django_apps
from django.test import TestCase
from rest_framework.test import APIClient

from .catalog import CURRICULUM_MODULES, TASK_BANK, get_task, tasks_for_module
from .models import (
    FuzzyEvaluationLog,
    HintEvent,
    LearnerSession,
    ModuleProgress,
    TaskSubmission,
)


class LearningApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def create_session(self, **payload):
        response = self.client.post("/api/learning/sessions/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        return response.json()

    def submit_current_task(self, token, correct=True, skipped=False):
        session = LearnerSession.objects.get(token=token)
        task = get_task(session.current_task_id)
        payload = {
            "sessionToken": token,
            "taskId": task["id"],
            "elapsedTimeSeconds": task["baselineTimeSeconds"],
        }
        if skipped:
            payload["skipped"] = True
        elif task["type"] == "mcq":
            payload["selectedChoice"] = (
                task["correctChoice"]
                if correct
                else next(
                    choice
                    for choice in task["choices"]
                    if choice != task["correctChoice"]
                )
            )
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
            self.assertNotIn("explanation", task)
            self.assertNotIn("hints", task)

    def test_expanded_task_bank_distribution_and_private_content(self):
        self.assertEqual(len(TASK_BANK), 105)
        self.assertEqual(len({task["id"] for task in TASK_BANK}), 105)
        self.assertEqual(
            Counter(task["type"] for task in TASK_BANK),
            Counter({"mcq": 53, "code": 52}),
        )

        expected_types = {
            1: Counter({"mcq": 8, "code": 7}),
            2: Counter({"mcq": 7, "code": 8}),
            3: Counter({"mcq": 8, "code": 7}),
            4: Counter({"mcq": 7, "code": 8}),
            5: Counter({"mcq": 8, "code": 7}),
            6: Counter({"mcq": 7, "code": 8}),
            7: Counter({"mcq": 8, "code": 7}),
        }
        for module in CURRICULUM_MODULES:
            module_tasks = tasks_for_module(module["id"])
            self.assertEqual(len(module_tasks), 15)
            self.assertEqual(
                Counter(task["difficulty"] for task in module_tasks),
                Counter(
                    {"foundation": 5, "intermediate": 5, "advanced": 5}
                ),
            )
            self.assertEqual(
                Counter(task["type"] for task in module_tasks),
                expected_types[module["id"]],
            )

        for task in TASK_BANK:
            self.assertTrue(task["explanation"])
            hints = task["hints"]
            self.assertEqual([hint["level"] for hint in hints], [1, 2, 3])
            self.assertEqual(
                [hint["kind"] for hint in hints],
                ["conceptual", "strategy", "scaffold"],
            )
            self.assertEqual(len({hint["text"] for hint in hints}), 3)
            if task["type"] == "mcq":
                self.assertEqual(len(task["choices"]), 4)
                self.assertIn(task["correctChoice"], task["choices"])
            else:
                self.assertTrue(task["answerGuide"])

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

    def test_every_expanded_task_can_reveal_its_first_hint(self):
        for task in TASK_BANK:
            state = self.create_session(taskId=task["id"])
            response = self.client.post(
                "/api/learning/hints/",
                {
                    "sessionToken": state["sessionToken"],
                    "taskId": task["id"],
                    "elapsedTimeSeconds": 1,
                },
                format="json",
            )
            self.assertEqual(response.status_code, 201, task["id"])
            self.assertEqual(response.json()["hint"]["level"], 1)
            self.assertEqual(
                response.json()["hint"]["text"],
                task["hints"][0]["text"],
            )
            self.assertEqual(
                len(response.json()["hintState"]["revealedHints"]),
                1,
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
        base_payload["answerPayload"] = {
            "skipped": True,
            "synthetic": True,
            "targetMastery": 100,
        }
        response = self.client.post(
            "/api/learning/submissions/",
            base_payload,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("answerPayload", response.json())
        self.assertEqual(TaskSubmission.objects.count(), 0)

        base_payload.pop("answerPayload")
        base_payload["taskId"] = "arrays-mcq-001"
        self.assertEqual(
            self.client.post("/api/learning/submissions/", base_payload, format="json").status_code,
            400,
        )

    def test_submission_rejects_client_completion_ratio(self):
        state = self.create_session()
        task = get_task(state["currentTaskId"])
        response = self.client.post(
            "/api/learning/submissions/",
            {
                "sessionToken": state["sessionToken"],
                "taskId": task["id"],
                "elapsedTimeSeconds": 10,
                "completionRatio": 1,
                "selectedChoice": task["correctChoice"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("completionRatio", response.json())

    def test_submission_derives_mcq_completion_and_validates_choice(self):
        state = self.create_session()
        task = get_task(state["currentTaskId"])
        invalid = self.client.post(
            "/api/learning/submissions/",
            {
                "sessionToken": state["sessionToken"],
                "taskId": task["id"],
                "elapsedTimeSeconds": 10,
                "selectedChoice": "not a published choice",
            },
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("selectedChoice", invalid.json())

        result = self.submit_current_task(state["sessionToken"])
        submission = TaskSubmission.objects.get(pk=result["submissionId"])
        self.assertEqual(submission.completion_ratio, 1)
        self.assertEqual(result["inputSnapshot"]["completionRatio"], 1)

    def test_code_submission_requires_meaningful_edit_and_derives_completion(self):
        task = next(
            task
            for task in TASK_BANK
            if task["type"] == "code" and task.get("starterCode", "").strip()
        )

        for answer in ("", task["starterCode"], f"  {task['starterCode']}  "):
            with self.subTest(answer=answer):
                state = self.create_session(taskId=task["id"])
                response = self.client.post(
                    "/api/learning/submissions/",
                    {
                        "sessionToken": state["sessionToken"],
                        "taskId": task["id"],
                        "elapsedTimeSeconds": 10,
                        "answerText": answer,
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("answerText", response.json())

        state = self.create_session(taskId=task["id"])
        response = self.client.post(
            "/api/learning/submissions/",
            {
                "sessionToken": state["sessionToken"],
                "taskId": task["id"],
                "elapsedTimeSeconds": 10,
                "answerText": f"{task['starterCode']}\n# learner edit",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.json())
        submission = TaskSubmission.objects.get(pk=response.json()["submissionId"])
        self.assertEqual(submission.completion_ratio, 1)
        self.assertIsNone(submission.is_correct)
        self.assertEqual(response.json()["engineTrace"]["anfis"]["correctnessSignal"], 65)

    def test_code_completion_is_not_stored_as_correctness(self):
        state = self.create_session(taskId="lists-code-001")
        result = self.submit_current_task(state["sessionToken"])

        submission = TaskSubmission.objects.get(pk=result["submissionId"])
        self.assertIsNone(submission.is_correct)

    def test_session_exposes_seven_module_progress_records(self):
        state = self.create_session()

        self.assertEqual(len(state["moduleProgress"]), 7)
        self.assertEqual(state["moduleProgress"][0]["status"], "active")
        self.assertTrue(
            all(
                item["status"] == "not_started"
                for item in state["moduleProgress"][1:]
            )
        )
        self.assertFalse(state["curriculumComplete"])

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
        self.assertEqual(response.json()["adaptation"]["requestedDirection"], "decrease")
        self.assertEqual(response.json()["adaptation"]["direction"], "hold")
        self.assertEqual(
            response.json()["adaptation"]["constraintApplied"],
            "difficulty_floor",
        )
        self.assertIn("difficulty floor", response.json()["adaptation"]["reason"])

    def test_strong_performance_exits_after_six_balanced_tasks(self):
        state = self.create_session()
        token = state["sessionToken"]
        submitted_task_ids = []
        task_types = []
        result = None

        for index in range(6):
            session = LearnerSession.objects.get(token=token)
            submitted_task_ids.append(session.current_task_id)
            task_types.append(get_task(session.current_task_id)["type"])
            result = self.submit_current_task(token)
            if index < 5:
                self.assertEqual(result["moduleDecision"]["outcome"], "continue")
                self.assertEqual(
                    result["session"]["currentModuleId"],
                    1,
                )
            if index == 0:
                self.assertEqual(result["adaptation"]["direction"], "increase")
                self.assertEqual(result["adaptation"]["requestedDirection"], "increase")
                self.assertIsNone(result["adaptation"]["constraintApplied"])
                self.assertEqual(
                    result["nextTask"]["difficulty"],
                    "intermediate",
                )
                self.assertEqual(result["nextTask"]["type"], "code")

        self.assertEqual(len(submitted_task_ids), len(set(submitted_task_ids)))
        self.assertEqual(Counter(task_types), Counter({"mcq": 3, "code": 3}))
        self.assertEqual(result["moduleDecision"]["outcome"], "mastery_exit")
        self.assertTrue(result["moduleDecision"]["masteryThresholdMet"])
        self.assertEqual(result["moduleDecision"]["nextModuleId"], 2)
        self.assertEqual(
            LearnerSession.objects.get(token=token).current_module_id,
            2,
        )
        progress = ModuleProgress.objects.get(session__token=token, module_id=1)
        self.assertEqual(progress.status, ModuleProgress.STATUS_MASTERED)
        self.assertEqual(
            ModuleProgress.objects.get(
                session__token=token,
                module_id=2,
            ).status,
            ModuleProgress.STATUS_ACTIVE,
        )
        self.assertTrue(
            ModuleProgress.objects.filter(
                session__token=token,
                module_id__gt=2,
                status=ModuleProgress.STATUS_NOT_STARTED,
            ).exists()
        )

    def test_struggling_learner_uses_all_fifteen_tasks_before_advancing(self):
        state = self.create_session()
        token = state["sessionToken"]
        task_ids = []
        result = None

        for index in range(15):
            session = LearnerSession.objects.get(token=token)
            task_ids.append(session.current_task_id)
            result = self.submit_current_task(token, skipped=True)
            expected = "bank_exhausted" if index == 14 else "continue"
            self.assertEqual(result["moduleDecision"]["outcome"], expected)

        self.assertEqual(len(set(task_ids)), 15)
        self.assertEqual(result["moduleDecision"]["nextModuleId"], 2)
        progress = ModuleProgress.objects.get(session__token=token, module_id=1)
        self.assertEqual(
            progress.status,
            ModuleProgress.STATUS_COMPLETED_BANK,
        )

    def test_curriculum_completion_uses_terminal_module_progress(self):
        state = self.create_session()
        session = LearnerSession.objects.get(token=state["sessionToken"])
        session.module_progress.update(
            status=ModuleProgress.STATUS_MASTERED,
            exit_reason="mastery_exit",
        )

        restored = self.client.get(
            f"/api/learning/sessions/{session.token}/"
        ).json()
        self.assertTrue(restored["curriculumComplete"])

    def test_review_is_read_only_for_skipped_and_incorrect_attempts(self):
        state = self.create_session()
        token = state["sessionToken"]
        first_task_id = state["currentTaskId"]
        hint_response = self.client.post(
            "/api/learning/hints/",
            {
                "sessionToken": token,
                "taskId": first_task_id,
                "elapsedTimeSeconds": 5,
            },
            format="json",
        )
        self.assertEqual(hint_response.status_code, 201)
        incorrect = self.submit_current_task(token, correct=False)
        skipped_task_id = incorrect["nextTask"]["id"]
        self.submit_current_task(token, skipped=True)

        review_response = self.client.get(
            f"/api/learning/sessions/{token}/review/"
        )
        self.assertEqual(review_response.status_code, 200)
        review = review_response.json()
        self.assertEqual(review["count"], 2)
        self.assertEqual(
            [item["outcome"] for item in review["items"]],
            ["incorrect", "skipped"],
        )
        first_review = review["items"][0]
        self.assertEqual(first_review["task"]["id"], first_task_id)
        self.assertIn("correctChoice", first_review["task"])
        self.assertIn("explanation", first_review["task"])
        self.assertEqual(len(first_review["revealedHints"]), 1)
        skipped_review = review["items"][1]
        self.assertEqual(skipped_review["task"]["id"], skipped_task_id)
        if skipped_review["task"]["type"] == "code":
            self.assertIn("answerGuide", skipped_review["task"])

        retry = self.client.post(
            "/api/learning/submissions/",
            {
                "sessionToken": token,
                "taskId": first_task_id,
                "elapsedTimeSeconds": 20,
                "selectedChoice": get_task(first_task_id)["correctChoice"],
            },
            format="json",
        )
        self.assertEqual(retry.status_code, 400)

    def test_correct_attempt_is_not_added_to_review(self):
        state = self.create_session()
        self.submit_current_task(state["sessionToken"])

        review = self.client.get(
            f"/api/learning/sessions/{state['sessionToken']}/review/"
        ).json()
        self.assertEqual(review["count"], 0)

    def test_session_history_restores_every_learner_response(self):
        mcq_task = next(task for task in TASK_BANK if task["type"] == "mcq")
        code_task = next(task for task in TASK_BANK if task["type"] == "code")
        incorrect_choice = next(
            choice
            for choice in mcq_task["choices"]
            if choice != mcq_task["correctChoice"]
        )
        cases = (
            (
                mcq_task,
                {"selectedChoice": mcq_task["correctChoice"]},
                "correct",
                {"selectedChoice": mcq_task["correctChoice"]},
            ),
            (
                mcq_task,
                {"selectedChoice": incorrect_choice},
                "incorrect",
                {"selectedChoice": incorrect_choice},
            ),
            (
                code_task,
                {"answerText": "print('persisted code response')"},
                "completed",
                {"answerText": "print('persisted code response')"},
            ),
            (
                mcq_task,
                {"skipped": True},
                "skipped",
                {"skipped": True},
            ),
        )

        for task, response_fields, expected_outcome, expected_answer in cases:
            with self.subTest(task=task["id"], outcome=expected_outcome):
                state = self.create_session(taskId=task["id"])
                payload = {
                    "sessionToken": state["sessionToken"],
                    "taskId": task["id"],
                    "elapsedTimeSeconds": 10,
                    **response_fields,
                }
                submission = self.client.post(
                    "/api/learning/submissions/",
                    payload,
                    format="json",
                )
                self.assertEqual(submission.status_code, 201, submission.json())

                restored = self.client.get(
                    f"/api/learning/sessions/{state['sessionToken']}/"
                )
                self.assertEqual(restored.status_code, 200)
                attempt = restored.json()["orderedAttempts"][0]
                self.assertEqual(attempt["taskId"], task["id"])
                self.assertEqual(attempt["outcome"], expected_outcome)
                self.assertEqual(attempt["learnerAnswer"], expected_answer)
                self.assertTrue(attempt["submittedAt"])

                # Attempt history restores the learner's response, not private solutions.
                self.assertNotIn("correctChoice", attempt)
                self.assertNotIn("answerGuide", attempt)

    def test_training_export_contains_module_progress_snapshots(self):
        state = self.create_session()
        result = self.submit_current_task(state["sessionToken"])

        export = self.client.get(
            "/api/learning/export/training-data/"
        ).json()
        row = next(
            row
            for row in export["rows"]
            if row["taskId"] == state["currentTaskId"]
        )
        self.assertEqual(row["moduleMasteryBefore"], 50.0)
        self.assertEqual(row["moduleFrictionBefore"], 25.0)
        self.assertEqual(
            row["moduleExitOutcome"],
            result["moduleDecision"]["outcome"],
        )

    def test_legacy_three_task_module_is_backfilled_as_completed(self):
        session = LearnerSession.objects.create(
            current_module_id=2,
            current_task_id="arrays-mcq-001",
            completed_task_count=3,
        )
        legacy_ids = ["lists-mcq-001", "lists-code-001", "lists-code-002"]
        for index, task_id in enumerate(legacy_ids):
            task = get_task(task_id)
            submission = TaskSubmission.objects.create(
                session=session,
                task_id=task_id,
                module_id=1,
                task_type=task["type"],
                difficulty=task["difficulty"],
                difficulty_level=task["difficultyLevel"],
                task_metric_weight=task["taskMetricWeight"],
                baseline_time_seconds=task["baselineTimeSeconds"],
                elapsed_time_seconds=task["baselineTimeSeconds"],
                relative_response_time=1,
                completion_ratio=1,
                is_correct=True if task["type"] == "mcq" else None,
            )
            FuzzyEvaluationLog.objects.create(
                session=session,
                submission=submission,
                input_snapshot={},
                engine_trace={},
                knowledge_mastery=80 + index,
                system_cognitive_friction=20,
                focus_state="Focused & Steady",
                recommendation="hold_current_tier",
                support_message="Ready.",
            )

        migration = import_module(
            "apps.learning.migrations.0004_module_progress"
        )
        migration.backfill_module_progress(django_apps, None)

        progress = ModuleProgress.objects.get(session=session, module_id=1)
        self.assertEqual(
            progress.status,
            ModuleProgress.STATUS_LEGACY_COMPLETED,
        )
        self.assertEqual(progress.attempted_task_count, 3)
        self.assertEqual(
            session.submissions.order_by("-created_at", "-id")
            .first()
            .module_exit_outcome,
            "legacy_completed",
        )

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
