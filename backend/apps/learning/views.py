from rest_framework.decorators import api_view
from rest_framework.response import Response


CURRICULUM_MODULES = [
    {
        "id": 1,
        "title": "Basic Control Flow & Loops",
        "concepts": ["if/elif/else", "for loops", "while loops", "nested loops"],
    },
    {
        "id": 2,
        "title": "Core Data Structures",
        "concepts": ["lists", "tuples", "indexing", "slicing", "comprehensions"],
    },
    {
        "id": 3,
        "title": "Fixed-Size Arrays & Memory Allocation",
        "concepts": ["allocation", "contiguous memory", "vectorization"],
    },
    {
        "id": 4,
        "title": "Key-Value Mappings",
        "concepts": ["dictionaries", "sets", "hashing", "O(1) lookup"],
    },
    {
        "id": 5,
        "title": "Object-Oriented Programming",
        "concepts": ["classes", "__init__", "instance methods", "encapsulation"],
    },
    {
        "id": 6,
        "title": "Inheritance & Polymorphism",
        "concepts": ["overriding", "abstract classes", "interfaces", "MRO"],
    },
    {
        "id": 7,
        "title": "Exception Handling & Robust Code Design",
        "concepts": ["try/except/finally", "custom errors", "with statements"],
    },
]


@api_view(["GET"])
def modules(request):
    return Response({"modules": CURRICULUM_MODULES})


@api_view(["GET"])
def next_task(request):
    return Response(
        {
            "id": "m1-mcq-001",
            "moduleId": 1,
            "type": "mcq",
            "difficulty": "foundation",
            "baselineTimeSeconds": 60,
            "prompt": "Which loop is best when the number of iterations is known before execution?",
            "choices": ["for loop", "while loop", "try block", "class constructor"],
        }
    )
