def mcq(
    task_id,
    difficulty,
    baseline_time_seconds,
    prompt,
    concept_tags,
    choices,
    correct_choice,
    explanation,
    hints,
):
    return {
        "task_id": task_id,
        "task_type": "mcq",
        "difficulty": difficulty,
        "baseline_time_seconds": baseline_time_seconds,
        "prompt": prompt,
        "concept_tags": concept_tags,
        "choices": choices,
        "correct_choice": correct_choice,
        "explanation": explanation,
        "hints": hints,
    }


def code(
    task_id,
    difficulty,
    baseline_time_seconds,
    prompt,
    concept_tags,
    starter_code,
    answer_guide,
    explanation,
    hints,
):
    return {
        "task_id": task_id,
        "task_type": "code",
        "difficulty": difficulty,
        "baseline_time_seconds": baseline_time_seconds,
        "prompt": prompt,
        "concept_tags": concept_tags,
        "starter_code": starter_code,
        "answer_guide": answer_guide,
        "explanation": explanation,
        "hints": hints,
    }
