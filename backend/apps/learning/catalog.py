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
    choices=None,
    correct_choice=None,
    starter_code="",
    answer_guide="",
    hints=None,
):
    hint_texts = list(hints or [])
    if len(hint_texts) != len(HINT_LEVEL_META):
        raise ValueError(f"Task {task_id} must define exactly three hint levels.")
    if any(not str(text).strip() for text in hint_texts):
        raise ValueError(f"Task {task_id} contains an empty hint.")

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
        "hints": [
            {
                "level": level,
                **HINT_LEVEL_META[level],
                "text": str(text).strip(),
            }
            for level, text in enumerate(hint_texts, start=1)
        ],
    }
    if task_type == "mcq":
        payload["choices"] = choices or []
        payload["correctChoice"] = correct_choice
    else:
        payload["starterCode"] = starter_code
        payload["answerGuide"] = answer_guide
    return payload


TASK_BANK = [
    task_definition(
        "lists-mcq-001",
        1,
        "mcq",
        "foundation",
        55,
        "What does append() do to a Python list?",
        ["append", "mutation"],
        ["Adds an item to the end", "Deletes the last item", "Sorts the list", "Creates a new tuple"],
        "Adds an item to the end",
        hints=[
            "Think about whether append() mutates the existing list or creates a different collection.",
            "After calling the method with one value, the list length grows by exactly one.",
            "For items = [1, 2], items.append(3) makes items[-1] equal to 3.",
        ],
    ),
    task_definition(
        "lists-code-001",
        1,
        "code",
        "foundation",
        75,
        "Create a list named evens containing the even numbers from 2 to 8.",
        ["list literal", "sequence"],
        starter_code="evens = []\n",
        answer_guide="Use a list literal or build it with a loop/comprehension.",
        hints=[
            "An even number is divisible by 2; include the requested endpoints 2 and 8.",
            "You can write the four values directly or use range() with a step of 2.",
            "A useful scaffold is evens = list(range(__, __, __)); remember that range's stop is exclusive.",
        ],
    ),
    task_definition(
        "lists-code-002",
        1,
        "code",
        "intermediate",
        95,
        "Build a list named squares with the squares of numbers 1 through 5.",
        ["iteration", "comprehension"],
        starter_code="squares = []\n",
        answer_guide="A loop or list comprehension can produce [1, 4, 9, 16, 25].",
        hints=[
            "The square of a number n is n * n.",
            "Iterate from 1 through 5; if you use range(), its stop value is excluded.",
            "Complete this scaffold: squares = [n * n for n in range(__, __)].",
        ],
    ),
    task_definition(
        "arrays-mcq-001",
        2,
        "mcq",
        "foundation",
        60,
        "Why can array lookups be fast?",
        ["memory layout", "indexing"],
        ["They use contiguous memory", "They always sort data", "They avoid indexes", "They duplicate values"],
        "They use contiguous memory",
        hints=[
            "Think about how an index can identify a physical position rather than searching each value.",
            "With a predictable layout, an element address can be computed from a base address and an offset.",
            "Choose the property that lets index i be located directly from fixed-size neighboring positions.",
        ],
    ),
    task_definition(
        "arrays-code-001",
        2,
        "code",
        "intermediate",
        80,
        "Store the numbers 10, 20, and 30 in a list called values and print the first item.",
        ["array access", "indexing"],
        starter_code="values = []\n",
        answer_guide="Use values[0] after creating the list.",
        hints=[
            "Python sequences use zero-based indexing, so the first position has index 0.",
            "Create the values in their stated order, then pass the indexed first element to print().",
            "Complete the structure: values = [__, __, __] followed by print(values[__]).",
        ],
    ),
    task_definition(
        "arrays-mcq-002",
        2,
        "mcq",
        "advanced",
        80,
        "Which operation is usually expensive for a fixed-size array?",
        ["insertion cost", "memory shift"],
        ["Inserting at the front", "Reading by index", "Checking length", "Reading the last value"],
        "Inserting at the front",
        hints=[
            "Compare operations that only inspect existing data with operations that change element positions.",
            "Making space near the beginning can require many later elements to move.",
            "Choose the operation that may shift almost every existing element by one position.",
        ],
    ),
    task_definition(
        "dicts-mcq-001",
        3,
        "mcq",
        "foundation",
        60,
        "What is the main purpose of a dictionary?",
        ["keys", "values"],
        ["Store key-value pairs", "Only store integers", "Build inheritance trees", "Measure execution time"],
        "Store key-value pairs",
        hints=[
            "A dictionary associates one piece of information with another for lookup.",
            "Its entries are written as key: value and accessed through the key.",
            "Choose the description of a mapping, rather than a restriction on one data type.",
        ],
    ),
    task_definition(
        "dicts-code-001",
        3,
        "code",
        "intermediate",
        85,
        "Create a dictionary named student with keys name and age, then read the name value into result.",
        ["dictionary access", "keys"],
        starter_code="student = {}\nresult = ''\n",
        answer_guide="Use student['name'] or student.get('name').",
        hints=[
            "Build the dictionary with the requested words as keys, then retrieve a value through its key.",
            "A dictionary literal uses {key: value}; square brackets can then access a known key.",
            "Use this shape: student = {'name': __, 'age': __} and result = student[__].",
        ],
    ),
    task_definition(
        "dicts-code-002",
        3,
        "code",
        "advanced",
        105,
        "Count how many times each word appears in words and store the result in counts.",
        ["aggregation", "hash lookup"],
        starter_code="words = ['a', 'b', 'a']\ncounts = {}\n",
        answer_guide="Loop over words and increment counts[word].",
        hints=[
            "Treat each word as a dictionary key and its number of appearances as the value.",
            "For each word, read its current count with a default of zero, then add one.",
            "Complete the loop body: counts[word] = counts.get(word, __) + __.",
        ],
    ),
    task_definition(
        "classes-mcq-001",
        4,
        "mcq",
        "foundation",
        65,
        "What does __init__ usually do in a Python class?",
        ["constructor", "object state"],
        ["Initializes object state", "Deletes the object", "Imports the module", "Creates a loop"],
        "Initializes object state",
        hints=[
            "Consider when __init__ runs in relation to creating an instance.",
            "Its self parameter refers to the new object, allowing attributes to be assigned.",
            "Choose the option describing preparation of the new object's stored data.",
        ],
    ),
    task_definition(
        "classes-code-001",
        4,
        "code",
        "intermediate",
        90,
        "Create a class named Person with an __init__ that stores a name attribute.",
        ["class", "instance attribute"],
        starter_code="class Person:\n    pass\n",
        answer_guide="Define __init__(self, name) and assign self.name = name.",
        hints=[
            "The constructor method receives the new instance as self plus the supplied name.",
            "Store an instance attribute by assigning to self.name inside __init__.",
            "Use this scaffold: def __init__(self, name): followed by self.name = __.",
        ],
    ),
    task_definition(
        "classes-code-002",
        4,
        "code",
        "advanced",
        115,
        "Add a greet method to Person that returns 'Hello, ' followed by the stored name.",
        ["methods", "state"],
        starter_code="class Person:\n    def __init__(self, name):\n        self.name = name\n",
        answer_guide="Define greet(self) and return a string using self.name.",
        hints=[
            "An instance method can read the name already stored on self.",
            "Define greet with self, then return a string formed from the greeting and self.name.",
            "Complete: def greet(self): return 'Hello, ' + ____.",
        ],
    ),
    task_definition(
        "inheritance-mcq-001",
        5,
        "mcq",
        "foundation",
        65,
        "What is a subclass?",
        ["subclass", "parent class"],
        ["A class based on another class", "A loop inside a class", "A dictionary key", "A syntax error"],
        "A class based on another class",
        hints=[
            "Think about the relationship created when one class inherits from another.",
            "The new class can reuse or specialize attributes and methods from its parent.",
            "Choose the option describing a class derived from an existing class.",
        ],
    ),
    task_definition(
        "inheritance-mcq-002",
        5,
        "mcq",
        "intermediate",
        75,
        "Which concept lets a subclass replace behavior from its parent class?",
        ["override", "polymorphism"],
        ["Overriding", "Indexing", "Hashing", "Slicing"],
        "Overriding",
        hints=[
            "The question asks about redefining inherited behavior in the child class.",
            "This happens when the subclass declares a method with the same name as the parent's method.",
            "Choose the object-oriented term for replacing an inherited method implementation.",
        ],
    ),
    task_definition(
        "inheritance-code-001",
        5,
        "code",
        "advanced",
        120,
        "Create a Dog subclass of Animal that overrides speak to return 'woof'.",
        ["inheritance", "override"],
        starter_code="class Animal:\n    def speak(self):\n        return 'sound'\n",
        answer_guide="Define class Dog(Animal) and override speak.",
        hints=[
            "Place the parent class name in parentheses after the subclass name.",
            "Inside Dog, define a speak method with the same signature as Animal.speak.",
            "Complete the scaffold: class Dog(__): def speak(self): return __.",
        ],
    ),
    task_definition(
        "exceptions-mcq-001",
        6,
        "mcq",
        "foundation",
        65,
        "Which block runs whether or not an exception happens?",
        ["finally", "control flow"],
        ["finally", "if", "else", "break"],
        "finally",
        hints=[
            "Look for the exception-handling block intended for cleanup work.",
            "This block is entered after try/except processing whether an exception was raised or not.",
            "Choose the keyword paired with try/except that guarantees cleanup execution.",
        ],
    ),
    task_definition(
        "exceptions-code-001",
        6,
        "code",
        "intermediate",
        95,
        "Wrap a file read in a try/except block and return 'failed' if opening the file raises an error.",
        ["try", "except"],
        starter_code="def read_name(path):\n    pass\n",
        answer_guide="Catch the error and return the fallback string.",
        hints=[
            "The operation that may fail belongs in try, while the fallback belongs in except.",
            "Open and read the file inside try; return the requested fallback string from the handler.",
            "Use this structure: try: return open(path).read(); except OSError: return ____.",
        ],
    ),
    task_definition(
        "exceptions-code-002",
        6,
        "code",
        "advanced",
        115,
        "Raise ValueError when age is below zero, otherwise return age.",
        ["raise", "validation"],
        starter_code="def validate_age(age):\n    pass\n",
        answer_guide="Use if age < 0: raise ValueError(...).",
        hints=[
            "Validate the invalid case before returning the ordinary result.",
            "Use a comparison against zero and the raise statement to create ValueError.",
            "Complete: if age < __: raise ValueError(...); return age.",
        ],
    ),
    task_definition(
        "control-mcq-001",
        7,
        "mcq",
        "foundation",
        50,
        "Which keyword starts a conditional branch in Python?",
        ["if", "branching"],
        ["if", "loop", "def", "return"],
        "if",
        hints=[
            "A conditional branch evaluates a Boolean expression before choosing a path.",
            "In Python, the relevant statement is followed by a condition and a colon.",
            "Choose the keyword used in the pattern: ___ condition:.",
        ],
    ),
    task_definition(
        "control-code-001",
        7,
        "code",
        "intermediate",
        65,
        "Write a for loop that prints numbers 1 to 3.",
        ["for loop", "range"],
        starter_code="",
        answer_guide="Use range(1, 4).",
        hints=[
            "A for loop can consume the sequence of integers produced by range().",
            "Start at 1 and use an exclusive stop one greater than the last number to print.",
            "Complete: for number in range(__, __): print(number).",
        ],
    ),
    task_definition(
        "control-code-002",
        7,
        "code",
        "advanced",
        100,
        "Loop over numbers and store only values greater than 10 in result.",
        ["filtering", "conditionals"],
        starter_code="numbers = [4, 12, 9, 18]\nresult = []\n",
        answer_guide="Use an if statement inside a loop.",
        hints=[
            "Visit every number, but append only those satisfying the threshold condition.",
            "Put an if statement inside the loop and compare each number with 10.",
            "Complete: for number in numbers: if number > __: result.append(__).",
        ],
    ),
]


def public_task_payload(task):
    """Return task data safe to expose before a learner submits an answer."""
    if task is None:
        return None
    return {
        key: value
        for key, value in task.items()
        if key not in {"correctChoice", "answerGuide", "hints"}
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
