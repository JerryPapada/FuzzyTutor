from rest_framework import serializers
from .catalog import get_task
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
        ]

    def get_surveyDue(self, obj):
        return obj.completed_task_count > 0 and obj.completed_task_count % 5 == 0

# Serializer for task submission data
class SubmissionSerializer(serializers.Serializer):
    sessionToken = serializers.CharField()
    taskId = serializers.CharField()
    elapsedTimeSeconds = serializers.FloatField(min_value=0.1)
    assistanceInteractions = serializers.IntegerField(default=0, min_value=0)
    completionRatio = serializers.FloatField(default=1.0, min_value=0.0, max_value=1.0)
    isCorrect = serializers.BooleanField(required=False, allow_null=True)
    selectedChoice = serializers.CharField(required=False, allow_blank=True)
    answerText = serializers.CharField(required=False, allow_blank=True)
    answerPayload = serializers.DictField(required=False)

    def validate(self, attrs):
        try:
            attrs["session"] = LearnerSession.objects.get(token=attrs["sessionToken"])
        except LearnerSession.DoesNotExist:
            raise serializers.ValidationError({"sessionToken": "Unknown session token."})

        task = get_task(attrs["taskId"])
        if task is None:
            raise serializers.ValidationError({"taskId": "Unknown task id."})
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
            attrs["session"] = LearnerSession.objects.get(token=attrs["sessionToken"])
        except LearnerSession.DoesNotExist:
            raise serializers.ValidationError({"sessionToken": "Unknown session token."})
        return attrs
