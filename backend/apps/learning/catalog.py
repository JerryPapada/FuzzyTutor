from collections import Counter

from .content import MODULE_TASKS


DIFFICULTY_META = {
    "foundation": {
        "difficultyLevel": 1,
        "taskMetricWeight": 35,
        "estimatedCognitiveLoad": "low",
    },
    "intermediate": {
        "difficultyLevel": 2,
        "taskMetricWeight": 55,
        "estimatedCognitiveLoad": "medium",
    },
    "advanced": {
        "difficultyLevel": 3,
        "taskMetricWeight": 75,
        "estimatedCognitiveLoad": "high",
    },
}

HINT_LEVEL_META = {
    1: {"kind": "conceptual", "label": "Conceptual cue"},
    2: {"kind": "strategy", "label": "Strategy"},
    3: {"kind": "scaffold", "label": "Scaffold"},
}

CURRICULUM_MODULES = [
    {
        "id": 1,
        "title": "Python Lists",
        "concepts": ["append", "indexing", "slicing", "iteration"],
        "score": 78,
        "aggregateScore": 81,
    },
    {
        "id": 2,
        "title": "Arrays",
        "concepts": ["contiguous storage", "memory layout", "lookup speed"],
        "score": 64,
        "aggregateScore": 68,
    },
    {
        "id": 3,
        "title": "Dictionaries",
        "concepts": ["keys", "values", "lookup", "hashing"],
        "score": 85,
        "aggregateScore": 83,
    },
    {
        "id": 4,
        "title": "Classes",
        "concepts": ["__init__", "methods", "state", "objects"],
        "score": 72,
        "aggregateScore": 76,
    },
    {
        "id": 5,
        "title": "Inheritance",
        "concepts": ["parent class", "override", "subclass"],
        "score": 61,
        "aggregateScore": 66,
    },
    {
        "id": 6,
        "title": "Exceptions",
        "concepts": ["try", "except", "finally", "custom errors"],
        "score": 58,
        "aggregateScore": 63,
    },
    {
        "id": 7,
        "title": "Loops & Control Flow",
        "concepts": ["if", "for", "while", "branching"],
        "score": 89,
        "aggregateScore": 88,
    },
]


def task_definition(
    task_id,
    module_id,
    task_type,
    difficulty,
    baseline_time_seconds,
    prompt,
    concept_tags,
    explanation,
    choices=None,
    correct_choice=None,
    starter_code="",
    answer_guide="",
    hints=None,
):
    hint_texts = [str(text).strip() for text in (hints or [])]
    if len(hint_texts) != len(HINT_LEVEL_META):
        raise ValueError(f"Task {task_id} must define exactly three hint levels.")
    if any(not text for text in hint_texts):
        raise ValueError(f"Task {task_id} contains an empty hint.")
    if len(set(hint_texts)) != len(hint_texts):
        raise ValueError(f"Task {task_id} must define three distinct hints.")
    if difficulty not in DIFFICULTY_META:
        raise ValueError(f"Task {task_id} has an unknown difficulty.")
    if task_type not in {"mcq", "code"}:
        raise ValueError(f"Task {task_id} has an unknown task type.")
    if not str(explanation).strip():
        raise ValueError(f"Task {task_id} must define an explanation.")

    meta = DIFFICULTY_META[difficulty]
    payload = {
        "id": task_id,
        "moduleId": module_id,
        "type": task_type,
        "difficulty": difficulty,
        "difficultyLevel": meta["difficultyLevel"],
        "taskMetricWeight": meta["taskMetricWeight"],
        "estimatedCognitiveLoad": meta["estimatedCognitiveLoad"],
        "baselineTimeSeconds": baseline_time_seconds,
        "prompt": prompt,
        "conceptTags": concept_tags,
        "explanation": str(explanation).strip(),
        "adaptationSignals": {
            "masteryFeature": "taskMetricWeight",
            "frictionFeature": "relativeResponseTime",
            "trainingValue": (
                "captures difficulty, timing, completion, assistance, and correctness context"
            ),
        },
        "hints": [
            {
                "level": level,
                **HINT_LEVEL_META[level],
                "text": text,
            }
            for level, text in enumerate(hint_texts, start=1)
        ],
    }
    if task_type == "mcq":
        choice_values = list(choices or [])
        if len(choice_values) != 4 or len(set(choice_values)) != 4:
            raise ValueError(f"MCQ task {task_id} must define four distinct choices.")
        if correct_choice not in choice_values:
            raise ValueError(f"MCQ task {task_id} has an invalid correct choice.")
        payload["choices"] = choice_values
        payload["correctChoice"] = correct_choice
    else:
        if not str(answer_guide).strip():
            raise ValueError(f"Code task {task_id} must define an answer guide.")
        payload["starterCode"] = starter_code
        payload["answerGuide"] = str(answer_guide).strip()
    return payload


def build_task_bank():
    tasks = []
    for module in CURRICULUM_MODULES:
        tasks.extend(
            task_definition(module_id=module["id"], **definition)
            for definition in MODULE_TASKS[module["id"]]
        )
    return tasks


def validate_task_bank(tasks):
    task_ids = [task["id"] for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("Task ids must be unique.")
    if len(tasks) != 105:
        raise ValueError("The expanded curriculum must contain exactly 105 tasks.")

    expected_type_counts = {
        1: {"mcq": 8, "code": 7},
        2: {"mcq": 7, "code": 8},
        3: {"mcq": 8, "code": 7},
        4: {"mcq": 7, "code": 8},
        5: {"mcq": 8, "code": 7},
        6: {"mcq": 7, "code": 8},
        7: {"mcq": 8, "code": 7},
    }
    for module in CURRICULUM_MODULES:
        module_tasks = [task for task in tasks if task["moduleId"] == module["id"]]
        if len(module_tasks) != 15:
            raise ValueError(f"Module {module['id']} must contain exactly 15 tasks.")
        difficulty_counts = Counter(task["difficulty"] for task in module_tasks)
        if difficulty_counts != Counter(
            {"foundation": 5, "intermediate": 5, "advanced": 5}
        ):
            raise ValueError(f"Module {module['id']} must contain five tasks per difficulty.")
        type_counts = Counter(task["type"] for task in module_tasks)
        if dict(type_counts) != expected_type_counts[module["id"]]:
            raise ValueError(f"Module {module['id']} has an invalid MCQ/code mix.")


TASK_BANK = build_task_bank()
validate_task_bank(TASK_BANK)
TASK_BY_ID = {task["id"]: task for task in TASK_BANK}


def public_task_payload(task):
    """Return task data safe to expose before a learner submits an answer."""
    if task is None:
        return None
    return {
        key: value
        for key, value in task.items()
        if key not in {"correctChoice", "answerGuide", "explanation", "hints"}
    }


def review_task_payload(task):
    """Return private answer material only after the task has been attempted."""
    payload = {
        **public_task_payload(task),
        "explanation": task["explanation"],
    }
    if task["type"] == "mcq":
        payload["correctChoice"] = task["correctChoice"]
    else:
        payload["answerGuide"] = task["answerGuide"]
    return payload


def module_task_counts():
    return {
        module["id"]: len(tasks_for_module(module["id"]))
        for module in CURRICULUM_MODULES
    }


def module_task_counts_by_difficulty():
    return {
        module["id"]: dict(
            Counter(task["difficulty"] for task in tasks_for_module(module["id"]))
        )
        for module in CURRICULUM_MODULES
    }


def task_index(task_id=None, module_id=None):
    module_tasks = tasks_for_module(module_id) if module_id is not None else TASK_BANK
    if task_id:
        for index, task in enumerate(module_tasks):
            if task["id"] == task_id:
                return index
    return 0


def get_task(task_id):
    return TASK_BY_ID.get(task_id)


def first_task(module_id=None):
    module_tasks = tasks_for_module(module_id)
    return module_tasks[0] if module_tasks else TASK_BANK[0]


def tasks_for_module(module_id):
    if module_id is None:
        return TASK_BANK
    return [task for task in TASK_BANK if task["moduleId"] == int(module_id)]


def active_task_payload(index, module_id=None):
    module_tasks = tasks_for_module(module_id)
    if not module_tasks:
        return {
            "task": None,
            "position": 0,
            "totalTasks": 0,
            "hasPrevious": False,
            "hasNext": False,
        }
    safe_index = max(0, min(len(module_tasks) - 1, index))
    return {
        "task": public_task_payload(module_tasks[safe_index]),
        "position": safe_index,
        "totalTasks": len(module_tasks),
        "hasPrevious": safe_index > 0,
        "hasNext": safe_index < len(module_tasks) - 1,
    }
