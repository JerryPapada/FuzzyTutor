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

## Current Backbone

- `backend/`: Django REST Framework API with health, curriculum, next-task, and placeholder fuzzy evaluation endpoints.
- `frontend/`: Vite React app that consumes the API and displays the first tutor/XAI workflow.
- `docs/`: assignment context and implementation plans.
- `docker-compose.yml`: local development stack for backend and frontend containers.
