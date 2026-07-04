# Frontend Implementation Plan

## Current Frontend Shape

- Left sidebar: clickable modules such as Python Lists, Arrays, Dictionaries, Classes, Inheritance, Exceptions, and Control Flow.
- Each module card shows a module score and an aggregate score.
- Center panel: one active task at a time, either MCQ or coding.
- Right sidebar: aggregate fuzzy metrics, recommendation, and support message.

## Phase 1: Workspace Shell

- Keep the app layout as a fixed three-column learning workspace.
- Keep module selection in the left sidebar and task rendering in the center panel.
- Keep the fuzzy statistics panel on the right.
- Maintain loading and empty states when modules or tasks are not yet loaded.

## Phase 2: Task Interaction

- Support MCQ selection and simple code-response entry.
- Track elapsed time per task.
- Support back/forward navigation inside the current module or task sequence.
- Send submission data to the fuzzy endpoint after each response.

## Phase 3: Progress and Scores

- Show per-module progress and scores in the sidebar.
- Show the current task position inside the active module.
- Keep aggregate mastery and friction visible in the right panel.
- Add stronger visual feedback when the learner needs support or looks ready to advance.

## Phase 4: Feedback and Surveys

- Trigger micro-surveys every five tasks if needed for evaluation.
- Collect student feedback on difficulty, clarity, and support.
- Show short explanations from the backend when the fuzzy engine returns them.

## Phase 5: Polish and Accessibility

- Keep the layout responsive on mobile and tablet.
- Ensure module cards, task options, and buttons are keyboard accessible.
- Add tests for module switching, task rendering, and fuzzy metric updates.
