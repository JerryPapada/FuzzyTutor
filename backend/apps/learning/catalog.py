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


def _task(
    task_id,
    module_id,
    task_type,
    difficulty,
    baseline_time_seconds,
    prompt,
    concept_tags,
    choices=None,
    correct_choice=None,
    starter_code="",
    answer_guide="",
):
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
        "adaptationSignals": {
            "masteryFeature": "taskMetricWeight",
            "frictionFeature": "relativeResponseTime",
            "trainingValue": "captures difficulty, timing, completion, assistance, and correctness context",
        },
    }
    if task_type == "mcq":
        payload["choices"] = choices or []
        payload["correctChoice"] = correct_choice
    else:
        payload["starterCode"] = starter_code
        payload["answerGuide"] = answer_guide
    return payload


TASK_BANK = [
    _task(
        "lists-mcq-001",
        1,
        "mcq",
        "foundation",
        55,
        "What does append() do to a Python list?",
        ["append", "mutation"],
        ["Adds an item to the end", "Deletes the last item", "Sorts the list", "Creates a new tuple"],
        "Adds an item to the end",
    ),
    _task(
        "lists-code-001",
        1,
        "code",
        "foundation",
        75,
        "Create a list named evens containing the even numbers from 2 to 8.",
        ["list literal", "sequence"],
        starter_code="evens = []\n",
        answer_guide="Use a list literal or build it with a loop/comprehension.",
    ),
    _task(
        "lists-code-002",
        1,
        "code",
        "intermediate",
        95,
        "Build a list named squares with the squares of numbers 1 through 5.",
        ["iteration", "comprehension"],
        starter_code="squares = []\n",
        answer_guide="A loop or list comprehension can produce [1, 4, 9, 16, 25].",
    ),
    _task(
        "arrays-mcq-001",
        2,
        "mcq",
        "foundation",
        60,
        "Why can array lookups be fast?",
        ["memory layout", "indexing"],
        ["They use contiguous memory", "They always sort data", "They avoid indexes", "They duplicate values"],
        "They use contiguous memory",
    ),
    _task(
        "arrays-code-001",
        2,
        "code",
        "intermediate",
        80,
        "Store the numbers 10, 20, and 30 in a list called values and print the first item.",
        ["array access", "indexing"],
        starter_code="values = []\n",
        answer_guide="Use values[0] after creating the list.",
    ),
    _task(
        "arrays-mcq-002",
        2,
        "mcq",
        "advanced",
        80,
        "Which operation is usually expensive for a fixed-size array?",
        ["insertion cost", "memory shift"],
        ["Inserting at the front", "Reading by index", "Checking length", "Reading the last value"],
        "Inserting at the front",
    ),
    _task(
        "dicts-mcq-001",
        3,
        "mcq",
        "foundation",
        60,
        "What is the main purpose of a dictionary?",
        ["keys", "values"],
        ["Store key-value pairs", "Only store integers", "Build inheritance trees", "Measure execution time"],
        "Store key-value pairs",
    ),
    _task(
        "dicts-code-001",
        3,
        "code",
        "intermediate",
        85,
        "Create a dictionary named student with keys name and age, then read the name value into result.",
        ["dictionary access", "keys"],
        starter_code="student = {}\nresult = ''\n",
        answer_guide="Use student['name'] or student.get('name').",
    ),
    _task(
        "dicts-code-002",
        3,
        "code",
        "advanced",
        105,
        "Count how many times each word appears in words and store the result in counts.",
        ["aggregation", "hash lookup"],
        starter_code="words = ['a', 'b', 'a']\ncounts = {}\n",
        answer_guide="Loop over words and increment counts[word].",
    ),
    _task(
        "classes-mcq-001",
        4,
        "mcq",
        "foundation",
        65,
        "What does __init__ usually do in a Python class?",
        ["constructor", "object state"],
        ["Initializes object state", "Deletes the object", "Imports the module", "Creates a loop"],
        "Initializes object state",
    ),
    _task(
        "classes-code-001",
        4,
        "code",
        "intermediate",
        90,
        "Create a class named Person with an __init__ that stores a name attribute.",
        ["class", "instance attribute"],
        starter_code="class Person:\n    pass\n",
        answer_guide="Define __init__(self, name) and assign self.name = name.",
    ),
    _task(
        "classes-code-002",
        4,
        "code",
        "advanced",
        115,
        "Add a greet method to Person that returns 'Hello, ' followed by the stored name.",
        ["methods", "state"],
        starter_code="class Person:\n    def __init__(self, name):\n        self.name = name\n",
        answer_guide="Define greet(self) and return a string using self.name.",
    ),
    _task(
        "inheritance-mcq-001",
        5,
        "mcq",
        "foundation",
        65,
        "What is a subclass?",
        ["subclass", "parent class"],
        ["A class based on another class", "A loop inside a class", "A dictionary key", "A syntax error"],
        "A class based on another class",
    ),
    _task(
        "inheritance-mcq-002",
        5,
        "mcq",
        "intermediate",
        75,
        "Which concept lets a subclass replace behavior from its parent class?",
        ["override", "polymorphism"],
        ["Overriding", "Indexing", "Hashing", "Slicing"],
        "Overriding",
    ),
    _task(
        "inheritance-code-001",
        5,
        "code",
        "advanced",
        120,
        "Create a Dog subclass of Animal that overrides speak to return 'woof'.",
        ["inheritance", "override"],
        starter_code="class Animal:\n    def speak(self):\n        return 'sound'\n",
        answer_guide="Define class Dog(Animal) and override speak.",
    ),
    _task(
        "exceptions-mcq-001",
        6,
        "mcq",
        "foundation",
        65,
        "Which block runs whether or not an exception happens?",
        ["finally", "control flow"],
        ["finally", "if", "else", "break"],
        "finally",
    ),
    _task(
        "exceptions-code-001",
        6,
        "code",
        "intermediate",
        95,
        "Wrap a file read in a try/except block and return 'failed' if opening the file raises an error.",
        ["try", "except"],
        starter_code="def read_name(path):\n    pass\n",
        answer_guide="Catch the error and return the fallback string.",
    ),
    _task(
        "exceptions-code-002",
        6,
        "code",
        "advanced",
        115,
        "Raise ValueError when age is below zero, otherwise return age.",
        ["raise", "validation"],
        starter_code="def validate_age(age):\n    pass\n",
        answer_guide="Use if age < 0: raise ValueError(...).",
    ),
    _task(
        "control-mcq-001",
        7,
        "mcq",
        "foundation",
        50,
        "Which keyword starts a conditional branch in Python?",
        ["if", "branching"],
        ["if", "loop", "def", "return"],
        "if",
    ),
    _task(
        "control-code-001",
        7,
        "code",
        "intermediate",
        65,
        "Write a for loop that prints numbers 1 to 3.",
        ["for loop", "range"],
        starter_code="",
        answer_guide="Use range(1, 4).",
    ),
    _task(
        "control-code-002",
        7,
        "code",
        "advanced",
        100,
        "Loop over numbers and store only values greater than 10 in result.",
        ["filtering", "conditionals"],
        starter_code="numbers = [4, 12, 9, 18]\nresult = []\n",
        answer_guide="Use an if statement inside a loop.",
    ),
]


def public_task_payload(task):
    """Return task data safe to expose before a learner submits an answer."""
    if task is None:
        return None
    return {
        key: value
        for key, value in task.items()
        if key not in {"correctChoice", "answerGuide"}
    }


def module_task_counts():
    counts = {module["id"]: 0 for module in CURRICULUM_MODULES}
    for task in TASK_BANK:
        counts[task["moduleId"]] += 1
    return counts


def module_task_counts_by_difficulty():
    counts = {
        module["id"]: {"foundation": 0, "intermediate": 0, "advanced": 0}
        for module in CURRICULUM_MODULES
    }
    for task in TASK_BANK:
        counts[task["moduleId"]][task["difficulty"]] += 1
    return counts


def task_index(task_id=None, module_id=None):
    tasks = tasks_for_module(module_id) if module_id is not None else TASK_BANK
    if task_id:
        for index, task in enumerate(tasks):
            if task["id"] == task_id:
                return index
    return 0


def get_task(task_id):
    for task in TASK_BANK:
        if task["id"] == task_id:
            return task
    return None


def first_task(module_id=None):
    tasks = tasks_for_module(module_id)
    return tasks[0] if tasks else TASK_BANK[0]


def tasks_for_module(module_id):
    if module_id is None:
        return TASK_BANK
    return [task for task in TASK_BANK if task["moduleId"] == int(module_id)]


def active_task_payload(index, module_id=None):
    tasks = tasks_for_module(module_id)
    if not tasks:
        return {
            "task": None,
            "position": 0,
            "totalTasks": 0,
            "hasPrevious": False,
            "hasNext": False,
        }
    safe_index = max(0, min(len(tasks) - 1, index))
    task = public_task_payload(tasks[safe_index])
    return {
        "task": task,
        "position": safe_index,
        "totalTasks": len(tasks),
        "hasPrevious": safe_index > 0,
        "hasNext": safe_index < len(tasks) - 1,
    }
