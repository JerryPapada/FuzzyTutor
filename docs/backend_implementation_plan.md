# Backend Implementation Plan

## Phase 1: API Foundation

- Add models for curriculum modules, tasks, choices, sessions, submissions, hints, and surveys.
- Add serializers and viewsets for read-only curriculum/task APIs.
- Seed the seven proposal modules and starter MCQ/code-writing tasks.
- Add API tests for health, module listing, next-task retrieval, and submission evaluation.

## Phase 2: Fuzzy Engine Layer

- Implement Mamdani inputs:
  - Relative response time: fast/rushing, nominal/focused, slow/stalling.
  - Assistance interactions: low, medium, high.
- Implement Mamdani output:
  - System cognitive friction: disengaged, balanced, frustrated.
- Define triangular/trapezoidal membership functions and centroid defuzzification.
- Implement ANFIS input contract:
  - Task metric weight.
  - Historical cumulative grade average.
- Start with a transparent TSK-style inference implementation, then add training from historical/sample data.
- Persist engine inputs/outputs with each submission for reporting and final-document analysis.

## Phase 3: Adaptation Controller

- Combine ANFIS mastery and Mamdani friction into a next-task decision matrix.
- Implement difficulty tiers and task selection rules.
- Add supportive explanation queueing when mastery is low and friction is high.
- Add safeguards against repeated task types and abrupt difficulty jumps.

## Phase 4: Evaluation & Reporting

- Add micro-survey storage every 5 tasks.
- Export anonymized CSV/JSON for live evaluation sessions.
- Add admin screens for reviewing modules, tasks, submissions, fuzzy outputs, and survey responses.
- Document fuzzy sets, rules, defuzzification, and ANFIS architecture for the final PDF.

## Phase 5: Hardening

- Add authentication or anonymous session tokens.
- Add rate limits and input validation.
- Add production settings for Postgres, static files, and secure secrets.
- Add CI checks for formatting, backend tests, and container builds.
