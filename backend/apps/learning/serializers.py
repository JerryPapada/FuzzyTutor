from rest_framework import serializers
from .catalog import get_task
from .models import LearnerSession
from .progress import curriculum_complete

class SessionCreateSerializer(serializers.Serializer):
    moduleId = serializers.IntegerField(required=False, min_value=1)
    taskId = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        task_id = attrs.get("taskId")
        module_id = attrs.get("moduleId")
        if task_id and get_task(task_id) is None:
            raise serializers.ValidationError({"taskId": "Unknown task id."})
        if task_id:
            attrs["moduleId"] = get_task(task_id)["moduleId"]
        elif module_id is not None and not any(
            task["moduleId"] == module_id for task in self.context["tasks"]
        ):
            raise serializers.ValidationError({"moduleId": "Unknown module id."})
        return attrs

class SessionSerializer(serializers.ModelSerializer):
    sessionToken = serializers.CharField(source="token")
    currentModuleId = serializers.IntegerField(source="current_module_id")
    currentTaskId = serializers.CharField(source="current_task_id")
    aggregateMastery = serializers.FloatField(source="aggregate_mastery")
    aggregateFriction = serializers.FloatField(source="aggregate_friction")
    completedTaskCount = serializers.IntegerField(source="completed_task_count")
    latestRecommendation = serializers.CharField(source="latest_recommendation")
    surveyDue = serializers.SerializerMethodField()
    curriculumComplete = serializers.SerializerMethodField()

    class Meta:
        model = LearnerSession
        fields = [
            "sessionToken",
            "currentModuleId",
            "currentTaskId",
            "aggregateMastery",
            "aggregateFriction",
            "completedTaskCount",
            "latestRecommendation",
            "surveyDue",
            "curriculumComplete",
        ]

    def get_surveyDue(self, obj):
        return obj.pending_survey_milestone() is not None

    def get_curriculumComplete(self, obj):
        return curriculum_complete(obj)

class SubmissionSerializer(serializers.Serializer):
    """Validate public response fields and derive private grading metadata."""
    sessionToken = serializers.CharField()
    taskId = serializers.CharField()
    elapsedTimeSeconds = serializers.FloatField(min_value=0.1)
    skipped = serializers.BooleanField(default=False)
    selectedChoice = serializers.CharField(required=False, allow_blank=True)
    answerText = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if "completionRatio" in self.initial_data:
            raise serializers.ValidationError(
                {
                    "completionRatio": (
                        "Completion is derived by the backend and must not be supplied."
                    )
                }
            )
        if "isCorrect" in self.initial_data:
            raise serializers.ValidationError(
                {"isCorrect": "Correctness is derived by the backend and must not be supplied."}
            )
        if "assistanceInteractions" in self.initial_data:
            raise serializers.ValidationError(
                {
                    "assistanceInteractions": (
                        "Assistance is derived from server-recorded hint events and must not be supplied."
                    )
                }
            )
        if "answerPayload" in self.initial_data:
            raise serializers.ValidationError(
                {
                    "answerPayload": (
                        "Answer metadata is built by the backend and must not be supplied."
                    )
                }
            )
        try:
            attrs["session"] = LearnerSession.objects.select_for_update().get(
                token=attrs["sessionToken"]
            )
        except LearnerSession.DoesNotExist:
            raise serializers.ValidationError({"sessionToken": "Unknown session token."})

        task = get_task(attrs["taskId"])
        if task is None:
            raise serializers.ValidationError({"taskId": "Unknown task id."})
        if task["id"] != attrs["session"].current_task_id:
            raise serializers.ValidationError(
                {"taskId": "Task is not the current backend-selected task for this session."}
            )
        if attrs["session"].submissions.filter(task_id=task["id"]).exists():
            raise serializers.ValidationError({"taskId": "Task has already been completed."})
        if attrs["skipped"]:
            # A skip is an explicit incomplete attempt, regardless of any stale form values.
            attrs["completionRatio"] = 0.0
            attrs.pop("selectedChoice", None)
            attrs.pop("answerText", None)
        elif task["type"] == "mcq":
            selected_choice = attrs.get("selectedChoice")
            if not selected_choice:
                raise serializers.ValidationError(
                    {"selectedChoice": "A selected choice is required for an MCQ task."}
                )
            if selected_choice not in task["choices"]:
                raise serializers.ValidationError(
                    {"selectedChoice": "The selected choice is not valid for this task."}
                )
            attrs["completionRatio"] = 1.0
            attrs.pop("answerText", None)
        else:
            answer_text = attrs.get("answerText", "")
            normalized_answer = self._normalize_code(answer_text)
            normalized_starter = self._normalize_code(task.get("starterCode", ""))
            if not normalized_answer:
                raise serializers.ValidationError(
                    {"answerText": "Enter a code response or explicitly skip this task."}
                )
            if normalized_answer == normalized_starter:
                raise serializers.ValidationError(
                    {
                        "answerText": (
                            "Edit the starter code meaningfully or explicitly skip this task."
                        )
                    }
                )
            attrs["completionRatio"] = 1.0
            attrs.pop("selectedChoice", None)
        attrs["task"] = task
        return attrs

    @staticmethod
    def _normalize_code(value):
        lines = str(value or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        return "\n".join(line.rstrip() for line in lines).strip()


class HintRequestSerializer(serializers.Serializer):
    sessionToken = serializers.CharField()
    taskId = serializers.CharField()
    elapsedTimeSeconds = serializers.FloatField(min_value=0.0)

    def validate(self, attrs):
        try:
            session = LearnerSession.objects.select_for_update().get(
                token=attrs["sessionToken"]
            )
        except LearnerSession.DoesNotExist:
            raise serializers.ValidationError({"sessionToken": "Unknown session token."})

        task = get_task(attrs["taskId"])
        if task is None:
            raise serializers.ValidationError({"taskId": "Unknown task id."})
        if task["id"] != session.current_task_id:
            raise serializers.ValidationError(
                {"taskId": "Hints are only available for the current backend-selected task."}
            )
        if session.submissions.filter(task_id=task["id"]).exists():
            raise serializers.ValidationError(
                {"taskId": "Hints are unavailable after a task has been completed."}
            )

        revealed_levels = set(
            session.hint_events.filter(task_id=task["id"]).values_list("level", flat=True)
        )
        next_level = next(
            (
                hint["level"]
                for hint in task["hints"]
                if hint["level"] not in revealed_levels
            ),
            None,
        )
        if next_level is None:
            raise serializers.ValidationError(
                {"taskId": "All three hint levels have already been revealed."}
            )

        attrs["session"] = session
        attrs["task"] = task
        attrs["hint"] = task["hints"][next_level - 1]
        return attrs


class MicroSurveySerializer(serializers.Serializer):
    sessionToken = serializers.CharField()
    satisfactionScore = serializers.IntegerField(min_value=1, max_value=5)
    perceivedDifficulty = serializers.IntegerField(min_value=1, max_value=5)
    confidenceScore = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        try:
            attrs["session"] = LearnerSession.objects.select_for_update().get(
                token=attrs["sessionToken"]
            )
        except LearnerSession.DoesNotExist:
            raise serializers.ValidationError({"sessionToken": "Unknown session token."})
        milestone = attrs["session"].pending_survey_milestone()
        if milestone is None:
            raise serializers.ValidationError(
                {"sessionToken": "No unanswered five-task survey is currently due."}
            )
        attrs["milestoneTaskCount"] = milestone
        return attrs


# These response-only serializers are verbose by design: they keep Swagger useful
# and prevent accidental API changes while the React client is developed separately.
class ErrorResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(required=False)
    moduleId = serializers.CharField(required=False)
    direction = serializers.CharField(required=False)
    sessionToken = serializers.CharField(required=False)
    taskId = serializers.CharField(required=False)
    assistanceInteractions = serializers.CharField(required=False)
    answerPayload = serializers.CharField(required=False)
    completionRatio = serializers.CharField(required=False)
    selectedChoice = serializers.CharField(required=False)
    answerText = serializers.CharField(required=False)

class DifficultyCountsSerializer(serializers.Serializer):
    foundation = serializers.IntegerField()
    intermediate = serializers.IntegerField()
    advanced = serializers.IntegerField()

class ModuleResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    concepts = serializers.ListField(child=serializers.CharField())
    score = serializers.FloatField()
    aggregateScore = serializers.FloatField()
    taskCount = serializers.IntegerField()
    difficultyCounts = DifficultyCountsSerializer()

class ModulesResponseSerializer(serializers.Serializer):
    modules = ModuleResponseSerializer(many=True)

class TaskResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    moduleId = serializers.IntegerField()
    type = serializers.CharField()
    difficulty = serializers.ChoiceField(choices=("foundation", "intermediate", "advanced"))
    difficultyLevel = serializers.IntegerField()
    taskMetricWeight = serializers.FloatField()
    estimatedCognitiveLoad = serializers.CharField()
    baselineTimeSeconds = serializers.IntegerField()
    prompt = serializers.CharField()
    conceptTags = serializers.ListField(child=serializers.CharField())
    adaptationSignals = serializers.DictField()
    choices = serializers.ListField(child=serializers.CharField(), required=False)
    starterCode = serializers.CharField(required=False, allow_blank=True)


class ReviewTaskResponseSerializer(TaskResponseSerializer):
    explanation = serializers.CharField()
    correctChoice = serializers.CharField(required=False)
    answerGuide = serializers.CharField(required=False)


class RevealedHintResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    level = serializers.IntegerField()
    kind = serializers.CharField()
    label = serializers.CharField()
    text = serializers.CharField()
    elapsedTimeSeconds = serializers.FloatField()
    revealedAt = serializers.DateTimeField()


class HintStateResponseSerializer(serializers.Serializer):
    revealedHints = RevealedHintResponseSerializer(many=True)
    assistanceInteractions = serializers.IntegerField()
    maxHintLevel = serializers.IntegerField()
    nextLevel = serializers.IntegerField(allow_null=True)
    exhausted = serializers.BooleanField()


class HintRevealResponseSerializer(serializers.Serializer):
    hint = RevealedHintResponseSerializer()
    hintState = HintStateResponseSerializer()


class ReviewItemResponseSerializer(serializers.Serializer):
    submissionId = serializers.IntegerField()
    moduleId = serializers.IntegerField()
    outcome = serializers.ChoiceField(choices=("skipped", "incorrect"))
    learnerAnswer = serializers.DictField()
    task = ReviewTaskResponseSerializer()
    revealedHints = RevealedHintResponseSerializer(many=True)
    submittedAt = serializers.DateTimeField()


class ReviewResponseSerializer(serializers.Serializer):
    items = ReviewItemResponseSerializer(many=True)
    count = serializers.IntegerField()


class ModuleProgressResponseSerializer(serializers.Serializer):
    moduleId = serializers.IntegerField()
    moduleMastery = serializers.FloatField()
    moduleFriction = serializers.FloatField()
    attemptedTaskCount = serializers.IntegerField()
    status = serializers.CharField()
    exitReason = serializers.CharField(allow_null=True)
    terminal = serializers.BooleanField()
    completedAt = serializers.DateTimeField(allow_null=True)


class TaskNavigationResponseSerializer(serializers.Serializer):
    task = TaskResponseSerializer(allow_null=True)
    position = serializers.IntegerField()
    totalTasks = serializers.IntegerField()
    hasPrevious = serializers.BooleanField()
    hasNext = serializers.BooleanField()

class TaskCatalogResponseSerializer(serializers.Serializer):
    tasks = TaskResponseSerializer(many=True)
    activeTask = TaskNavigationResponseSerializer()


class OrderedAttemptResponseSerializer(serializers.Serializer):
    taskId = serializers.CharField()
    moduleId = serializers.IntegerField()
    skipped = serializers.BooleanField()
    outcome = serializers.ChoiceField(
        choices=("correct", "incorrect", "completed", "skipped")
    )
    learnerAnswer = serializers.DictField()
    submittedAt = serializers.DateTimeField()


class SessionStateResponseSerializer(serializers.Serializer):
    sessionToken = serializers.CharField()
    currentModuleId = serializers.IntegerField()
    currentTaskId = serializers.CharField()
    aggregateMastery = serializers.FloatField()
    aggregateFriction = serializers.FloatField()
    completedTaskCount = serializers.IntegerField()
    latestRecommendation = serializers.CharField()
    surveyDue = serializers.BooleanField()
    curriculumComplete = serializers.BooleanField()
    currentTask = TaskResponseSerializer(allow_null=True)
    submittedTaskIds = serializers.ListField(child=serializers.CharField(), required=False)
    skippedTaskIds = serializers.ListField(child=serializers.CharField(), required=False)
    orderedAttempts = OrderedAttemptResponseSerializer(many=True, required=False)
    hintState = HintStateResponseSerializer()
    moduleProgress = ModuleProgressResponseSerializer(many=True)

class CurrentSessionTaskResponseSerializer(serializers.Serializer):
    task = TaskResponseSerializer(allow_null=True)
    session = SessionStateResponseSerializer()

class AdaptationSignalsResponseSerializer(serializers.Serializer):
    knowledgeMastery = serializers.FloatField()
    systemCognitiveFriction = serializers.FloatField()
    recommendation = serializers.CharField()

class AdaptationResponseSerializer(serializers.Serializer):
    direction = serializers.CharField()
    requestedDirection = serializers.CharField()
    constraintApplied = serializers.CharField(allow_null=True)
    targetDifficultyLevel = serializers.IntegerField()
    selectedDifficulty = serializers.CharField()
    selectedScope = serializers.CharField()
    curriculumComplete = serializers.BooleanField()
    reason = serializers.CharField()
    signals = AdaptationSignalsResponseSerializer()


class HintUsageResponseSerializer(serializers.Serializer):
    assistanceInteractions = serializers.IntegerField()
    maxHintLevel = serializers.IntegerField()
    revealedLevels = serializers.ListField(child=serializers.IntegerField())


class ModuleDecisionResponseSerializer(serializers.Serializer):
    moduleId = serializers.IntegerField()
    outcome = serializers.CharField()
    attemptedTaskCount = serializers.IntegerField()
    moduleMastery = serializers.FloatField()
    moduleFriction = serializers.FloatField()
    minimumAttempts = serializers.IntegerField()
    recentMcqResults = serializers.ListField(
        child=serializers.BooleanField(allow_null=True)
    )
    recentMcqCorrectCount = serializers.IntegerField()
    masteryThresholdMet = serializers.BooleanField()
    nextModuleId = serializers.IntegerField(allow_null=True)


class SubmissionResponseSerializer(serializers.Serializer):
    knowledgeMastery = serializers.FloatField()
    systemCognitiveFriction = serializers.FloatField()
    focusState = serializers.CharField()
    recommendation = serializers.CharField()
    supportMessage = serializers.CharField()
    inputSnapshot = serializers.DictField()
    engineTrace = serializers.DictField()
    submissionId = serializers.IntegerField()
    session = SessionStateResponseSerializer()
    nextTask = TaskResponseSerializer()
    adaptation = AdaptationResponseSerializer()
    moduleDecision = ModuleDecisionResponseSerializer()
    hintUsage = HintUsageResponseSerializer()
    surveyDue = serializers.BooleanField()

class MicroSurveyResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    sessionToken = serializers.CharField()
    submissionId = serializers.IntegerField(allow_null=True)
    satisfactionScore = serializers.IntegerField()
    perceivedDifficulty = serializers.IntegerField()
    confidenceScore = serializers.IntegerField()
    milestoneTaskCount = serializers.IntegerField()
    surveyDue = serializers.BooleanField()

class TrainingDataRowSerializer(serializers.Serializer):
    sessionToken = serializers.CharField()
    taskId = serializers.CharField()
    moduleId = serializers.IntegerField()
    taskType = serializers.CharField()
    difficulty = serializers.CharField()
    difficultyLevel = serializers.IntegerField()
    taskMetricWeight = serializers.FloatField()
    historicalGradeAverage = serializers.FloatField(allow_null=True)
    moduleMasteryBefore = serializers.FloatField()
    moduleFrictionBefore = serializers.FloatField()
    moduleExitOutcome = serializers.CharField()
    relativeResponseTime = serializers.FloatField()
    assistanceInteractions = serializers.IntegerField()
    maxHintLevel = serializers.IntegerField()
    revealedHintLevels = serializers.ListField(child=serializers.IntegerField())
    completionRatio = serializers.FloatField()
    isCorrect = serializers.BooleanField(allow_null=True)
    knowledgeMastery = serializers.FloatField()
    systemCognitiveFriction = serializers.FloatField()
    focusState = serializers.CharField()
    recommendation = serializers.CharField()
    satisfactionScore = serializers.IntegerField(allow_null=True)
    perceivedDifficulty = serializers.IntegerField(allow_null=True)
    confidenceScore = serializers.IntegerField(allow_null=True)
    createdAt = serializers.DateTimeField()

class TrainingDataExportResponseSerializer(serializers.Serializer):
    rows = TrainingDataRowSerializer(many=True)
    count = serializers.IntegerField()
