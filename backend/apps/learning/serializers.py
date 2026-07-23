from rest_framework import serializers
from .catalog import TASK_BANK, get_task
from .models import LearnerSession

# Serializers for the learning app
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

# Serializer for the session model
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
        return obj.completed_task_count >= len(TASK_BANK)

# Serializer for task submission data
class SubmissionSerializer(serializers.Serializer):
    sessionToken = serializers.CharField()
    taskId = serializers.CharField()
    elapsedTimeSeconds = serializers.FloatField(min_value=0.1)
    skipped = serializers.BooleanField(default=False)
    assistanceInteractions = serializers.IntegerField(default=0, min_value=0)
    completionRatio = serializers.FloatField(default=1.0, min_value=0.0, max_value=1.0)
    selectedChoice = serializers.CharField(required=False, allow_blank=True)
    answerText = serializers.CharField(required=False, allow_blank=True)
    answerPayload = serializers.DictField(required=False)

    def validate(self, attrs):
        if "isCorrect" in self.initial_data:
            raise serializers.ValidationError(
                {"isCorrect": "Correctness is derived by the backend and must not be supplied."}
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
        if task["type"] == "mcq" and not attrs["skipped"] and not attrs.get("selectedChoice"):
            raise serializers.ValidationError(
                {"selectedChoice": "A selected choice is required for an MCQ task."}
            )
        if attrs["skipped"]:
            # A skip is an explicit incomplete attempt, regardless of any stale form values.
            attrs["completionRatio"] = 0.0
            attrs.pop("selectedChoice", None)
            attrs.pop("answerText", None)
        attrs["task"] = task
        return attrs

# Serializer for micro-survey responses
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


# Explicit response serializers keep the generated OpenAPI contract useful to clients.
class ErrorResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(required=False)
    moduleId = serializers.CharField(required=False)
    direction = serializers.CharField(required=False)

# Serializer for difficulty counts in a module
class DifficultyCountsSerializer(serializers.Serializer):
    foundation = serializers.IntegerField()
    intermediate = serializers.IntegerField()
    advanced = serializers.IntegerField()

# Serializer for module response data
class ModuleResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    concepts = serializers.ListField(child=serializers.CharField())
    score = serializers.FloatField()
    aggregateScore = serializers.FloatField()
    taskCount = serializers.IntegerField()
    difficultyCounts = DifficultyCountsSerializer()

# Serializer for a list of modules in the response
class ModulesResponseSerializer(serializers.Serializer):
    modules = ModuleResponseSerializer(many=True)

# Serializer for task response data
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

# Serializer for task navigation response data
class TaskNavigationResponseSerializer(serializers.Serializer):
    task = TaskResponseSerializer(allow_null=True)
    position = serializers.IntegerField()
    totalTasks = serializers.IntegerField()
    hasPrevious = serializers.BooleanField()
    hasNext = serializers.BooleanField()

# Serializer for task catalog response data
class TaskCatalogResponseSerializer(serializers.Serializer):
    tasks = TaskResponseSerializer(many=True)
    activeTask = TaskNavigationResponseSerializer()

# Serializer for session state response data
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

# Serializer for the current session task response data
class CurrentSessionTaskResponseSerializer(serializers.Serializer):
    task = TaskResponseSerializer(allow_null=True)
    session = SessionStateResponseSerializer()

# Serializer for adaptation signals response data
class AdaptationSignalsResponseSerializer(serializers.Serializer):
    knowledgeMastery = serializers.FloatField()
    systemCognitiveFriction = serializers.FloatField()
    recommendation = serializers.CharField()

# Serializer for adaptation response data
class AdaptationResponseSerializer(serializers.Serializer):
    direction = serializers.CharField()
    targetDifficultyLevel = serializers.IntegerField()
    selectedDifficulty = serializers.CharField()
    selectedScope = serializers.CharField()
    curriculumComplete = serializers.BooleanField()
    reason = serializers.CharField()
    signals = AdaptationSignalsResponseSerializer()

# Serializer for submission response data
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
    surveyDue = serializers.BooleanField()

# Serializer for micro-survey response data
class MicroSurveyResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    sessionToken = serializers.CharField()
    submissionId = serializers.IntegerField(allow_null=True)
    satisfactionScore = serializers.IntegerField()
    perceivedDifficulty = serializers.IntegerField()
    confidenceScore = serializers.IntegerField()
    milestoneTaskCount = serializers.IntegerField()
    surveyDue = serializers.BooleanField()

# Serializer for a single row of training data
class TrainingDataRowSerializer(serializers.Serializer):
    sessionToken = serializers.CharField()
    taskId = serializers.CharField()
    moduleId = serializers.IntegerField()
    taskType = serializers.CharField()
    difficulty = serializers.CharField()
    difficultyLevel = serializers.IntegerField()
    taskMetricWeight = serializers.FloatField()
    historicalGradeAverage = serializers.FloatField(allow_null=True)
    relativeResponseTime = serializers.FloatField()
    assistanceInteractions = serializers.IntegerField()
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

# Serializer for training data export response
class TrainingDataExportResponseSerializer(serializers.Serializer):
    rows = TrainingDataRowSerializer(many=True)
    count = serializers.IntegerField()
