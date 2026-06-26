# Frontend Implementation Plan

## Phase 1: Learning Workspace

- Build a full task workflow for MCQ tasks.
- Add sandbox code-writing task UI with a syntax-highlighted editor.
- Track elapsed time, hint/documentation expansions, and submission events.
- Add robust loading, error, and empty states for all API calls.

## Phase 2: Explainable AI Sidebar

- Replace placeholder metrics with live evaluation results after each submission.
- Add mastery and friction gauges.
- Add linguistic state badges such as Focused & Steady, Rushing, Needs Support, and Frustrated.
- Show concise supportive explanations when the backend queues them.

## Phase 3: Curriculum & Progress

- Add module navigation and task history.
- Show difficulty tier, task archetype, and progress through each module.
- Add transitions between MCQ and sandbox tasks.
- Add a student session summary view.

## Phase 4: Feedback Loops

- Trigger micro-surveys every 5 tasks.
- Collect satisfaction with difficulty, clarity, and perceived support.
- Add educator-facing feedback hooks if required by the evaluation design.

## Phase 5: Polish & Accessibility

- Add keyboard-friendly interactions and visible focus states.
- Validate responsive layouts for mobile, tablet, and desktop.
- Add accessible labels for gauges, editor controls, choices, and survey inputs.
- Add frontend tests for task rendering, submission flow, and XAI panel updates.
