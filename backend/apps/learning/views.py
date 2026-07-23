from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, PolymorphicProxySerializer, extend_schema
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from apps.fuzzy.engines import evaluate_learning_state
from .adaptation import select_next_task
from .catalog import (
    CURRICULUM_MODULES,
    TASK_BANK,
    active_task_payload,
    first_task,
    get_task,
    module_task_counts,
    module_task_counts_by_difficulty,
    public_task_payload,
    task_index,
    tasks_for_module,
)
from .models import FuzzyEvaluationLog, LearnerSession, MicroSurveyResponse, TaskSubmission
from .serializers import (
    CurrentSessionTaskResponseSerializer,
    ErrorResponseSerializer,
    MicroSurveyResponseSerializer,
    MicroSurveySerializer,
    ModulesResponseSerializer,
    SessionCreateSerializer,
    SessionSerializer,
    SessionStateResponseSerializer,
    SubmissionResponseSerializer,
    SubmissionSerializer,
    TaskCatalogResponseSerializer,
    TaskNavigationResponseSerializer,
    TrainingDataExportResponseSerializer,
)

# Helper functions for serializing session and submission data
def session_payload(session):
    payload = SessionSerializer(session).data
    payload["currentTask"] = public_task_payload(get_task(session.current_task_id))
    return payload


def answer_payload(validated):
    payload = dict(validated.get("answerPayload") or {})
    if validated.get("skipped"):
        payload["skipped"] = True
    if "selectedChoice" in validated:
        payload["selectedChoice"] = validated["selectedChoice"]
    if "answerText" in validated:
        payload["answerText"] = validated["answerText"]
    return payload


def correctness_signal(task, validated):
    if validated.get("skipped"):
        return None
    if task["type"] == "mcq" and validated.get("selectedChoice"):
        return validated["selectedChoice"] == task.get("correctChoice")
    return None


def survey_due(session):
    return session.pending_survey_milestone() is not None


def module_id_or_error(raw_module_id):
    if raw_module_id in (None, ""):
        return None, None
    try:
        module_id = int(raw_module_id)
    except (TypeError, ValueError):
        return None, Response(
            {"moduleId": "Module id must be an integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    valid_ids = {module["id"] for module in CURRICULUM_MODULES}
    if module_id not in valid_ids:
        return None, Response(
            {"moduleId": "Unknown module id."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return module_id, None


@extend_schema(
    tags=["learning"],
    summary="List curriculum modules",
    description="Returns the seven programming modules with task totals and difficulty distribution.",
    responses={200: ModulesResponseSerializer},
)
@api_view(["GET"])
def modules(request):
    task_counts = module_task_counts()
    difficulty_counts = module_task_counts_by_difficulty()
    return Response(
        {
            "modules": [
                {
                    **module,
                    "taskCount": task_counts[module["id"]],
                    "difficultyCounts": difficulty_counts[module["id"]],
                }
                for module in CURRICULUM_MODULES
            ]
        }
    )


@extend_schema(
    tags=["learning"],
    summary="List task catalog",
    description=(
        "Returns programming tasks with fuzzy-model metadata such as difficultyLevel, "
        "taskMetricWeight, cognitive load, concept tags, and adaptation signals."
    ),
    parameters=[
        OpenApiParameter("index", OpenApiTypes.INT, OpenApiParameter.QUERY),
        OpenApiParameter("taskId", OpenApiTypes.STR, OpenApiParameter.QUERY),
        OpenApiParameter("moduleId", OpenApiTypes.INT, OpenApiParameter.QUERY),
    ],
    responses={200: TaskCatalogResponseSerializer, 400: ErrorResponseSerializer},
)
@api_view(["GET"])
def tasks(request):
    index = request.query_params.get("index")
    task_id = request.query_params.get("taskId")
    module_id = request.query_params.get("moduleId")
    module_id, error_response = module_id_or_error(module_id)
    if error_response:
        return error_response

    try:
        selected_index = int(index) if index is not None else task_index(task_id, module_id)
    except ValueError:
        selected_index = 0

    return Response(
        {
            "tasks": [public_task_payload(task) for task in tasks_for_module(module_id)],
            "activeTask": active_task_payload(selected_index, module_id),
        }
    )


@extend_schema(
    tags=["learning"],
    summary="Get next task",
    description=(
        "Returns sequential navigation for catalog browsing, or the current backend-selected "
        "task when sessionToken is supplied."
    ),
    parameters=[
        OpenApiParameter("taskId", OpenApiTypes.STR, OpenApiParameter.QUERY),
        OpenApiParameter("moduleId", OpenApiTypes.INT, OpenApiParameter.QUERY),
        OpenApiParameter("direction", OpenApiTypes.STR, OpenApiParameter.QUERY),
        OpenApiParameter("sessionToken", OpenApiTypes.STR, OpenApiParameter.QUERY),
    ],
    responses={
        200: PolymorphicProxySerializer(
            component_name="NextTaskResponse",
            serializers=[TaskNavigationResponseSerializer, CurrentSessionTaskResponseSerializer],
            resource_type_field_name=None,
        ),
        400: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
    },
)
@api_view(["GET"])
def next_task(request):
    task_id = request.query_params.get("taskId")
    module_id = request.query_params.get("moduleId")
    direction = request.query_params.get("direction", "forward")
    session_token = request.query_params.get("sessionToken")

    if session_token:
        try:
            session = LearnerSession.objects.get(token=session_token)
        except LearnerSession.DoesNotExist:
            return Response({"detail": "Unknown session token."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "task": public_task_payload(get_task(session.current_task_id)),
                "session": session_payload(session),
            }
        )

    module_id, error_response = module_id_or_error(module_id)
    if error_response:
        return error_response
    if direction not in {"forward", "backward"}:
        return Response(
            {"direction": "Direction must be 'forward' or 'backward'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    current_index = task_index(task_id, module_id)
    current_index = current_index - 1 if direction == "backward" else current_index + 1
    return Response(active_task_payload(current_index, module_id))


@extend_schema(
    tags=["learning"],
    summary="Create anonymous learner session",
    request=SessionCreateSerializer,
    responses={201: SessionStateResponseSerializer, 400: ErrorResponseSerializer},
)
@api_view(["POST"])
def sessions(request):
    serializer = SessionCreateSerializer(data=request.data, context={"tasks": TASK_BANK})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    requested_task = get_task(serializer.validated_data.get("taskId", ""))
    task = requested_task or first_task(serializer.validated_data.get("moduleId"))
    session = LearnerSession.objects.create(
        current_module_id=task["moduleId"],
        current_task_id=task["id"],
    )
    return Response(session_payload(session), status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["learning"],
    summary="Get learner session state",
    parameters=[
        OpenApiParameter("session_token", OpenApiTypes.STR, OpenApiParameter.PATH),
    ],
    responses={200: SessionStateResponseSerializer, 404: ErrorResponseSerializer},
)
@api_view(["GET"])
def session_detail(request, session_token):
    try:
        session = LearnerSession.objects.get(token=session_token)
    except LearnerSession.DoesNotExist:
        return Response({"detail": "Unknown session token."}, status=status.HTTP_404_NOT_FOUND)
    return Response(session_payload(session))


@extend_schema(
    tags=["learning"],
    summary="Submit a task response",
    description=(
        "Persists a task submission or explicit skip, derives fuzzy inputs from task metadata, runs the "
        "ANFIS and Mamdani engines, stores the model trace, updates session state, and "
        "returns the next adapted task."
    ),
    request=SubmissionSerializer,
    responses={201: SubmissionResponseSerializer, 400: ErrorResponseSerializer},
)
@api_view(["POST"])
@transaction.atomic
def submissions(request):
    serializer = SubmissionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    session = data["session"]
    task = data["task"]
    elapsed = data["elapsedTimeSeconds"]
    relative_time = elapsed / max(1, task["baselineTimeSeconds"])
    is_correct = correctness_signal(task, data)

    fuzzy_inputs = {
        "taskMetricWeight": task["taskMetricWeight"],
        "historicalGradeAverage": session.aggregate_mastery,
        "relativeResponseTime": relative_time,
        "assistanceInteractions": data["assistanceInteractions"],
        "completionRatio": data["completionRatio"],
        "taskType": task["type"],
        "isCorrect": is_correct,
    }
    fuzzy_result = evaluate_learning_state(fuzzy_inputs)

    submission = TaskSubmission.objects.create(
        session=session,
        task_id=task["id"],
        module_id=task["moduleId"],
        task_type=task["type"],
        difficulty=task["difficulty"],
        difficulty_level=task["difficultyLevel"],
        task_metric_weight=task["taskMetricWeight"],
        baseline_time_seconds=task["baselineTimeSeconds"],
        elapsed_time_seconds=elapsed,
        relative_response_time=relative_time,
        assistance_interactions=data["assistanceInteractions"],
        completion_ratio=data["completionRatio"],
        is_correct=is_correct,
        answer_payload=answer_payload(data),
    )
    FuzzyEvaluationLog.objects.create(
        session=session,
        submission=submission,
        input_snapshot=fuzzy_result["inputSnapshot"],
        engine_trace=fuzzy_result["engineTrace"],
        knowledge_mastery=fuzzy_result["knowledgeMastery"],
        system_cognitive_friction=fuzzy_result["systemCognitiveFriction"],
        focus_state=fuzzy_result["focusState"],
        recommendation=fuzzy_result["recommendation"],
        support_message=fuzzy_result["supportMessage"],
    )

    session.completed_task_count += 1
    session.aggregate_mastery = round((session.aggregate_mastery * 0.65) + (fuzzy_result["knowledgeMastery"] * 0.35), 2)
    session.aggregate_friction = round((session.aggregate_friction * 0.65) + (fuzzy_result["systemCognitiveFriction"] * 0.35), 2)
    session.latest_recommendation = fuzzy_result["recommendation"]

    adaptation_result = select_next_task(session, task, fuzzy_result)
    session.save()

    return Response(
        {
            **fuzzy_result,
            "submissionId": submission.id,
            "session": session_payload(session),
            "nextTask": public_task_payload(adaptation_result["nextTask"]),
            "adaptation": adaptation_result["adaptation"],
            "surveyDue": survey_due(session),
        },
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    tags=["learning"],
    summary="Store a learner micro-survey",
    description="Stores satisfaction, perceived difficulty, and confidence labels for model analysis.",
    request=MicroSurveySerializer,
    responses={201: MicroSurveyResponseSerializer, 400: ErrorResponseSerializer},
)
@api_view(["POST"])
@transaction.atomic
def micro_surveys(request):
    serializer = MicroSurveySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    session = serializer.validated_data["session"]
    latest_submission = session.submissions.order_by("-created_at").first()
    survey = MicroSurveyResponse.objects.create(
        session=session,
        submission=latest_submission,
        satisfaction_score=serializer.validated_data["satisfactionScore"],
        perceived_difficulty=serializer.validated_data["perceivedDifficulty"],
        confidence_score=serializer.validated_data["confidenceScore"],
        milestone_task_count=serializer.validated_data["milestoneTaskCount"],
        comment=serializer.validated_data.get("comment", ""),
    )
    return Response(
        {
            "id": survey.id,
            "sessionToken": session.token,
            "submissionId": latest_submission.id if latest_submission else None,
            "satisfactionScore": survey.satisfaction_score,
            "perceivedDifficulty": survey.perceived_difficulty,
            "confidenceScore": survey.confidence_score,
            "milestoneTaskCount": survey.milestone_task_count,
            "surveyDue": survey_due(session),
        },
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    tags=["learning"],
    summary="Export model training data",
    description=(
        "Exports telemetry rows that can be used to evaluate or retrain the ANFIS model, "
        "including task metadata, timing, assistance, completion, model outputs, and survey labels."
    ),
    responses={200: TrainingDataExportResponseSerializer},
)
@api_view(["GET"])
def training_data_export(request):
    rows = []
    logs = FuzzyEvaluationLog.objects.select_related("submission", "session").order_by("created_at")
    for log in logs:
        submission = log.submission
        survey = submission.micro_surveys.order_by("-created_at").first()
        rows.append(
            {
                "sessionToken": log.session.token,
                "taskId": submission.task_id,
                "moduleId": submission.module_id,
                "taskType": submission.task_type,
                "difficulty": submission.difficulty,
                "difficultyLevel": submission.difficulty_level,
                "taskMetricWeight": submission.task_metric_weight,
                "historicalGradeAverage": log.input_snapshot.get("historicalGradeAverage"),
                "relativeResponseTime": submission.relative_response_time,
                "assistanceInteractions": submission.assistance_interactions,
                "completionRatio": submission.completion_ratio,
                "isCorrect": submission.is_correct,
                "knowledgeMastery": log.knowledge_mastery,
                "systemCognitiveFriction": log.system_cognitive_friction,
                "focusState": log.focus_state,
                "recommendation": log.recommendation,
                "satisfactionScore": survey.satisfaction_score if survey else None,
                "perceivedDifficulty": survey.perceived_difficulty if survey else None,
                "confidenceScore": survey.confidence_score if survey else None,
                "createdAt": log.created_at.isoformat(),
            }
        )
    return Response({"rows": rows, "count": len(rows)})
