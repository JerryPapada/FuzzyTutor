import json
import random
from pathlib import Path
from django.conf import settings
from .utils import clamp


RULE_NAMES = [
    "secure_prior_mastery",
    "developing_mastery",
    "productive_challenge",
    "fragile_progress",
    "knowledge_gap",
]

DEFAULT_CONSEQUENT_WEIGHTS = {
    "secure_prior_mastery": {
        "historicalGradeAverage": 0.48,
        "completionRatio": 0.22,
        "correctnessSignal": 0.22,
        "taskMetricWeight": 0.08,
        "codePenalty": -1.0,
        "bias": 0.0,
    },
    "developing_mastery": {
        "historicalGradeAverage": 0.52,
        "completionRatio": 0.24,
        "correctnessSignal": 0.18,
        "taskMetricWeight": 0.06,
        "codePenalty": -1.0,
        "bias": 0.0,
    },
    "productive_challenge": {
        "historicalGradeAverage": 0.42,
        "completionRatio": 0.23,
        "correctnessSignal": 0.25,
        "taskMetricWeight": 0.10,
        "codePenalty": -1.0,
        "bias": 0.0,
    },
    "fragile_progress": {
        "historicalGradeAverage": 0.58,
        "completionRatio": 0.23,
        "correctnessSignal": 0.15,
        "taskMetricWeight": 0.04,
        "codePenalty": -1.0,
        "bias": 0.0,
    },
    "knowledge_gap": {
        "historicalGradeAverage": 0.60,
        "completionRatio": 0.20,
        "correctnessSignal": 0.16,
        "taskMetricWeight": 0.04,
        "codePenalty": -1.0,
        "bias": 0.0,
    },
}

FEATURE_NAMES = [
    "historicalGradeAverage",
    "completionRatio",
    "correctnessSignal",
    "taskMetricWeight",
    "codePenalty",
    "bias",
]

# paths
def default_parameters_path():
    return Path(settings.BASE_DIR) / "apps" / "fuzzy" / "trained" / "anfis_parameters.json"

# load trained model parameters
def load_trained_parameters(path=None):
    parameter_path = Path(path) if path else default_parameters_path()
    if not parameter_path.exists():
        return None
    with parameter_path.open("r", encoding="utf-8") as parameter_file:
        return json.load(parameter_file)

# save trained model parameters
def save_trained_parameters(parameters, path=None):
    parameter_path = Path(path) if path else default_parameters_path()
    parameter_path.parent.mkdir(parents=True, exist_ok=True)
    with parameter_path.open("w", encoding="utf-8") as parameter_file:
        json.dump(parameters, parameter_file, indent=2, sort_keys=True)
    return parameter_path

# generate feature vector for a given task
def feature_vector(task_weight, historical_grade, completion_ratio, correctness_score, task_type):
    code_penalty = 3.0 if str(task_type).lower() == "code" and completion_ratio < 1 else 0.0
    return {
        "historicalGradeAverage": clamp(historical_grade),
        "completionRatio": clamp(completion_ratio, 0.0, 1.0) * 100.0,
        "correctnessSignal": clamp(correctness_score),
        "taskMetricWeight": clamp(task_weight),
        "codePenalty": code_penalty,
        "bias": 1.0,
    }

# compute the consequent output for a given rule and feature vector
def consequent_output(weights, features):
    return clamp(sum(weights[name] * features[name] for name in FEATURE_NAMES))

# compute a synthetic target mastery score based on input features
def synthetic_target_mastery(row):
    speed_score = clamp(100.0 - abs(float(row["relativeResponseTime"]) - 1.0) * 35.0)
    confidence = clamp((float(row.get("confidenceScore") or 3) - 1.0) * 25.0)
    perceived_difficulty = float(row.get("perceivedDifficulty") or 3)
    difficulty_bonus = (4.0 - perceived_difficulty) * 3.0
    correctness = 100.0 if row["isCorrect"] else 20.0
    target = (
        0.42 * correctness
        + 0.24 * float(row["completionRatio"]) * 100.0
        + 0.14 * speed_score
        + 0.12 * confidence
        + 0.08 * float(row["historicalGradeAverage"])
        + difficulty_bonus
    )
    return clamp(target)

# generate synthetic training data rows for ANFIS model training
def generate_synthetic_training_rows(count=180, seed=42):
    rng = random.Random(seed)
    profiles = [
        {
            "name": "strong",
            "history": (78, 96),
            "time": (0.65, 1.05),
            "assistance": (0, 1),
            "completion": (0.85, 1.0),
            "correct_probability": 0.9,
            "confidence": (4, 5),
            "difficulty": (2, 4),
        },
        {
            "name": "struggling",
            "history": (25, 55),
            "time": (1.25, 2.4),
            "assistance": (3, 6),
            "completion": (0.15, 0.75),
            "correct_probability": 0.25,
            "confidence": (1, 3),
            "difficulty": (4, 5),
        },
        {
            "name": "improving",
            "history": (48, 75),
            "time": (0.9, 1.45),
            "assistance": (1, 3),
            "completion": (0.55, 1.0),
            "correct_probability": 0.62,
            "confidence": (3, 4),
            "difficulty": (2, 4),
        },
        {
            "name": "overchallenged",
            "history": (55, 78),
            "time": (1.5, 2.7),
            "assistance": (3, 7),
            "completion": (0.25, 0.8),
            "correct_probability": 0.35,
            "confidence": (1, 3),
            "difficulty": (4, 5),
        },
        {
            "name": "fast_incorrect",
            "history": (45, 82),
            "time": (0.35, 0.8),
            "assistance": (0, 1),
            "completion": (0.7, 1.0),
            "correct_probability": 0.38,
            "confidence": (2, 4),
            "difficulty": (2, 5),
        },
    ]
    task_weights = [35.0, 55.0, 75.0]
    rows = []
    for index in range(count):
        profile = profiles[index % len(profiles)]
        is_correct = rng.random() < profile["correct_probability"]
        row = {
            "syntheticProfile": profile["name"],
            "taskMetricWeight": rng.choice(task_weights),
            "historicalGradeAverage": round(rng.uniform(*profile["history"]), 2),
            "relativeResponseTime": round(rng.uniform(*profile["time"]), 2),
            "assistanceInteractions": rng.randint(*profile["assistance"]),
            "completionRatio": round(rng.uniform(*profile["completion"]), 2),
            "taskType": rng.choice(["mcq", "code"]),
            "isCorrect": is_correct,
            "confidenceScore": rng.randint(*profile["confidence"]),
            "perceivedDifficulty": rng.randint(*profile["difficulty"]),
        }
        row["targetMastery"] = round(synthetic_target_mastery(row), 2)
        rows.append(row)
    return rows

# Train the consequent parameters of the ANFIS model
def train_consequent_parameters(samples, initial_weights=None, epochs=650, learning_rate=0.00002):
    weights = json.loads(json.dumps(initial_weights or DEFAULT_CONSEQUENT_WEIGHTS))
    losses = []
    for _epoch in range(epochs):
        total_loss = 0.0
        for sample in samples:
            features = sample["features"]
            strengths = sample["ruleStrengths"]
            target = sample["targetMastery"]
            active_total = sum(strengths.values())
            if active_total <= 0:
                continue
            outputs = {
                rule_name: consequent_output(weights[rule_name], features)
                for rule_name in RULE_NAMES
            }
            prediction = sum(strengths[name] * outputs[name] for name in RULE_NAMES) / active_total
            error = prediction - target
            total_loss += error * error
            for rule_name in RULE_NAMES:
                influence = strengths[rule_name] / active_total
                for feature_name in FEATURE_NAMES:
                    gradient = 2.0 * error * influence * features[feature_name]
                    weights[rule_name][feature_name] -= learning_rate * gradient
        losses.append(total_loss / max(1, len(samples)))
    return weights, losses

# Predict the mastery score for a given sample
def predict_sample_mastery(sample, consequent_weights):
    strengths = sample["ruleStrengths"]
    active_total = sum(strengths.values())
    if active_total <= 0:
        return consequent_output(
            consequent_weights["developing_mastery"],
            sample["features"],
        )
    outputs = {
        rule_name: consequent_output(consequent_weights[rule_name], sample["features"])
        for rule_name in RULE_NAMES
    }
    return sum(strengths[name] * outputs[name] for name in RULE_NAMES) / active_total

# Compute regression metrics for a set of targets and predictions
def regression_metrics(targets, predictions):
    count = len(targets)
    if count == 0:
        return {
            "count": 0,
            "mae": 0.0,
            "rmse": 0.0,
            "r2": 0.0,
        }
    errors = [prediction - target for target, prediction in zip(targets, predictions)]
    mae = sum(abs(error) for error in errors) / count
    mse = sum(error * error for error in errors) / count
    mean_target = sum(targets) / count
    total_variance = sum((target - mean_target) ** 2 for target in targets)
    residual_variance = sum(error * error for error in errors)
    r2 = 1.0 - (residual_variance / total_variance) if total_variance > 0 else 0.0
    return {
        "count": count,
        "mae": mae,
        "rmse": mse ** 0.5,
        "r2": r2,
    }
