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
- Load the 105-task, seven-module catalog through `/api/learning/modules/` and `/api/learning/tasks/`.
- Reveal up to three progressive, server-persisted hints through `/api/learning/hints/`.
- Submit the backend-selected task through `/api/learning/submissions/`.
- Use module mastery, cognitive friction, and graded MCQ evidence to exit a module after at least six tasks, or continue through its 15-task bank.
- Review skipped and incorrect attempts through `/api/learning/sessions/<token>/review/`.
- Submit the persistent micro-survey requested at each unanswered five-task milestone.

Interactive API documentation is available at `http://localhost:8000/api/docs/`.

Public task payloads intentionally omit MCQ answer keys, code answer guides, explanations, and unrevealed hints. These are exposed only through read-only review after an eligible attempt. Hint usage, completion, and MCQ correctness are derived by the backend. Code tasks are not graded: blank or unchanged starter code is rejected, while a meaningfully edited response remains ungraded and contributes conservative behavioral evidence.

## Fuzzy Models

The versioned ANFIS parameter artifact is bootstrapped from deterministic synthetic learner profiles because no real learner dataset is available. Training uses a fixed 80/20 train/holdout split. Synthetic code rows have unknown correctness and use the conservative `40 + 25 × completion` performance signal. The current 180-row artifact reports holdout RMSE `4.3674` and R² `0.9364`.

The Mamdani engine clips linguistic output membership functions, aggregates rule consequents with `max`, and defuzzifies the result using the centroid of the aggregated output area.

To reproduce the ANFIS artifact:

```bash
docker compose run --rm backend python manage.py migrate --noinput
docker compose run --rm backend python manage.py seed_anfis_training_data --count 180 --seed 42 --clear-existing
docker compose run --rm backend python manage.py train_anfis --epochs 650 --validation-fraction 0.2 --split-seed 42 --include-synthetic-only
docker compose run --rm backend python manage.py evaluate_anfis --min-samples 30 --include-synthetic-only
```

Run backend verification with:

```bash
docker compose run --rm backend python manage.py test -v 2
docker compose run --rm backend python manage.py spectacular --validate
docker compose run --rm frontend npm test
docker compose run --rm frontend npm run build
```

The consolidated theory, implementation, worked example, and presentation notes are in
`output/pdf/FuzzyTutor_Master_Study_Guide.pdf`.
