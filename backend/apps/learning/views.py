from rest_framework.decorators import api_view
from rest_framework.response import Response


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

TASK_BANK = [
    {
        "id": "lists-mcq-001",
        "moduleId": 1,
        "type": "mcq",
        "difficulty": "foundation",
        "baselineTimeSeconds": 55,
        "prompt": "What does append() do to a Python list?",
        "choices": ["Adds an item to the end", "Deletes the last item", "Sorts the list", "Creates a new tuple"],
        "correctChoice": "Adds an item to the end",
    },
    {
        "id": "lists-code-001",
        "moduleId": 1,
        "type": "code",
        "difficulty": "foundation",
        "baselineTimeSeconds": 75,
        "prompt": "Create a list named evens containing the even numbers from 2 to 8.",
        "starterCode": "evens = []\n",
        "answerGuide": "Use a list literal or build it with a loop/comprehension.",
    },
    {
        "id": "arrays-mcq-001",
        "moduleId": 2,
        "type": "mcq",
        "difficulty": "foundation",
        "baselineTimeSeconds": 60,
        "prompt": "Why can array lookups be fast?",
        "choices": ["They use contiguous memory", "They always sort data", "They avoid indexes", "They duplicate values"],
        "correctChoice": "They use contiguous memory",
    },
    {
        "id": "arrays-code-001",
        "moduleId": 3,
        "type": "code",
        "difficulty": "intermediate",
        "baselineTimeSeconds": 80,
        "prompt": "Store the numbers 10, 20, and 30 in a list called values and print the first item.",
        "starterCode": "values = []\n",
        "answerGuide": "Use values[0] after creating the list.",
    },
    {
        "id": "dicts-mcq-001",
        "moduleId": 3,
        "type": "mcq",
        "difficulty": "intermediate",
        "baselineTimeSeconds": 65,
        "prompt": "What is the main purpose of a dictionary?",
        "choices": ["Store key-value pairs", "Only store integers", "Build inheritance trees", "Measure execution time"],
        "correctChoice": "Store key-value pairs",
    },
    {
        "id": "dicts-code-001",
        "moduleId": 3,
        "type": "code",
        "difficulty": "intermediate",
        "baselineTimeSeconds": 85,
        "prompt": "Create a dictionary named student with keys name and age, then read the name value into result.",
        "starterCode": "student = {}\nresult = ''\n",
        "answerGuide": "Use student['name'] or student.get('name').",
    },
    {
        "id": "classes-mcq-001",
        "moduleId": 4,
        "type": "mcq",
        "difficulty": "intermediate",
        "baselineTimeSeconds": 70,
        "prompt": "What does __init__ usually do in a Python class?",
        "choices": ["Initializes object state", "Deletes the object", "Imports the module", "Creates a loop"],
        "correctChoice": "Initializes object state",
    },
    {
        "id": "classes-code-001",
        "moduleId": 4,
        "type": "code",
        "difficulty": "intermediate",
        "baselineTimeSeconds": 90,
        "prompt": "Create a class named Person with an __init__ that stores a name attribute.",
        "starterCode": "class Person:\n    pass\n",
        "answerGuide": "Define __init__(self, name) and assign self.name = name.",
    },
    {
        "id": "inheritance-mcq-001",
        "moduleId": 5,
        "type": "mcq",
        "difficulty": "advanced",
        "baselineTimeSeconds": 75,
        "prompt": "Which concept lets a subclass replace behavior from its parent class?",
        "choices": ["Overriding", "Indexing", "Hashing", "Slicing"],
        "correctChoice": "Overriding",
    },
    {
        "id": "exceptions-mcq-001",
        "moduleId": 6,
        "type": "mcq",
        "difficulty": "advanced",
        "baselineTimeSeconds": 75,
        "prompt": "Which block runs whether or not an exception happens?",
        "choices": ["finally", "if", "else", "break"],
        "correctChoice": "finally",
    },
    {
        "id": "exceptions-code-001",
        "moduleId": 6,
        "type": "code",
        "difficulty": "advanced",
        "baselineTimeSeconds": 95,
        "prompt": "Wrap a file read in a try/except block and return 'failed' if opening the file raises an error.",
        "starterCode": "def read_name(path):\n    pass\n",
        "answerGuide": "Catch a broad exception only for the example and return the fallback string.",
    },
    {
        "id": "control-mcq-001",
        "moduleId": 7,
        "type": "mcq",
        "difficulty": "foundation",
        "baselineTimeSeconds": 50,
        "prompt": "Which keyword starts a conditional branch in Python?",
        "choices": ["if", "loop", "def", "return"],
        "correctChoice": "if",
    },
    {
        "id": "control-code-001",
        "moduleId": 7,
        "type": "code",
        "difficulty": "foundation",
        "baselineTimeSeconds": 65,
        "prompt": "Write a for loop that prints numbers 1 to 3.",
        "starterCode": "",
        "answerGuide": "Use range(1, 4).",
    },
]


def _module_task_counts():
    counts = {module["id"]: 0 for module in CURRICULUM_MODULES}
    for task in TASK_BANK:
        counts[task["moduleId"]] += 1
    return counts


def _task_index(task_id=None):
    if task_id:
        for index, task in enumerate(TASK_BANK):
            if task["id"] == task_id:
                return index
    return 0


def _active_task_payload(index):
    safe_index = max(0, min(len(TASK_BANK) - 1, index))
    task = TASK_BANK[safe_index]
    return {
        "task": task,
        "position": safe_index,
        "totalTasks": len(TASK_BANK),
        "hasPrevious": safe_index > 0,
        "hasNext": safe_index < len(TASK_BANK) - 1,
    }


@api_view(["GET"])
def modules(request):
    task_counts = _module_task_counts()
    return Response(
        {
            "modules": [
                {**module, "taskCount": task_counts[module["id"]]}
                for module in CURRICULUM_MODULES
            ]
        }
    )


@api_view(["GET"])
def tasks(request):
    index = request.query_params.get("index")
    task_id = request.query_params.get("taskId")

    try:
        task_index = int(index) if index is not None else _task_index(task_id)
    except ValueError:
        task_index = 0

    return Response(
        {
            "tasks": TASK_BANK,
            "activeTask": _active_task_payload(task_index),
        }
    )


@api_view(["GET"])
def next_task(request):
    task_id = request.query_params.get("taskId")
    direction = request.query_params.get("direction", "forward")
    current_index = _task_index(task_id)

    if direction == "backward":
        current_index -= 1
    else:
        current_index += 1

    return Response(_active_task_payload(current_index))
