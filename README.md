# FuzzyTutor

MSc assignment project for Fuzzy Systems and User Experience / Artificial Intelligence.

FuzzyTutor is a decoupled Django + React platform for adaptive programming education. It is designed around two fuzzy-logic dimensions:

- ANFIS cognitive assessment for predicted knowledge mastery.
- Mamdani fuzzy inference for behavioral engagement and cognitive friction.

## Run With Docker

```bash
docker compose up --build
```

Services:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api
- Health check: http://localhost:8000/api/health/

## Backend Workflow

- Create or restore an anonymous learner session through `/api/learning/sessions/`.
- Load the seven-module task catalog through `/api/learning/modules/` and `/api/learning/tasks/`.
- Reveal up to three progressive, server-persisted hints through `/api/learning/hints/`.
- Submit the backend-selected task through `/api/learning/submissions/`.
- Use the returned ANFIS mastery, Mamdani cognitive-friction, explanation, and adapted `nextTask`.
- Submit the persistent micro-survey requested at each unanswered five-task milestone.

Interactive API documentation is available at `http://localhost:8000/api/docs/`.

Public task payloads intentionally omit MCQ answer keys, code answer guides, and unrevealed hints. Hint usage and MCQ correctness are derived by the backend. Code tasks are not graded; their model signals come from completion, timing, and server-recorded assistance behavior.

## Fuzzy Models

The versioned ANFIS parameter artifact is bootstrapped from deterministic synthetic learner profiles because no real learner dataset is available. Training uses a fixed 80/20 train/holdout split. The current 180-row artifact reports holdout RMSE `5.8401` and R² `0.922`.

The Mamdani engine clips linguistic output membership functions, aggregates rule consequents with `max`, and defuzzifies the result using the centroid of the aggregated output area.

To reproduce the ANFIS artifact:

```bash
docker compose run --rm backend python manage.py migrate --noinput
docker compose run --rm backend python manage.py seed_anfis_training_data --count 180 --seed 42 --clear-existing
docker compose run --rm backend python manage.py train_anfis --epochs 650 --validation-fraction 0.2 --split-seed 42
docker compose run --rm backend python manage.py evaluate_anfis --min-samples 30
```

Run backend verification with:

```bash
docker compose run --rm backend python manage.py test -v 2
docker compose run --rm backend python manage.py spectacular --validate
```

The technical report and user manual are in `docs/FuzzyTutor_Technical_Report.pdf`, with its editable source beside it.
