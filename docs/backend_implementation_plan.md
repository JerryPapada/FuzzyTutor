# Backend Implementation Plan

## Current Backend Shape

- Serve a read-only curriculum catalog with example module records for Python Lists, Arrays, Dictionaries, Classes, Inheritance, Exceptions, and Control Flow.
- Serve a small example task bank that includes MCQ and coding tasks, grouped by `moduleId`.
- Keep the fuzzy endpoint as a scoring contract that returns aggregate mastery, cognitive friction, focus state, recommendation, and a short support message.
- Keep the backend decoupled from the frontend: the frontend drives navigation, while the backend provides content and fuzzy evaluation responses.

## Phase 1: Content and API Contracts

- Keep the `/api/health/`, `/api/learning/modules/`, `/api/learning/tasks/`, `/api/learning/next-task/`, and `/api/fuzzy/evaluate/` endpoints stable.
- Add models later only when session persistence is needed for real students.
- Expand serializers/viewsets only if the API becomes database-backed.
- Add tests for module listing, task retrieval, and fuzzy evaluation response shape.

## Phase 2: Session and Task Tracking

- Add anonymous session tokens or lightweight session records.
- Store selected module, current task index, answer attempts, elapsed time, and hint usage.
- Persist per-module score history and aggregate learner score history.
- Record whether a submission was MCQ or code and whether it was correct or completed.

## Phase 3: Fuzzy Engine Layer

- Keep mastery as the aggregate learner state returned by the fuzzy endpoint.
- Keep friction as the aggregate cognitive-load estimate for the current session.
- Define Mamdani inputs for response time, assistance interactions, and completion behavior.
- Define ANFIS inputs for task weight, historical grade, and submission quality.
- Replace the current deterministic approximation with a transparent fuzzy inference flow when training data exists.

## Phase 4: Adaptation and Reporting

- Use mastery and friction to choose the next task difficulty and support level.
- Support module-local progression plus an overall learner summary.
- Store micro-surveys every five tasks if the evaluation requires them.
- Export submission and fuzzy logs for the final report.

## Phase 5: Hardening

- Add rate limiting and validation for submission payloads.
- Add production settings for Postgres, static files, and secure secrets.
- Add CI checks for formatting, backend tests, and container builds.
