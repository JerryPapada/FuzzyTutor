# FuzzyTutor Fuzzy Engines Analysis

## 1. System Overview

FuzzyTutor uses two cooperating fuzzy engines to personalize programming tasks:

- **ANFIS mastery engine**: estimates `knowledgeMastery`, i.e. how strongly the learner appears to understand the current programming concept.
- **Mamdani cognitive-friction engine**: estimates `systemCognitiveFriction`, i.e. how much strain, hesitation, or support need is visible during the task.

The two outputs are combined by the adaptation controller. The controller returns:

- `focusState`
- `recommendation`
- `supportMessage`
- `nextTask` and adaptation metadata when a learner submits through the learning API

The main endpoint for standalone fuzzy evaluation is:

```text
POST /api/fuzzy/evaluate/
```

The preferred operational flow is:

```text
POST /api/learning/sessions/
POST /api/learning/submissions/
POST /api/learning/micro-surveys/
GET  /api/learning/export/training-data/
```

Swagger/OpenAPI documentation is available at:

```text
http://localhost:8000/api/docs/
http://localhost:8000/api/schema/
http://localhost:8000/api/redoc/
```

## 2. Shared Input Features

The backend task catalog defines task difficulty metadata:

| Difficulty | difficultyLevel | taskMetricWeight | Cognitive Load |
|---|---:|---:|---|
| foundation | 1 | 35 | low |
| intermediate | 2 | 55 | medium |
| advanced | 3 | 75 | high |

The fuzzy engines use the following learner/task features:

| Feature | Meaning | Used By |
|---|---|---|
| `taskMetricWeight` | Numeric task difficulty, derived from task metadata | ANFIS |
| `historicalGradeAverage` | Current session mastery estimate, defaulting to 70 for new sessions | ANFIS |
| `relativeResponseTime` | elapsed time divided by task baseline time | Mamdani |
| `assistanceInteractions` | Number of help/hint/support interactions | Mamdani |
| `completionRatio` | Completion amount from 0 to 1 | ANFIS and Mamdani |
| `taskType` | `mcq` or `code` | ANFIS and Mamdani |
| `isCorrect` | Correctness signal when available; code tasks are completion-based | ANFIS |

For code-writing tasks, the system does not execute arbitrary code. Code submissions are interpreted through completion behavior, timing, assistance, and optional answer metadata.

## 3. Engine 1: Mamdani Cognitive-Friction Model

### Purpose

The Mamdani model estimates how much cognitive friction the learner is experiencing while attempting a task. It is intentionally behavioral: it does not judge code correctness directly. Instead, it focuses on time pressure, assistance, and completion.

### Inputs

| Input | Range | Interpretation |
|---|---:|---|
| `relativeResponseTime` | 0+ | 1.0 means equal to baseline task time |
| `assistanceInteractions` | 0+ | Number of help/hint/support interactions |
| `completionRatio` | 0..1 | How much of the task was completed |
| `taskType` | `mcq`/`code` | Code tasks add moderate baseline workspace load |

### Fuzzy Sets

Time pressure:

| Set | Membership Function |
|---|---|
| low | left shoulder from 0.45 to 0.95 |
| normal | triangle with points 0.65, 1.0, 1.45 |
| high | right shoulder from 1.15 to 2.1 |

Assistance:

| Set | Membership Function |
|---|---|
| low | left shoulder from 0.0 to 1.5 |
| medium | triangle with points 0.5, 2.0, 3.5 |
| high | right shoulder from 2.5 to 5.0 |

Completion:

| Set | Membership Function |
|---|---|
| incomplete | left shoulder from 0.15 to 0.55 |
| partial | triangle with points 0.25, 0.6, 0.95 |
| complete | right shoulder from 0.7 to 1.0 |

### Output Sets and Defuzzification

The output is `systemCognitiveFriction`, clamped to 0..100.

| Consequent | Centroid |
|---|---:|
| low | 15 |
| moderate | 42 |
| high | 72 |
| severe | 92 |

Defuzzification uses a centroid-style weighted average:

```text
friction = sum(rule_strength * consequent_centroid) / sum(rule_strength)
```

### Rule Base

The Mamdani model uses these rules:

| Rule | Condition | Consequent |
|---|---|---|
| `steady_complete` | low time pressure AND low assistance AND complete task | low |
| `normal_complete` | normal time pressure AND complete task | low |
| `minor_delay_or_hint` | normal time with medium assistance OR high time with completion | moderate |
| `partial_progress` | partial completion with normal time or medium assistance | moderate |
| `slow_with_support` | high time and medium/high assistance | high |
| `blocked_incomplete` | incomplete with high time or high assistance | severe |
| `code_workspace_load` | task type is code | moderate, fixed strength 0.35 |

### Example Result

For:

```json
{
  "relativeResponseTime": 1.1,
  "assistanceInteractions": 1,
  "completionRatio": 0.9,
  "taskType": "mcq"
}
```

The Mamdani model produced:

```text
systemCognitiveFriction = 26.25
```

Active rules:

| Rule | Strength | Consequent |
|---|---:|---|
| `normal_complete` | 0.6667 | low |
| `minor_delay_or_hint` | 0.3333 | moderate |
| `partial_progress` | 0.1429 | moderate |

Interpretation: the learner is mostly completing the task normally, but mild assistance/partial-progress signals raise friction slightly above the steady threshold.

## 4. Engine 2: ANFIS Mastery Model

### Purpose

The ANFIS engine estimates `knowledgeMastery`. It predicts a mastery score from task difficulty, prior session mastery, completion, task type, and correctness/completion evidence.

The implementation supports two modes:

- **Fallback rule-weighted ANFIS-style mode** when no trained parameter file exists.
- **Trained ANFIS mode** when `backend/apps/fuzzy/trained/anfis_parameters.json` exists.

The current trained model reports:

```text
modelType = trained_anfis
sampleCount = 180
epochs = 650
learningRate = 0.00002
training loss = 77.4607 -> 32.3729
```

### Inputs

| Input | Meaning |
|---|---|
| `taskMetricWeight` | Task difficulty weight: 35, 55, or 75 |
| `historicalGradeAverage` | Prior/session mastery estimate |
| `completionRatio` | Completion from 0 to 1 |
| `taskType` | MCQ or code |
| `isCorrect` | Boolean correctness when available |

The correctness signal is transformed as:

| Case | correctnessSignal |
|---|---:|
| `isCorrect = true` | 100 |
| `isCorrect = false` | 20 |
| correctness unknown | `45 + completionRatio * 35` |

### Fuzzy Sets

Challenge:

| Set | Membership Function |
|---|---|
| foundation | left shoulder from 35 to 60 |
| intermediate | triangle with points 35, 58, 82 |
| advanced | right shoulder from 65 to 85 |

Historical mastery:

| Set | Membership Function |
|---|---|
| low | left shoulder from 35 to 60 |
| medium | triangle with points 45, 68, 86 |
| high | right shoulder from 72 to 90 |

Completion:

| Set | Membership Function |
|---|---|
| low | left shoulder from 0.2 to 0.65 |
| medium | triangle with points 0.35, 0.7, 0.98 |
| high | right shoulder from 0.75 to 1.0 |

Correctness:

| Set | Membership Function |
|---|---|
| weak | left shoulder from 35 to 65 |
| emerging | triangle with points 45, 70, 90 |
| strong | right shoulder from 75 to 95 |

### ANFIS Rules

The ANFIS model uses five named fuzzy rules:

| Rule | Activation Logic |
|---|---|
| `secure_prior_mastery` | high history AND high completion AND strong correctness |
| `developing_mastery` | medium history with high completion OR high history with emerging correctness |
| `productive_challenge` | advanced challenge AND high completion AND strong correctness |
| `fragile_progress` | medium history with medium completion OR emerging correctness with medium completion |
| `knowledge_gap` | low history with weak correctness OR low completion with weak correctness |

Each rule has a first-order consequent function:

```text
output =
  w_history * historicalGradeAverage
+ w_completion * completionRatioPercent
+ w_correctness * correctnessSignal
+ w_taskWeight * taskMetricWeight
+ w_codePenalty * codePenalty
+ bias
```

The final mastery is the weighted average of active rule outputs:

```text
knowledgeMastery = sum(rule_strength * rule_output) / sum(rule_strength)
```

### Training Dataset

Because real student data is not available yet, the project uses synthetic/bootstrap training data. The generator creates realistic learner profiles:

| Profile | Behavior |
|---|---|
| strong | high history, fast/normal time, high completion, high correctness |
| struggling | low history, slow time, high assistance, low completion |
| improving | medium history, improving completion and correctness |
| overchallenged | medium history but high friction and low confidence |
| fast_incorrect | quick responses but lower correctness |

Each synthetic row contains:

```text
taskMetricWeight
historicalGradeAverage
relativeResponseTime
assistanceInteractions
completionRatio
taskType
isCorrect
confidenceScore
perceivedDifficulty
targetMastery
```

The synthetic target label is:

```text
targetMastery =
  0.42 * correctness
+ 0.24 * completion
+ 0.14 * speed
+ 0.12 * confidence
+ 0.08 * historicalGrade
+ difficulty_adjustment
```

This is used only as a bootstrap target. The same pipeline can later train from real logged student data.

### Training Commands

Seed synthetic data:

```bash
docker compose run --rm backend python manage.py seed_anfis_training_data \
  --count 180 \
  --seed 42 \
  --clear-existing
```

Train ANFIS parameters:

```bash
docker compose run --rm backend python manage.py train_anfis \
  --epochs 650 \
  --min-samples 30
```

Evaluate trained ANFIS:

```bash
docker compose run --rm backend python manage.py evaluate_anfis
```

### Training Results

The current trained parameter file reports:

| Metric | Value |
|---|---:|
| Samples | 180 |
| Epochs | 650 |
| Learning rate | 0.00002 |
| Initial training loss | 77.4607 |
| Final training loss | 32.3729 |

Evaluation results:

| Model | Samples | MAE | RMSE | R2 |
|---|---:|---:|---:|---:|
| Default ANFIS baseline | 180 | 10.498 | 12.574 | 0.719 |
| Trained ANFIS | 180 | 3.861 | 4.909 | 0.957 |

Improvement:

```text
RMSE improvement = 7.665
```

Interpretation: the trained ANFIS model fits the bootstrap training labels substantially better than the default hand-authored weights. This demonstrates that the backend can train and evaluate an ANFIS-style model, while still falling back safely if no trained parameter file exists.

### Example ANFIS Inference

Input:

```json
{
  "taskMetricWeight": 55,
  "historicalGradeAverage": 72,
  "relativeResponseTime": 1.1,
  "assistanceInteractions": 1,
  "completionRatio": 0.9,
  "taskType": "mcq",
  "isCorrect": true
}
```

Output:

```text
knowledgeMastery = 92.81
modelType = trained_anfis
```

Active ANFIS rules:

| Rule | Strength | Output |
|---|---:|---:|
| `developing_mastery` | 0.6000 | 91.7961 |
| `fragile_progress` | 0.2857 | 94.9452 |

Interpretation: the learner has high predicted mastery because correctness is strong, completion is high, and the session history is medium-to-high. The active rules indicate a developing but solid mastery pattern.

## 5. Adaptation Controller

The controller combines both model outputs.

Thresholds:

| Threshold | Value |
|---|---:|
| steady friction max | 25 |
| steady mastery min | 65 |
| support friction max | 55 |
| high mastery min | 75 |
| low mastery max | 45 |

Focus state:

| Condition | focusState |
|---|---|
| friction < 25 and mastery >= 65 | `Focused & Steady` |
| friction < 55 | `Needs Support` |
| otherwise | `Frustrated` |

Recommendation:

| Condition | recommendation |
|---|---|
| mastery >= 75 and friction < 35 | `increase_or_hold_high_tier` |
| mastery < 45 and friction >= 55 | `reduce_difficulty_and_show_support` |
| otherwise | `hold_current_tier` |

The learning adaptation service maps the recommendation to the next task:

| Recommendation/Signal | Direction |
|---|---|
| high mastery and low friction | increase difficulty |
| low mastery or high friction | decrease difficulty |
| mixed signals | hold current difficulty |

The service first tries to select a task in the same module. If no suitable task exists, it falls back to the wider catalog.

## 6. Persistence and Data Collection

The backend stores the data needed for future real ANFIS training:

| Model | Purpose |
|---|---|
| `LearnerSession` | Anonymous session state |
| `TaskSubmission` | Task answer metadata, timing, difficulty, completion, correctness |
| `FuzzyEvaluationLog` | Inputs, outputs, rule trace, recommendation, support text |
| `MicroSurveyResponse` | Satisfaction, perceived difficulty, confidence |

Training/export endpoint:

```text
GET /api/learning/export/training-data/
```

This returns rows containing:

```text
task difficulty
historical grade estimate
response-time ratio
assistance count
completion ratio
correctness
mastery output
friction output
recommendation
survey labels
```

## 7. Summary

FuzzyTutor currently implements two fuzzy engines:

1. **Mamdani cognitive-friction model**
   - Fully rule-based.
   - Uses fuzzy sets, fuzzy rules, and centroid-style defuzzification.
   - Produces interpretable friction scores and active rule traces.

2. **Trainable ANFIS mastery model**
   - Uses fuzzy membership functions and rule activations.
   - Learns consequent parameters through a backend training command.
   - Uses synthetic/bootstrap data initially.
   - Can later train on real learner logs without changing the API design.

Together, these models support personalized educational decisions: the system estimates both what the learner knows and how much friction the learner is experiencing, then adapts task difficulty and support level accordingly.
