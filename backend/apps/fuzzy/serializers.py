from rest_framework import serializers

# Serializer for input data to the fuzzy evaluation engine
class FuzzyEvaluationInputSerializer(serializers.Serializer):
    taskMetricWeight = serializers.FloatField(default=50.0, min_value=0.0, max_value=100.0)
    historicalGradeAverage = serializers.FloatField(default=70.0, min_value=0.0, max_value=100.0)
    relativeResponseTime = serializers.FloatField(default=1.0, min_value=0.0)
    assistanceInteractions = serializers.IntegerField(default=0, min_value=0)
    completionRatio = serializers.FloatField(default=1.0, min_value=0.0, max_value=1.0)
    taskType = serializers.ChoiceField(choices=("mcq", "code"), default="mcq")
    isCorrect = serializers.BooleanField(required=False, allow_null=True)
    selectedChoice = serializers.CharField(required=False, allow_blank=True)
    answerText = serializers.CharField(required=False, allow_blank=True)

    def validate_taskType(self, value):
        return str(value).lower()

# Serializer for output data from the fuzzy evaluation engine
class FuzzyEvaluationOutputSerializer(serializers.Serializer):
    knowledgeMastery = serializers.FloatField()
    systemCognitiveFriction = serializers.FloatField()
    focusState = serializers.CharField()
    recommendation = serializers.CharField()
    supportMessage = serializers.CharField()
    inputSnapshot = serializers.DictField()
    engineTrace = serializers.DictField(required=False)
